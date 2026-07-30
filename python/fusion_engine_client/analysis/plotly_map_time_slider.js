// Time-range control injected below plot_map()'s figure (see Analyzer._map_time_slider_js()). Draws a
// speed-vs-time background chart (from pose velocity data) with a draggable/resizable window on top: dragging an
// edge narrows the P1 time range shown on the map, dragging the body pans it, and double-clicking resets it to the
// full range. A one-line "Showing X -> Y" readout below the slider echoes the current window as text.
//
// Requires the MAP_SLIDER_* globals (set by Analyzer._map_time_slider_js() immediately before this file is injected)
// plus the common per-figure globals set up by Analyzer.__write_html_and_inject_js() (`figure`, `time_axis_type`,
// `p1_t0_sec`, `gps_posix_offset_sec`).
(function() {
  var P1_TIME_MIN = MAP_SLIDER_T_MIN;
  var P1_TIME_MAX = MAP_SLIDER_T_MAX;
  var PROFILE_TIME = MAP_SLIDER_PROFILE_TIME;
  var PROFILE_SPEED = MAP_SLIDER_PROFILE_SPEED;
  var PROFILE_GPS_TIME = MAP_SLIDER_PROFILE_GPS_TIME;
  var SECONDS_PER_WEEK = 7 * 24 * 3600.0;
  // Column index of P1 time within each point's customdata row -- must match the column order built by
  // Analyzer._build_position_customdata() in analyzer.py (currently [utc_str, rel_time, p1_time, ...]).
  var P1_TIME_CUSTOMDATA_INDEX = 2;
  var SLIDER_HEIGHT_PX = 80;
  var READOUT_HEIGHT_PX = 22;
  var TRACK_INSET_PX = 16;
  var TRACK_PADDING_V_PX = 4;
  var X_AXIS_LABEL_PX = 14;
  var ACCENT_COLOR = '#FF9C00';
  var MIN_WINDOW_SEC = Math.max(1e-3, (P1_TIME_MAX - P1_TIME_MIN) * 0.001);

  // Plotly stores large numeric arrays (e.g. lat/lon built from numpy arrays) internally as a typed-array wrapper
  // object (`{dtype, bdata, _inputArray}`) rather than a plain Array, so a real Array can't always be recovered with
  // trace.lat.slice() -- unwrap `_inputArray` (an array-like object keyed "0", "1", ... with a few extra
  // non-numeric metadata keys mixed in) and copy its numeric entries out by hand instead.
  function toPlainArray(value) {
    if (value == null) return null;
    if (Array.isArray(value)) return value.slice();
    var src = value.hasOwnProperty('_inputArray') ? value._inputArray : value;
    if (Array.isArray(src)) return src.slice();
    var out = [];
    for (var i = 0; src.hasOwnProperty(i); i++) out.push(src[i]);
    return out;
  }

  // Snapshot each trace's original lat/lon/customdata before any restyle() call mutates figure.data in place --
  // narrowing/widening the window always re-filters from this pristine copy, never from what's currently displayed.
  var ORIGINAL_TRACES = figure.data.map(function(trace) {
    return {
      lat: toPlainArray(trace.lat),
      lon: toPlainArray(trace.lon),
      customdata: toPlainArray(trace.customdata),
    };
  });

  // Locate the slider below the map. We'll reflow the map and make it visible below, in scheduleReveal(), after Plotly
  // finishes rendering it, to make sure it displays at the correct size right away, making room vertically for the
  // slider. If we display it immediately, instead of after the first render, it will initially appear full size and
  // then shrink to accommodate the slider.
  var mapContainer = figure.parentNode;

  var sliderContainer = document.createElement('div');
  sliderContainer.style.cssText = 'flex:0 0 ' + SLIDER_HEIGHT_PX + 'px; width:100%; box-sizing:border-box; ' +
    'padding:' + TRACK_PADDING_V_PX + 'px ' + TRACK_INSET_PX + 'px; background:#ffffff; border-top:1px solid #e4e4e1;';

  var trackDiv = document.createElement('div');
  trackDiv.style.cssText = 'position:relative; width:100%; height:100%;';
  sliderContainer.appendChild(trackDiv);

  var canvas = document.createElement('canvas');
  canvas.style.cssText = 'position:absolute; left:0; top:0; width:100%; height:100%;';
  trackDiv.appendChild(canvas);

  // windowDiv (the draggable selection) only covers the plotted chart area, not the X axis label strip below it
  // (see drawProfile()), so the highlighted band lines up with the speed curve it's overlaid on.
  var windowDiv = document.createElement('div');
  windowDiv.style.cssText = 'position:absolute; top:0; bottom:' + X_AXIS_LABEL_PX + 'px; ' +
    'background:rgba(201,127,10,0.10); border:1px solid ' + ACCENT_COLOR + '; box-sizing:border-box; cursor:grab;';
  trackDiv.appendChild(windowDiv);

  // Solid, protruding grab bars for dragging the size of the visible time range.
  var HANDLE_CSS = 'position:absolute; top:-4px; bottom:-4px; width:8px; background:' + ACCENT_COLOR + '; ' +
    'cursor:ew-resize;';
  var leftHandle = document.createElement('div');
  leftHandle.style.cssText = HANDLE_CSS + 'left:-5px;';
  windowDiv.appendChild(leftHandle);

  var rightHandle = document.createElement('div');
  rightHandle.style.cssText = HANDLE_CSS + 'right:-5px;';
  windowDiv.appendChild(rightHandle);

  mapContainer.appendChild(sliderContainer);

  // Text echo of the current window, in the same time-type-aware format as the axis ticks -- lets the current
  // range be read precisely (and copy-pasted) without having to eyeball tick positions.
  var readoutDiv = document.createElement('div');
  readoutDiv.style.cssText = 'flex:0 0 ' + READOUT_HEIGHT_PX + 'px; width:100%; box-sizing:border-box; ' +
    'padding:2px ' + TRACK_INSET_PX + 'px; background:#ffffff; color:' + ACCENT_COLOR + '; ' +
    'font:12px -apple-system, "Segoe UI", Roboto, sans-serif;';
  mapContainer.appendChild(readoutDiv);

  function timeToFrac(t) { return (t - P1_TIME_MIN) / (P1_TIME_MAX - P1_TIME_MIN); }
  function fracToTime(f) { return P1_TIME_MIN + f * (P1_TIME_MAX - P1_TIME_MIN); }

  function pixelToTime(clientX) {
    var rect = trackDiv.getBoundingClientRect();
    var frac = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    return fracToTime(frac);
  }

  // Only P1 times with a real (non-NaN) GPS time can be used as GPS time interpolation/extrapolation anchors below.
  var VALID_PROFILE_TIME = [];
  var VALID_PROFILE_GPS_TIME = [];
  for (var vi = 0; vi < PROFILE_TIME.length; vi++) {
    if (!isNaN(PROFILE_GPS_TIME[vi])) {
      VALID_PROFILE_TIME.push(PROFILE_TIME[vi]);
      VALID_PROFILE_GPS_TIME.push(PROFILE_GPS_TIME[vi]);
    }
  }

  // Interpolate (or, beyond the known data, extrapolate) GPS time for an arbitrary P1 time -- P1 and GPS time
  // aren't related by a fixed offset (see Analyzer._map_time_slider_js() docstring) but P1 time should be rate-locked
  // to GPS time when it is available.
  //
  // For timeline purposes, displayed timestamps don't need to be precise: the scale is large and can't be zoomed in on
  // the map's slider. Before GPS time is known, extrapolate assuming P1 time tracks real elapsed time 1:1 -- it does
  // not, but this is a good enough approximation for a while.
  //
  // Before GPS time is available, P1 time is rate-locked to the device's local oscillator. Even a very poor 300 PPM
  // oscillator only accumulates ~1 sec of error per hour. A 1-2 hour window should be good enough for display purposes.
  // Past that, the error is large enough it's better to just say so (fall back to a P1 reading) than to show a
  // wrong-looking UTC/GPS time -- see formatTickLabel()/utcPartsForP1() callers.
  var GPS_EXTRAPOLATION_LIMIT_SEC = 2 * 3600;

  function p1ToGpsTime(p1) {
    var n = VALID_PROFILE_TIME.length;
    if (n === 0) {
      return NaN;
    }
    if (n === 1) {
      var dtOnly = p1 - VALID_PROFILE_TIME[0];
      return Math.abs(dtOnly) <= GPS_EXTRAPOLATION_LIMIT_SEC ? VALID_PROFILE_GPS_TIME[0] + dtOnly : NaN;
    }
    if (p1 <= VALID_PROFILE_TIME[0]) {
      var dtBefore = VALID_PROFILE_TIME[0] - p1;
      return dtBefore <= GPS_EXTRAPOLATION_LIMIT_SEC ? VALID_PROFILE_GPS_TIME[0] - dtBefore : NaN;
    }
    if (p1 >= VALID_PROFILE_TIME[n - 1]) {
      var dtAfter = p1 - VALID_PROFILE_TIME[n - 1];
      return dtAfter <= GPS_EXTRAPOLATION_LIMIT_SEC ? VALID_PROFILE_GPS_TIME[n - 1] + dtAfter : NaN;
    }
    // Interior: bracket and linearly interpolate between the two nearest valid points -- no error cap needed here
    // (unlike the edges above), since the real GPS time is known at both ends, however far apart a mid-log gap in
    // GPS availability left them.
    var lo = 0, hi = n - 1;
    while (hi - lo > 1) {
      var mid = (lo + hi) >> 1;
      if (VALID_PROFILE_TIME[mid] <= p1) lo = mid; else hi = mid;
    }
    var t0 = VALID_PROFILE_TIME[lo], t1 = VALID_PROFILE_TIME[hi];
    var frac = (t1 > t0) ? (p1 - t0) / (t1 - t0) : 0;
    return VALID_PROFILE_GPS_TIME[lo] + frac * (VALID_PROFILE_GPS_TIME[hi] - VALID_PROFILE_GPS_TIME[lo]);
  }

  // Split a P1 time into UTC calendar date + time-of-day, for the tick loop below to decide when a date needs to
  // be shown (first tick, or a tick that landed on a different day than the previous one). Returns null if UTC
  // can't be resolved (no GPS/POSIX offset, or no profile data to interpolate GPS time from).
  function utcPartsForP1(p1) {
    var gps = p1ToGpsTime(p1);
    if (isNaN(gps) || typeof gps_posix_offset_sec !== 'number') {
      return null;
    }
    var iso = new Date((gps + gps_posix_offset_sec) * 1000.0).toISOString();
    return { date: iso.slice(0, 10).split('-').join('/'), time: iso.substr(11, 8) };
  }

  // Match the X axis format used by the log's other time-series plots (see Analyzer.time_type / _resolve_x_axis()).
  // The domain label ("Rel:", "P1:", "GPS:") only needs to appear once, on the first tick -- it's the same for
  // every tick after that.
  function formatTickLabel(p1, is_first) {
    if (time_axis_type === 'relative') {
      var s = (p1 - (p1_t0_sec || 0)).toFixed(1) + ' s';
      return is_first ? 'Rel: ' + s : s;
    }
    if (time_axis_type === 'p1') {
      var s = p1.toFixed(1) + ' s';
      return is_first ? 'P1: ' + s : s;
    }
    if (time_axis_type === 'gps') {
      var gps = p1ToGpsTime(p1);
      // GPS time may not be available at the start of the timeline if we have to extrapolate backward for a very long
      // time. Rather than silently showing a bare number that looks like a GPS value but isn't, label it as what it
      // actually is.
      if (isNaN(gps)) {
        return 'P1: ' + p1.toFixed(1) + ' s';
      }
      var week = Math.floor(gps / SECONDS_PER_WEEK);
      var tow_sec = gps - week * SECONDS_PER_WEEK;
      var s = week + ':' + tow_sec.toFixed(1);
      return is_first ? 'GPS: ' + s : s;
    }
    // 'utc' -- no date-change context here (see the tick loop's own UTC handling below), just the time of day.
    var parts = utcPartsForP1(p1);
    return parts ? parts.time : 'P1: ' + p1.toFixed(1) + ' s';
  }

  function resizeCanvas() {
    var rect = trackDiv.getBoundingClientRect();
    var dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(rect.width * dpr);
    canvas.height = Math.round(rect.height * dpr);
    drawProfile();
  }

  function drawProfile() {
    var ctx = canvas.getContext('2d');
    var dpr = window.devicePixelRatio || 1;
    var w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    var axisPx = Math.round(X_AXIS_LABEL_PX * dpr);
    var chartH = Math.max(0, h - axisPx);

    var maxSpeed = 0;
    for (var i = 0; i < PROFILE_SPEED.length; i++) {
      if (PROFILE_SPEED[i] > maxSpeed) maxSpeed = PROFILE_SPEED[i];
    }
    maxSpeed = Math.max(1, Math.ceil(maxSpeed));

    if (PROFILE_TIME.length >= 2) {
      function y(speed) { return chartH - (speed / maxSpeed) * chartH; }
      ctx.beginPath();
      for (var i = 0; i < PROFILE_TIME.length; i++) {
        var x = timeToFrac(PROFILE_TIME[i]) * w;
        if (i === 0) ctx.moveTo(x, y(PROFILE_SPEED[i])); else ctx.lineTo(x, y(PROFILE_SPEED[i]));
      }
      ctx.strokeStyle = '#aab2bc';
      ctx.lineWidth = Math.max(1, 1.4 * dpr);
      ctx.stroke();
    }

    // Y axis context (vehicle speed) - 0 at the bottom, ceil(max) at the top.
    ctx.fillStyle = '#6b6b66';
    ctx.font = Math.round(10 * dpr) + 'px sans-serif';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText(maxSpeed + ' m/s', 4 * dpr, 3 * dpr);
    ctx.textBaseline = 'alphabetic';
    ctx.fillText('0 m/s', 4 * dpr, chartH - 3 * dpr);

    // X axis time, in whatever format the rest of the log's plots use (self.time_type). The domain marker
    // ("Rel:"/"P1:"/"GPS:"/"UTC:") only appears once, on the first tick that actually has it -- usually tick 0,
    // but GPS/UTC time may not be available yet that early in the log (e.g. before first fix), in which case that
    // tick falls back to a clearly-labeled "P1: ..." reading instead, and the "UTC:" marker moves to the first
    // tick that does resolve. In 'utc' mode, the bare time of day is also ambiguous about which day it's from, so
    // that same first-resolved tick -- and any later tick that lands on a different UTC calendar day than the one
    // before it, however many days apart -- gets the date too.
    var tickFracs = [0, 0.25, 0.5, 0.75, 1.0];
    ctx.font = Math.round(10 * dpr) + 'px sans-serif';
    ctx.textBaseline = 'top';
    var lastUtcDate = null;
    var utcDomainLabelShown = false;
    tickFracs.forEach(function(f, idx) {
      ctx.textAlign = (idx === 0) ? 'left' : (idx === tickFracs.length - 1) ? 'right' : 'center';
      var p1 = fracToTime(f);
      var label;
      if (time_axis_type === 'utc') {
        var parts = utcPartsForP1(p1);
        if (parts === null) {
          label = 'P1: ' + p1.toFixed(1) + ' s';
        } else {
          var showDate = !utcDomainLabelShown || (parts.date !== lastUtcDate);
          lastUtcDate = parts.date;
          var dateTime = showDate ? (parts.date + ' ' + parts.time) : parts.time;
          label = !utcDomainLabelShown ? ('UTC: ' + dateTime) : dateTime;
          utcDomainLabelShown = true;
        }
      } else {
        label = formatTickLabel(p1, idx === 0);
      }
      ctx.fillText(label, f * w, chartH + 2 * dpr);
    });
  }

  var winStart = P1_TIME_MIN;
  var winEnd = P1_TIME_MAX;

  // Neither side gets a "Rel:"/"P1:"/"GPS:"/"UTC:" prefix here -- "Showing" already establishes these are times,
  // and the axis ticks above spell out which domain -- *unless* GPS/UTC time isn't actually available for that
  // particular value (e.g. before first fix), in which case it falls back to an explicitly-labeled "P1: ..."
  // reading instead of a bare number that looks like it's in the axis's domain but isn't. In 'utc' mode, the end
  // date is only repeated if it actually differs from the start's (mirrors the axis ticks' own midnight-crossing
  // rule, just for these two values) -- unless the start itself fell back to P1, in which case there's no prior
  // date to compare against, so the end always shows its date too.
  // Always HH:MM:SS, even when hours is 0 -- dropping leading zero fields reads ambiguously (is "01:25" one
  // minute or one hour?).
  function formatDuration(duration_sec) {
    var total_sec = Math.max(0, Math.round(duration_sec));
    var hh = Math.floor(total_sec / 3600);
    var mm = Math.floor((total_sec % 3600) / 60);
    var ss = total_sec % 60;
    function pad(n) { return (n < 10 ? '0' : '') + n; }
    return pad(hh) + ':' + pad(mm) + ':' + pad(ss);
  }

  function formatRangeReadout() {
    var rangeText;
    if (time_axis_type === 'utc') {
      var p0 = utcPartsForP1(winStart);
      var p1 = utcPartsForP1(winEnd);
      var startText = p0 ? (p0.date + ' ' + p0.time) : ('P1: ' + winStart.toFixed(1) + ' s');
      var endText;
      if (p1 === null) {
        endText = 'P1: ' + winEnd.toFixed(1) + ' s';
      } else if (p0 === null || p1.date !== p0.date) {
        endText = p1.date + ' ' + p1.time;
      } else {
        endText = p1.time;
      }
      rangeText = startText + ' → ' + endText;
    } else {
      rangeText = formatTickLabel(winStart, false) + ' - ' + formatTickLabel(winEnd, false);
    }
    return 'Displaying: ' + rangeText + ' | Duration: ' + formatDuration(winEnd - winStart);
  }

  function updateWindowDivStyle() {
    var f0 = timeToFrac(winStart), f1 = timeToFrac(winEnd);
    windowDiv.style.left = (f0 * 100) + '%';
    windowDiv.style.width = Math.max(0, (f1 - f0) * 100) + '%';
    readoutDiv.textContent = formatRangeReadout();
  }

  // Re-slice from ORIGINAL_TRACES (not figure.data) so widening the window can bring back points a previous
  // restyle() dropped.
  function applyMapFilter() {
    var traceIndices = [], latUpdate = [], lonUpdate = [], cdUpdate = [];
    for (var i = 0; i < ORIGINAL_TRACES.length; i++) {
      var orig = ORIGINAL_TRACES[i];
      if (!orig.customdata) continue;
      var lat = [], lon = [], cd = [];
      for (var j = 0; j < orig.customdata.length; j++) {
        var t = orig.customdata[j][P1_TIME_CUSTOMDATA_INDEX];
        if (t >= winStart && t <= winEnd) {
          lat.push(orig.lat[j]);
          lon.push(orig.lon[j]);
          cd.push(orig.customdata[j]);
        }
      }

      if (lat.length === 0) {
        // A trace with a genuinely empty lat/lon array gets dropped from the legend entirely -- making a solution
        // type that just has no points in *this* window look like it never had any data at all (unlike the
        // always-present placeholder trace Analyzer.plot_map() draws for solution types with no data in the whole
        // log, which uses a single [NaN] point specifically to stay in the legend). Match that same convention
        // here so narrowing the window doesn't make legend entries disappear.
        lat = [NaN];
        lon = [NaN];
        cd = [];
      }

      traceIndices.push(i);
      latUpdate.push(lat);
      lonUpdate.push(lon);
      cdUpdate.push(cd);
    }
    if (traceIndices.length > 0) {
      Plotly.restyle(figure, {lat: latUpdate, lon: lonUpdate, customdata: cdUpdate}, traceIndices);
    }
  }

  var pendingFilter = null;
  function scheduleFilter() {
    updateWindowDivStyle();
    if (pendingFilter) return;
    pendingFilter = setTimeout(function() {
      pendingFilter = null;
      applyMapFilter();
    }, 16);
  }

  function resetWindow() {
    winStart = P1_TIME_MIN;
    winEnd = P1_TIME_MAX;
    scheduleFilter();
  }

  var dragMode = null, dragStartX = 0, dragWinStart = 0, dragWinEnd = 0;

  function onPointerMove(evt) {
    if (!dragMode) return;
    if (dragMode === 'left') {
      winStart = Math.max(P1_TIME_MIN, Math.min(pixelToTime(evt.clientX), winEnd - MIN_WINDOW_SEC));
    } else if (dragMode === 'right') {
      winEnd = Math.min(P1_TIME_MAX, Math.max(pixelToTime(evt.clientX), winStart + MIN_WINDOW_SEC));
    } else if (dragMode === 'pan') {
      var rect = trackDiv.getBoundingClientRect();
      var deltaTime = ((evt.clientX - dragStartX) / rect.width) * (P1_TIME_MAX - P1_TIME_MIN);
      var width = dragWinEnd - dragWinStart;
      var newStart = dragWinStart + deltaTime, newEnd = dragWinEnd + deltaTime;
      if (newStart < P1_TIME_MIN) { newStart = P1_TIME_MIN; newEnd = newStart + width; }
      if (newEnd > P1_TIME_MAX) { newEnd = P1_TIME_MAX; newStart = newEnd - width; }
      winStart = newStart;
      winEnd = newEnd;
    }
    scheduleFilter();
  }

  function onPointerUp() {
    dragMode = null;
    windowDiv.style.cursor = 'grab';
    document.removeEventListener('mousemove', onPointerMove);
    document.removeEventListener('mouseup', onPointerUp);
  }

  function beginDrag(mode) {
    return function(evt) {
      evt.preventDefault();
      evt.stopPropagation();
      dragMode = mode;
      dragStartX = evt.clientX;
      dragWinStart = winStart;
      dragWinEnd = winEnd;
      if (mode === 'pan') windowDiv.style.cursor = 'grabbing';
      document.addEventListener('mousemove', onPointerMove);
      document.addEventListener('mouseup', onPointerUp);
    };
  }

  leftHandle.addEventListener('mousedown', beginDrag('left'));
  rightHandle.addEventListener('mousedown', beginDrag('right'));
  windowDiv.addEventListener('mousedown', function(evt) {
    if (evt.target === leftHandle || evt.target === rightHandle) return;
    beginDrag('pan')(evt);
  });
  trackDiv.addEventListener('dblclick', resetWindow);

  window.addEventListener('resize', function() {
    setTimeout(function() { Plotly.Plots.resize(figure); resizeCanvas(); }, 0);
  });

  updateWindowDivStyle();

  // The <head> <style> block (see Analyzer.plot_map()) starts the map hidden (visibility:hidden, not display:none,
  // so it still occupies its final layout space) and already-shrunk to make room for the slider -- so the slider
  // and readout below are correctly positioned from the very first paint. But Plotly.newPlot()'s initial autosize
  // pass computes its internal plot dimensions from the window size, not the (already-correct) container box, and
  // -- worse, for a WebGL/mapbox trace -- doesn't finish reflecting a resize() call in the same tick it's called,
  // so revealing the map right away (even after calling resize() synchronously) can still show a visible moment of
  // it at the wrong (window-sized) dimensions before catching up. Instead, reveal only once Plotly itself reports
  // a completed (re)draw following the resize -- debounced, in case that triggers more than one -- with a fixed
  // fallback delay in case 'plotly_afterplot' never fires for some reason (so the map is never stuck invisible).
  var revealTimer = null;
  function scheduleReveal(delay_ms) {
    if (revealTimer !== null) {
      clearTimeout(revealTimer);
    }
    revealTimer = setTimeout(function() {
      figure.style.visibility = 'visible';
    }, delay_ms);
  }
  figure.on('plotly_afterplot', function() { scheduleReveal(50); });
  scheduleReveal(500);

  Plotly.Plots.resize(figure);
  resizeCanvas();
})();
