// Time-range control injected below plot_map()'s figure (see Analyzer._map_time_slider_js()). Draws a
// speed-vs-time background chart (from pose velocity data) with a draggable/resizable window on top: dragging an
// edge narrows the P1 time range shown on the map, dragging the body pans it, and double-clicking resets it to the
// full range. Filtering re-slices each trace's original (already-rendered) lat/lon/customdata via
// `Plotly.restyle()`, so no extra per-window traces are added to the page.
//
// Requires the MAP_SLIDER_* globals (set by Analyzer._map_time_slider_js() immediately before this file is
// injected) plus the common per-figure globals set up by Analyzer.__write_html_and_inject_js() (`figure`,
// `time_axis_type`, `p1_t0_sec`, `gps_posix_offset_sec`).
(function() {
  var P1_TIME_MIN = MAP_SLIDER_T_MIN;
  var P1_TIME_MAX = MAP_SLIDER_T_MAX;
  var PROFILE_TIME = MAP_SLIDER_PROFILE_TIME;
  var PROFILE_SPEED = MAP_SLIDER_PROFILE_SPEED;
  var PROFILE_GPS_TIME = MAP_SLIDER_PROFILE_GPS_TIME;
  var SECONDS_PER_WEEK = 7 * 24 * 3600.0;
  var SLIDER_HEIGHT_PX = 80;
  var TRACK_INSET_PX = 16;
  var TRACK_PADDING_V_PX = 4;
  var X_AXIS_LABEL_PX = 14;
  var MIN_WINDOW_SEC = Math.max(1e-3, (P1_TIME_MAX - P1_TIME_MIN) * 0.001);

  // Snapshot each trace's original lat/lon/customdata before any restyle() call mutates figure.data in place --
  // narrowing/widening the window always re-filters from this pristine copy, never from what's currently displayed.
  var ORIGINAL_TRACES = figure.data.map(function(trace) {
    return {
      lat: trace.lat ? trace.lat.slice() : null,
      lon: trace.lon ? trace.lon.slice() : null,
      customdata: trace.customdata ? trace.customdata.slice() : null,
    };
  });

  // Reflow so the map shrinks to make room for the slider below it, instead of the slider being pushed below the
  // fold by the map's normal 100vh height.
  document.documentElement.style.height = '100%';
  document.body.style.height = '100%';
  document.body.style.margin = '0';
  var mapContainer = figure.parentNode;
  mapContainer.style.height = '100%';
  mapContainer.style.display = 'flex';
  mapContainer.style.flexDirection = 'column';
  figure.style.flex = '1 1 auto';
  figure.style.minHeight = '0';
  figure.style.width = '100%';

  var sliderContainer = document.createElement('div');
  sliderContainer.style.cssText = 'flex:0 0 ' + SLIDER_HEIGHT_PX + 'px; width:100%; box-sizing:border-box; ' +
    'padding:' + TRACK_PADDING_V_PX + 'px ' + TRACK_INSET_PX + 'px; background:#f5f5f5; border-top:1px solid #ccc;';

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
    'background:rgba(31,119,180,0.25); border:1px solid rgba(31,119,180,0.9); box-sizing:border-box; cursor:grab;';
  trackDiv.appendChild(windowDiv);

  // Solid, protruding grab bars -- a plain hit-region (no visible affordance) didn't make it obvious the window's
  // edges are independently draggable to resize the range, as opposed to just dragging the body to pan it.
  var HANDLE_CSS = 'position:absolute; top:-4px; bottom:-4px; width:9px; background:rgb(31,119,180); ' +
    'border-radius:3px; box-shadow:0 0 0 1px rgba(255,255,255,0.8); cursor:ew-resize;';
  var leftHandle = document.createElement('div');
  leftHandle.style.cssText = HANDLE_CSS + 'left:-5px;';
  windowDiv.appendChild(leftHandle);

  var rightHandle = document.createElement('div');
  rightHandle.style.cssText = HANDLE_CSS + 'right:-5px;';
  windowDiv.appendChild(rightHandle);

  mapContainer.appendChild(sliderContainer);

  function timeToFrac(t) { return (t - P1_TIME_MIN) / (P1_TIME_MAX - P1_TIME_MIN); }
  function fracToTime(f) { return P1_TIME_MIN + f * (P1_TIME_MAX - P1_TIME_MIN); }

  function pixelToTime(clientX) {
    var rect = trackDiv.getBoundingClientRect();
    var frac = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    return fracToTime(frac);
  }

  // Interpolate GPS time for an arbitrary P1 time using the actual per-point profile samples -- P1 and GPS time
  // aren't related by a fixed offset (see Analyzer._map_time_slider_js() docstring), but both progress at ~1
  // sec/sec, so linear interpolation between the nearest two samples is effectively exact.
  function p1ToGpsTime(p1) {
    var n = PROFILE_GPS_TIME.length;
    if (n < 2) return NaN;
    var lo = 0, hi = n - 1;
    if (p1 <= PROFILE_TIME[0]) { lo = 0; hi = 1; }
    else if (p1 >= PROFILE_TIME[hi]) { lo = hi - 1; }
    else {
      while (hi - lo > 1) {
        var mid = (lo + hi) >> 1;
        if (PROFILE_TIME[mid] <= p1) lo = mid; else hi = mid;
      }
    }
    var t0 = PROFILE_TIME[lo], t1 = PROFILE_TIME[hi];
    var frac = (t1 > t0) ? (p1 - t0) / (t1 - t0) : 0;
    return PROFILE_GPS_TIME[lo] + frac * (PROFILE_GPS_TIME[hi] - PROFILE_GPS_TIME[lo]);
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
      if (isNaN(gps)) {
        return p1.toFixed(1) + ' s';
      }
      var week = Math.floor(gps / SECONDS_PER_WEEK);
      var tow_sec = gps - week * SECONDS_PER_WEEK;
      var s = week + ':' + tow_sec.toFixed(1);
      return is_first ? 'GPS: ' + s : s;
    }
    // 'utc' -- no date-change context here (see the tick loop's own UTC handling below), just the time of day.
    var parts = utcPartsForP1(p1);
    return parts ? parts.time : p1.toFixed(1) + ' s';
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
      ctx.strokeStyle = '#ff7f0e';
      ctx.lineWidth = Math.max(1, 1.5 * dpr);
      ctx.stroke();
    }

    // Y axis context (0 at the baseline, ceil(max) at the top) -- without this there's no indication the
    // background trace is even speed, let alone its scale.
    ctx.fillStyle = 'rgba(90,90,90,0.95)';
    ctx.font = Math.round(10 * dpr) + 'px sans-serif';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText(maxSpeed + ' m/s', 4 * dpr, 3 * dpr);
    ctx.textBaseline = 'alphabetic';
    ctx.fillText('0 m/s', 4 * dpr, chartH - 3 * dpr);

    // X axis time, in whatever format the rest of the log's plots use (self.time_type). The domain marker
    // ("Rel:"/"P1:"/"GPS:"/"UTC:") only appears once, on the first tick. In 'utc' mode, the bare time of day is
    // also ambiguous about which day it's from, so the first tick -- and any later tick that lands on a different
    // UTC calendar day than the one before it, however many days apart -- gets the date too (but not the "UTC:"
    // marker again, since that was already established by the first tick).
    var tickFracs = [0, 0.25, 0.5, 0.75, 1.0];
    ctx.font = Math.round(9 * dpr) + 'px sans-serif';
    ctx.textBaseline = 'top';
    var lastUtcDate = null;
    tickFracs.forEach(function(f, idx) {
      ctx.textAlign = (idx === 0) ? 'left' : (idx === tickFracs.length - 1) ? 'right' : 'center';
      var p1 = fracToTime(f);
      var label;
      if (time_axis_type === 'utc') {
        var parts = utcPartsForP1(p1);
        if (parts === null) {
          label = p1.toFixed(1) + ' s';
        } else {
          var showDate = (idx === 0) || (parts.date !== lastUtcDate);
          lastUtcDate = parts.date;
          var dateTime = showDate ? (parts.date + ' ' + parts.time) : parts.time;
          label = (idx === 0) ? ('UTC: ' + dateTime) : dateTime;
        }
      } else {
        label = formatTickLabel(p1, idx === 0);
      }
      ctx.fillText(label, f * w, chartH + 2 * dpr);
    });
  }

  var winStart = P1_TIME_MIN;
  var winEnd = P1_TIME_MAX;

  function updateWindowDivStyle() {
    var f0 = timeToFrac(winStart), f1 = timeToFrac(winEnd);
    windowDiv.style.left = (f0 * 100) + '%';
    windowDiv.style.width = Math.max(0, (f1 - f0) * 100) + '%';
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
        var t = orig.customdata[j][1];
        if (t >= winStart && t <= winEnd) {
          lat.push(orig.lat[j]);
          lon.push(orig.lon[j]);
          cd.push(orig.customdata[j]);
        }
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
  setTimeout(function() { Plotly.Plots.resize(figure); resizeCanvas(); }, 0);
})();
