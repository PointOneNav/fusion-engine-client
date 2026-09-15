// Time-range control injected below a figure's plot (see Analyzer._time_slider_js()). Draws a background chart of
// some per-sample quantity vs time (e.g., vehicle speed), with a window on top marking the P1 time range the figure
// shows and a one-line readout of that range below.
//
// Choosing a range:
//
// - Drag outside the window to pick out a new range, drag the window itself to slide it through the log, and drag
//   an edge of it to adjust that edge.
// - Double-click the window to narrow it to a single step in time, and again to go back to the whole log. With a
//   step selected, clicking anywhere on the track jumps to the step there.
// - The left/right arrow keys move the window, and a play button (or the space bar) animates it forward at a
//   selectable multiple of real time.
//
// Moving around the time scale itself, which is independent of the range selected on it:
//
// - Ctrl+scroll zooms it about the cursor, and shift+drag or shift+scroll pans it.
// - Double-clicking away from the window fits the whole log back on it.
//
// Requires the TIME_SLIDER_* globals (set by Analyzer._time_slider_js() immediately before this file is injected)
// plus the common per-figure globals set up by Analyzer.__write_html_and_inject_js() (`figure`, `time_axis_type`,
// `p1_t0_sec`, `gps_posix_offset_sec`).
(function() {
  var P1_TIME_MIN = TIME_SLIDER_T_MIN;
  // A log covering a single instant would leave the time scale no width to map timestamps onto, so give it one.
  var P1_TIME_MAX = (TIME_SLIDER_T_MAX > TIME_SLIDER_T_MIN) ? TIME_SLIDER_T_MAX : TIME_SLIDER_T_MIN + 1.0;
  // Trace attributes holding one entry per plotted point, filtered together whenever the window changes. Nested
  // attributes are named with a dot (e.g. `marker.color`), the same way Plotly.restyle() addresses them.
  var POINT_FIELDS = TIME_SLIDER_POINT_FIELDS;
  var P1_TIME_CUSTOMDATA_INDEX = TIME_SLIDER_TIME_CUSTOMDATA_INDEX;
  var PROFILE_TIME = TIME_SLIDER_PROFILE_TIME;
  // One or more series sharing PROFILE_TIME, each `{values, color, label}`. A label is drawn next to the chart's
  // zero line to say which curve is which, and left empty where there is only one curve to name.
  var PROFILE_SERIES = TIME_SLIDER_PROFILE_SERIES;
  var PROFILE_GPS_TIME = TIME_SLIDER_PROFILE_GPS_TIME;
  var PROFILE_UNITS = TIME_SLIDER_PROFILE_UNITS;
  var NOTE = TIME_SLIDER_NOTE;
  var HAS_DRAGGABLE_VIEW = TIME_SLIDER_HAS_DRAGGABLE_VIEW;
  var SECONDS_PER_WEEK = 7 * 24 * 3600.0;
  var SLIDER_HEIGHT_PX = 80;
  var READOUT_HEIGHT_PX = 26;
  var TRACK_INSET_PX = 16;
  var TRACK_PADDING_V_PX = 4;
  var X_AXIS_LABEL_PX = 14;
  var ACCENT_COLOR = '#FF9C00';
  var WINDOW_FILL = 'rgba(201,127,10,0.10)';
  var PANEL_COLOR = '#ffffff';
  // Everything the control draws in the accent color goes grey while playback is held for a figure gesture. The
  // readout says so too, but a line of text at the end of a status line is easy to miss, where the whole control
  // changing color is not.
  var HELD_COLOR = '#9a9a92';
  var HELD_WINDOW_FILL = 'rgba(120,120,112,0.12)';
  var HELD_PANEL_COLOR = '#f1f1ee';
  var MIN_WINDOW_SEC = 1e-3;
  // Smallest time span the X axis can be zoomed in to with ctrl+scroll.
  var MIN_VIEW_SPAN_SEC = 0.05;
  // Width the selection is drawn at when its true width would be narrower than this, so a very short window (a
  // single step, say) stays visible and grabbable.
  var MIN_WINDOW_PX = 7;
  // Below this drawn width, the resize handles are hidden -- the two of them would otherwise cover the entire
  // selection, leaving no way to tell which edge is being grabbed. A selection that narrow is redrawn by dragging
  // out a new one instead.
  var MIN_HANDLE_WINDOW_PX = 18;
  // Largest half-width of the padding placed around a single-step selection, so the window reaches every trace's
  // data at that step without touching the neighboring ones.
  var MAX_STEP_PAD_SEC = 0.05;
  var PLAY_GLYPH = '▶';
  var PAUSE_GLYPH = '⏸';
  var SPEED_OPTIONS = [0.25, 0.5, 1, 2, 5, 10, 25, 50, 100];

  // Plotly stores large numeric arrays (e.g. lat/lon built from numpy arrays) internally as a typed-array wrapper
  // object (`{dtype, bdata, _inputArray}`) rather than a plain Array, so a real Array can't always be recovered with
  // trace.lat.slice() -- unwrap `_inputArray` (an array-like object keyed "0", "1", ... with a few extra
  // non-numeric metadata keys mixed in) and copy its numeric entries out by hand instead.
  function toPlainArray(value) {
    if (value == null) return null;
    if (Array.isArray(value)) return value.slice();
    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return null;
    var src = value.hasOwnProperty('_inputArray') ? value._inputArray : value;
    if (Array.isArray(src)) return src.slice();
    var out = [];
    for (var i = 0; src.hasOwnProperty(i); i++) out.push(src[i]);
    return out;
  }

  // Read a possibly-nested trace attribute named the way Plotly.restyle() addresses it ("marker.color").
  function getField(trace, path) {
    var parts = path.split('.');
    var value = trace;
    for (var i = 0; i < parts.length && value != null; i++) {
      value = value[parts[i]];
    }
    return value;
  }

  // Snapshot each trace's original per-point data before any restyle() call mutates figure.data in place --
  // narrowing/widening the window always re-filters from this pristine copy, never from what's currently displayed.
  // A field that isn't a per-point array (a single marker color shared by the whole trace, say) is recorded as
  // `null` and left alone by the filter.
  var ORIGINAL_TRACES = figure.data.map(function(trace) {
    var customdata = toPlainArray(trace.customdata);
    var times = [];
    if (customdata) {
      for (var j = 0; j < customdata.length; j++) {
        times.push(customdata[j][P1_TIME_CUSTOMDATA_INDEX]);
      }
    }

    var fields = {};
    POINT_FIELDS.forEach(function(path) {
      fields[path] = toPlainArray(getField(trace, path));
    });

    return {times: times, fields: fields, num_points: times.length};
  });

  // Group the plotted times into steps -- the individual moments in time the window can be snapped to, and
  // stepped through one at a time. These are the moments the figure actually holds a point for, which on a
  // decimated plot is far coarser than the rate the data was logged at.
  //
  // Traces don't necessarily carry the exact same timestamp for a given moment: a sky plot decimated to one point
  // per satellite every 30 seconds, for instance, has each satellite land on its own sample within that interval.
  // What separates two steps is therefore judged relative to how often a single trace is sampled -- times closer
  // together than a fraction of that are the same moment seen through different traces, not different moments.
  var STEPS = [];
  var STEP_PAD_SEC = MAX_STEP_PAD_SEC;
  var STEP_SPACING_SEC = 0;
  (function() {
    var diffs = [];
    var all = [];
    ORIGINAL_TRACES.forEach(function(trace) {
      var times = trace.times.filter(function(t) { return !isNaN(t); }).sort(function(a, b) { return a - b; });
      for (var i = 0; i < times.length; i++) {
        all.push(times[i]);
        if (i > 0 && times[i] > times[i - 1]) diffs.push(times[i] - times[i - 1]);
      }
    });
    if (all.length === 0) return;

    diffs.sort(function(a, b) { return a - b; });
    STEP_SPACING_SEC = diffs.length > 0 ? diffs[diffs.length >> 1] : 0;
    var tolerance_sec = Math.max(1e-4, 0.25 * STEP_SPACING_SEC);
    STEP_PAD_SEC = Math.max(1e-4, Math.min(MAX_STEP_PAD_SEC, 0.25 * tolerance_sec));

    all.sort(function(a, b) { return a - b; });
    for (var i = 0; i < all.length; i++) {
      var current = STEPS[STEPS.length - 1];
      if (current === undefined || all[i] - current.end > tolerance_sec) {
        STEPS.push({start: all[i], end: all[i], center: all[i]});
      } else {
        current.end = all[i];
        current.center = 0.5 * (current.start + current.end);
      }
    }
  })();

  // The X axis range currently drawn on the slider, narrowed by ctrl+scroll. Always within the full time range,
  // and independent of the selection window, which may extend beyond it.
  var view_min = P1_TIME_MIN;
  var view_max = P1_TIME_MAX;

  var mapContainer = figure.parentNode;

  var sliderContainer = document.createElement('div');
  sliderContainer.style.cssText = 'flex:0 0 ' + SLIDER_HEIGHT_PX + 'px; width:100%; box-sizing:border-box; ' +
    'padding:' + TRACK_PADDING_V_PX + 'px ' + TRACK_INSET_PX + 'px; background:' + PANEL_COLOR + '; ' +
    'border-top:1px solid #e4e4e1;';
  sliderContainer.title = 'Drag outside the selection to pick a new time range, or drag the selection to move it.\n' +
    'Double-click the selection to narrow it to a single step in time, and again to go back to the full range.\n' +
    'With a step selected, click anywhere on the track to jump to the step there.\n' +
    'Ctrl+scroll to zoom the time scale, shift+drag or shift+scroll to pan it, and double-click away from the\n' +
    'selection to fit the whole log back on it.\n' +
    'Left/right arrow keys step back and forth through the log, and space plays and pauses.';

  var trackDiv = document.createElement('div');
  trackDiv.style.cssText = 'position:relative; width:100%; height:100%; cursor:crosshair;';
  sliderContainer.appendChild(trackDiv);

  var canvas = document.createElement('canvas');
  canvas.style.cssText = 'position:absolute; left:0; top:0; width:100%; height:100%;';
  trackDiv.appendChild(canvas);

  // windowDiv (the draggable selection) only covers the plotted chart area, not the X axis label strip below it
  // (see drawProfile()), so the highlighted band lines up with the curve it's overlaid on.
  var windowDiv = document.createElement('div');
  windowDiv.style.cssText = 'position:absolute; top:0; bottom:' + X_AXIS_LABEL_PX + 'px; ' +
    'background:' + WINDOW_FILL + '; border:1px solid ' + ACCENT_COLOR + '; box-sizing:border-box; cursor:grab;';
  trackDiv.appendChild(windowDiv);

  // While a range is being dragged out, the part of the visible scale it leaves out is dimmed, the way Plotly's
  // own drag-to-zoom shows what a release would keep.
  var SHADE_CSS = 'position:absolute; top:0; bottom:' + X_AXIS_LABEL_PX + 'px; background:rgba(40,40,36,0.22); ' +
    'pointer-events:none; display:none;';
  var leftShade = document.createElement('div');
  leftShade.style.cssText = SHADE_CSS;
  trackDiv.appendChild(leftShade);

  var rightShade = document.createElement('div');
  rightShade.style.cssText = SHADE_CSS;
  trackDiv.appendChild(rightShade);

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

  // Playback controls, plus a text echo of the current window in the same time-type-aware format as the axis ticks
  // -- the readout lets the current range be read precisely (and copy-pasted) without having to eyeball tick
  // positions.
  var controlsDiv = document.createElement('div');
  controlsDiv.style.cssText = 'flex:0 0 ' + READOUT_HEIGHT_PX + 'px; width:100%; box-sizing:border-box; ' +
    'display:flex; align-items:center; gap:6px; padding:2px ' + TRACK_INSET_PX + 'px; ' +
    'background:' + PANEL_COLOR + '; ' +
    'font:12px -apple-system, "Segoe UI", Roboto, sans-serif;';
  mapContainer.appendChild(controlsDiv);

  var playButton = document.createElement('button');
  playButton.type = 'button';
  playButton.textContent = PLAY_GLYPH;
  playButton.style.cssText = 'flex:0 0 auto; width:26px; height:20px; padding:0; line-height:1; cursor:pointer; ' +
    'border:1px solid #c9c9c4; border-radius:3px; background:#f7f7f5; color:#3a3a36; font-size:11px;';
  controlsDiv.appendChild(playButton);

  var speedSelect = document.createElement('select');
  speedSelect.style.cssText = 'flex:0 0 auto; height:20px; padding:0 2px; cursor:pointer; ' +
    'border:1px solid #c9c9c4; border-radius:3px; background:#f7f7f5; color:#3a3a36; font-size:11px;';
  speedSelect.title = 'Playback speed, as a multiple of real time.';
  // A sky plot decimated to one point every 30 seconds would sit on the same frame for half a minute at real
  // time, which reads as broken rather than slow. Start at the slowest speed of at least real time that advances
  // about once a second, which leaves plots sampled faster than that at 1x.
  var DEFAULT_SPEED = SPEED_OPTIONS[SPEED_OPTIONS.length - 1];
  for (var si = 0; si < SPEED_OPTIONS.length; si++) {
    if (SPEED_OPTIONS[si] >= 1 && STEP_SPACING_SEC / SPEED_OPTIONS[si] <= 1.0) {
      DEFAULT_SPEED = SPEED_OPTIONS[si];
      break;
    }
  }

  SPEED_OPTIONS.forEach(function(speed) {
    var option = document.createElement('option');
    option.value = String(speed);
    option.textContent = speed + 'x';
    if (speed === DEFAULT_SPEED) option.selected = true;
    speedSelect.appendChild(option);
  });
  controlsDiv.appendChild(speedSelect);

  var readoutDiv = document.createElement('div');
  readoutDiv.style.cssText = 'flex:1 1 auto; color:' + ACCENT_COLOR + '; overflow:hidden; white-space:nowrap;';
  controlsDiv.appendChild(readoutDiv);

  // Anything the figure needs to say about the times it holds sits at the far end of the row, next to the controls
  // that move between them -- a plot showing one point per 30 seconds, say, otherwise looks like it is stepping
  // through the log far too coarsely.
  if (NOTE) {
    var noteDiv = document.createElement('div');
    noteDiv.style.cssText = 'flex:0 0 auto; color:#6b6b66; overflow:hidden; white-space:nowrap;';
    noteDiv.textContent = NOTE;
    controlsDiv.appendChild(noteDiv);
  }

  function timeToFrac(t) { return (t - view_min) / (view_max - view_min); }
  function fracToTime(f) { return view_min + f * (view_max - view_min); }

  function pixelToTime(clientX) {
    var rect = trackDiv.getBoundingClientRect();
    // The track has no width to measure against until it has been laid out, and dividing by it there would put a
    // NaN into the window bounds that nothing afterwards could recover from.
    var frac = (rect.width > 0) ? (clientX - rect.left) / rect.width : 0;
    return Math.min(P1_TIME_MAX, Math.max(P1_TIME_MIN, fracToTime(frac)));
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
  // aren't related by a fixed offset (see Analyzer._time_slider_js() docstring) but P1 time should be rate-locked
  // to GPS time when it is available.
  //
  // For timeline purposes, displayed timestamps don't need to be precise. Before GPS time is known, extrapolate
  // assuming P1 time tracks real elapsed time 1:1 -- it does not, but this is a good enough approximation for a
  // while.
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

  // Number of fractional second digits to show, based on how much time the axis currently spans -- a tenth of a
  // second reads fine across a whole log, but says nothing once ctrl+scroll has zoomed in to a few seconds.
  function tickDecimals() {
    var span = view_max - view_min;
    if (span < 1.0) return 3;
    if (span < 20.0) return 2;
    return 1;
  }

  // Split a P1 time into UTC calendar date + time-of-day, for the tick loop below to decide when a date needs to
  // be shown (first tick, or a tick that landed on a different day than the previous one). Returns null if UTC
  // can't be resolved (no GPS/POSIX offset, or no profile data to interpolate GPS time from).
  function utcPartsForP1(p1, decimals) {
    var gps = p1ToGpsTime(p1);
    if (isNaN(gps) || typeof gps_posix_offset_sec !== 'number') {
      return null;
    }
    var iso = new Date((gps + gps_posix_offset_sec) * 1000.0).toISOString();
    var time = ((decimals === undefined ? tickDecimals() : decimals) > 1) ? iso.substr(11, 12) : iso.substr(11, 8);
    return {date: iso.slice(0, 10).split('-').join('/'), time: time};
  }

  // Match the X axis format used by the log's other time-series plots (see Analyzer.time_type / _resolve_x_axis()).
  // The domain label ("Rel:", "P1:", "GPS:") only needs to appear once, on the first tick -- it's the same for
  // every tick after that.
  function formatTickLabel(p1, is_first, decimals) {
    if (decimals === undefined) decimals = tickDecimals();
    if (time_axis_type === 'relative') {
      var s = (p1 - (p1_t0_sec || 0)).toFixed(decimals) + ' s';
      return is_first ? 'Rel: ' + s : s;
    }
    if (time_axis_type === 'p1') {
      var s = p1.toFixed(decimals) + ' s';
      return is_first ? 'P1: ' + s : s;
    }
    if (time_axis_type === 'gps') {
      var gps = p1ToGpsTime(p1);
      // GPS time may not be available at the start of the timeline if we have to extrapolate backward for a very long
      // time. Rather than silently showing a bare number that looks like a GPS value but isn't, label it as what it
      // actually is.
      if (isNaN(gps)) {
        return 'P1: ' + p1.toFixed(decimals) + ' s';
      }
      var week = Math.floor(gps / SECONDS_PER_WEEK);
      var tow_sec = gps - week * SECONDS_PER_WEEK;
      var s = week + ':' + tow_sec.toFixed(decimals);
      return is_first ? 'GPS: ' + s : s;
    }
    // 'utc' -- no date-change context here (see the tick loop's own UTC handling below), just the time of day.
    var parts = utcPartsForP1(p1, decimals);
    return parts ? parts.time : 'P1: ' + p1.toFixed(decimals) + ' s';
  }

  // The track's own width, remeasured only when it actually changes (see the ResizeObserver below). Measuring it
  // forces the browser to flush a layout it is otherwise free to defer, which is not something to ask for on every
  // animation frame of a playback running alongside a figure the user is trying to drag.
  var trackWidthPx = 1;

  // The background chart is broken wherever the data behind it stops for longer than this, so that a stretch of
  // the log holding nothing reads as missing rather than as a straight line drawn across it. A single missing
  // sample is enough to count, with room left over for the spacing to wobble.
  var PROFILE_GAP_FACTOR = 1.75;
  var PROFILE_GAP_SEC = (function() {
    if (PROFILE_TIME.length < 3) return Infinity;

    var diffs = [];
    for (var i = 1; i < PROFILE_TIME.length; i++) diffs.push(PROFILE_TIME[i] - PROFILE_TIME[i - 1]);
    diffs.sort(function(a, b) { return a - b; });
    return Math.max(1e-6, PROFILE_GAP_FACTOR * diffs[diffs.length >> 1]);
  })();

  function resizeCanvas() {
    var rect = trackDiv.getBoundingClientRect();
    var dpr = window.devicePixelRatio || 1;
    trackWidthPx = rect.width || 1;
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

    // Every series shares one scale, so that they can be read against each other.
    var maxValue = 0;
    PROFILE_SERIES.forEach(function(series) {
      for (var i = 0; i < series.values.length; i++) {
        if (series.values[i] > maxValue) maxValue = series.values[i];
      }
    });
    maxValue = Math.max(1, Math.ceil(maxValue));

    function x(time) { return timeToFrac(time) * w; }
    function y(value) { return chartH - (value / maxValue) * chartH; }

    // A curve is drawn across the whole time range and simply clipped by the canvas when the X axis is zoomed
    // in, and lifts over any gap in the data behind it (see PROFILE_GAP_SEC).
    function drawSeries(series) {
      // A sample with a gap on either side of it has no line to be part of, so it gets a dot of its own.
      var dot_px = Math.max(1, 1.4 * dpr);
      function drawIsolated(i) { ctx.fillRect(x(PROFILE_TIME[i]) - dot_px, y(series.values[i]) - dot_px,
                                              2 * dot_px, 2 * dot_px); }

      ctx.strokeStyle = series.color;
      ctx.fillStyle = series.color;
      ctx.lineWidth = Math.max(1, 1.4 * dpr);
      ctx.beginPath();

      var run_length = 0;
      for (var i = 0; i < PROFILE_TIME.length; i++) {
        if (i > 0 && PROFILE_TIME[i] - PROFILE_TIME[i - 1] <= PROFILE_GAP_SEC) {
          ctx.lineTo(x(PROFILE_TIME[i]), y(series.values[i]));
          run_length++;
        } else {
          if (run_length === 1) drawIsolated(i - 1);
          ctx.moveTo(x(PROFILE_TIME[i]), y(series.values[i]));
          run_length = 1;
        }
      }
      if (run_length === 1) drawIsolated(PROFILE_TIME.length - 1);

      ctx.stroke();
    }

    if (PROFILE_TIME.length >= 2) {
      PROFILE_SERIES.forEach(drawSeries);
    }

    // Y axis context - 0 at the bottom, ceil(max) at the top.
    ctx.fillStyle = '#6b6b66';
    ctx.font = Math.round(10 * dpr) + 'px sans-serif';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText(maxValue + ' ' + PROFILE_UNITS, 4 * dpr, 3 * dpr);
    ctx.textBaseline = 'alphabetic';

    // Name the curves along the bottom, each in its own color, where there is more than one to tell apart. The
    // chart's low end is the emptiest part of it, so the names sit next to the zero label rather than over the
    // curves they belong to.
    var label_x = 4 * dpr;
    function drawLabel(text, color) {
      ctx.fillStyle = color;
      ctx.fillText(text, label_x, chartH - 3 * dpr);
      label_x += ctx.measureText(text).width + 8 * dpr;
    }

    drawLabel('0 ' + PROFILE_UNITS, '#6b6b66');
    PROFILE_SERIES.forEach(function(series) {
      if (series.label) drawLabel(series.label, series.color);
    });

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
          label = 'P1: ' + p1.toFixed(tickDecimals()) + ' s';
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
  // Index into STEPS of the step the window is locked to, or -1 when the window is a free time range.
  var stepIndex = -1;

  // Index of the step nearest a given time.
  function nearestStepIndex(t) {
    var n = STEPS.length;
    if (n === 0) return -1;
    var lo = 0, hi = n - 1;
    while (hi - lo > 1) {
      var mid = (lo + hi) >> 1;
      if (STEPS[mid].center <= t) lo = mid; else hi = mid;
    }
    return (Math.abs(STEPS[hi].center - t) < Math.abs(t - STEPS[lo].center)) ? hi : lo;
  }

  // Index of the last step at or before a given time, for stepping forward during playback.
  function stepIndexAtOrBefore(t) {
    var i = nearestStepIndex(t);
    if (i > 0 && STEPS[i].center > t) i--;
    return i;
  }

  // Narrow the window to a single step.
  function setStepWindow(index) {
    stepIndex = Math.max(0, Math.min(STEPS.length - 1, index));
    winStart = STEPS[stepIndex].start - STEP_PAD_SEC;
    winEnd = STEPS[stepIndex].end + STEP_PAD_SEC;
    scheduleFilter();
  }

  function resetWindow() {
    stepIndex = -1;
    winStart = P1_TIME_MIN;
    winEnd = P1_TIME_MAX;
    scheduleFilter();
  }

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

  // Neither side gets a "Rel:"/"P1:"/"GPS:"/"UTC:" prefix here -- "Displaying" already establishes these are times,
  // and the axis ticks above spell out which domain -- *unless* GPS/UTC time isn't actually available for that
  // particular value (e.g. before first fix), in which case it falls back to an explicitly-labeled "P1: ..."
  // reading instead of a bare number that looks like it's in the axis's domain but isn't. In 'utc' mode, the end
  // date is only repeated if it actually differs from the start's (mirrors the axis ticks' own midnight-crossing
  // rule, just for these two values) -- unless the start itself fell back to P1, in which case there's no prior
  // date to compare against, so the end always shows its date too.
  function formatRangeReadout() {
    var held_text = isPlaybackHeld() ? ' | Paused while the plot is moved' : '';

    if (stepIndex >= 0) {
      // A single step is worth reading to the millisecond, however coarse the axis ticks currently are.
      return 'Step ' + (stepIndex + 1) + ' of ' + STEPS.length + ': ' +
             formatTickLabel(STEPS[stepIndex].center, false, 3) + held_text;
    }

    var rangeText;
    if (time_axis_type === 'utc') {
      var p0 = utcPartsForP1(winStart);
      var p1 = utcPartsForP1(winEnd);
      var startText = p0 ? (p0.date + ' ' + p0.time) : ('P1: ' + winStart.toFixed(tickDecimals()) + ' s');
      var endText;
      if (p1 === null) {
        endText = 'P1: ' + winEnd.toFixed(tickDecimals()) + ' s';
      } else if (p0 === null || p1.date !== p0.date) {
        endText = p1.date + ' ' + p1.time;
      } else {
        endText = p1.time;
      }
      rangeText = startText + ' → ' + endText;
    } else {
      rangeText = formatTickLabel(winStart, false) + ' - ' + formatTickLabel(winEnd, false);
    }
    return 'Displaying: ' + rangeText + ' | Duration: ' + formatDuration(winEnd - winStart) + held_text;
  }

  // `true` when the selection is wide enough to draw usable resize handles on.
  var handles_fit = false;
  // `true` while a selection is being dragged out, which is when the unselected part of the scale is dimmed.
  var dragSelecting = false;

  // Round a CSS pixel offset to a whole device pixel. The selection's left and right edges are drawn from two
  // separate style values, so at fractional offsets the browser snaps each of them to the pixel grid on its own
  // and they appear to step at different moments as the window slides. Rounding the position and the width
  // separately keeps the width fixed while the window moves, so both edges step together.
  function snapToDevicePixel(offset_px) {
    var dpr = window.devicePixelRatio || 1;
    return Math.round(offset_px * dpr) / dpr;
  }

  var drawnLeft = null, drawnWidth = null, drawnHeld = null;

  function updateHeldStyle() {
    var held = !!isPlaybackHeld();
    if (held === drawnHeld) return;
    drawnHeld = held;

    var color = held ? HELD_COLOR : ACCENT_COLOR;
    windowDiv.style.borderColor = color;
    windowDiv.style.background = held ? HELD_WINDOW_FILL : WINDOW_FILL;
    leftHandle.style.background = color;
    rightHandle.style.background = color;
    readoutDiv.style.color = color;
    sliderContainer.style.background = held ? HELD_PANEL_COLOR : PANEL_COLOR;
    controlsDiv.style.background = held ? HELD_PANEL_COLOR : PANEL_COLOR;
  }

  function updateWindowDivStyle() {
    var width_px = trackWidthPx;
    var x0 = timeToFrac(winStart) * width_px;
    var x1 = timeToFrac(winEnd) * width_px;
    handles_fit = (x1 - x0) >= MIN_HANDLE_WINDOW_PX;

    // Draw a too-narrow selection at a fixed minimum width, centered on where it really is, so it stays visible
    // and grabbable no matter how little time it covers.
    if (x1 - x0 < MIN_WINDOW_PX) {
      var center = 0.5 * (x0 + x1);
      x0 = center - 0.5 * MIN_WINDOW_PX;
      x1 = center + 0.5 * MIN_WINDOW_PX;
    }

    // The selection can extend past either end of a zoomed-in axis. Clip it to the track, and hide the handle for
    // any edge that isn't on screen so it can't be dragged from a position it isn't actually at.
    var clipped_x0 = Math.max(0, x0);
    var clipped_x1 = Math.min(width_px, x1);
    var left = snapToDevicePixel(clipped_x0);
    var width = snapToDevicePixel(Math.max(0, clipped_x1 - clipped_x0));
    windowDiv.style.display = (clipped_x1 <= clipped_x0) ? 'none' : '';
    if (left !== drawnLeft) {
      windowDiv.style.left = left + 'px';
      drawnLeft = left;
    }
    if (width !== drawnWidth) {
      windowDiv.style.width = width + 'px';
      drawnWidth = width;
    }
    leftHandle.style.display = (handles_fit && x0 >= 0 && x0 <= width_px) ? '' : 'none';
    rightHandle.style.display = (handles_fit && x1 >= 0 && x1 <= width_px) ? '' : 'none';

    // A selection covering the whole log has nowhere to slide, so dragging it picks out a new range instead.
    windowDiv.style.cursor = isFullRangeWindow() ? 'crosshair' : (dragMode === 'move' ? 'grabbing' : 'grab');

    leftShade.style.display = dragSelecting ? '' : 'none';
    rightShade.style.display = dragSelecting ? '' : 'none';
    if (dragSelecting) {
      leftShade.style.left = '0px';
      leftShade.style.width = Math.max(0, clipped_x0) + 'px';
      rightShade.style.left = clipped_x1 + 'px';
      rightShade.style.width = Math.max(0, width_px - clipped_x1) + 'px';
    }

    readoutDiv.textContent = formatRangeReadout();
    updateHeldStyle();
    updatePlayEnabled();
  }

  function sliceField(source, keep, path) {
    // A trace with a genuinely empty data array gets dropped from the legend entirely -- making a solution type
    // (or satellite) that just has no points in *this* window look like it never had any data at all. Plot a
    // single placeholder point instead, matching the convention the plots themselves use for data that is
    // missing from the whole log, so narrowing the window never makes legend entries disappear.
    //
    // The NaN in whichever fields position the point is what keeps it from being drawn. Every other field needs
    // a value the figure will actually accept, so those take one the trace already carries -- a NaN marker
    // symbol, for one, is not a symbol Plotly can draw, and it throws partway through the redraw rather than
    // falling back to a default.
    if (keep.length === 0) {
      if (path === 'customdata' || source.length === 0) return [];
      return [typeof source[0] === 'number' ? NaN : source[0]];
    }

    var out = new Array(keep.length);
    for (var i = 0; i < keep.length; i++) out[i] = source[keep[i]];
    return out;
  }

  // Number of restyle events still expected from our own filtering, so the hook that watches for figure-driven
  // style changes (see below) doesn't react to the filter's own output.
  var pending_self_restyles = 0;

  // Re-slice from ORIGINAL_TRACES (not figure.data) so widening the window can bring back points a previous
  // restyle() dropped.
  function applyFilter() {
    var started_ms = performance.now();
    var traceIndices = [];
    var update = {};
    POINT_FIELDS.forEach(function(path) { update[path] = []; });

    for (var i = 0; i < ORIGINAL_TRACES.length; i++) {
      var orig = ORIGINAL_TRACES[i];
      if (orig.num_points === 0) continue;

      var keep = [];
      for (var j = 0; j < orig.times.length; j++) {
        if (orig.times[j] >= winStart && orig.times[j] <= winEnd) keep.push(j);
      }

      traceIndices.push(i);
      POINT_FIELDS.forEach(function(path) {
        // A field this trace doesn't store per point is rewritten with the value it already has, so that every
        // field can be restyled in one pass without disturbing the traces it doesn't apply to.
        var source = orig.fields[path];
        update[path].push(source === null ? getField(figure.data[i], path) : sliceField(source, keep, path));
      });
    }

    if (traceIndices.length > 0) {
      pending_self_restyles++;
      try {
        Plotly.restyle(figure, update, traceIndices);
      } catch (e) {
        pending_self_restyles--;
        throw e;
      }
    }

    // Redrawing a figure holding a lot of points can take tens of milliseconds, and running one redraw per
    // animation frame leaves the figure's own pan and zoom nothing to run in. Hold the next redraw off for a
    // multiple of however long this one took, so that however heavy the figure is, most of the time is still the
    // browser's to spend on whatever the user is doing with it.
    lastFilterMs = performance.now();
    filterIntervalMs = Math.min(MAX_FILTER_INTERVAL_MS,
                                Math.max(MIN_FILTER_INTERVAL_MS,
                                         FILTER_DUTY_CYCLE * (lastFilterMs - started_ms)));
  }

  var MIN_FILTER_INTERVAL_MS = 16;
  var MAX_FILTER_INTERVAL_MS = 250;
  var FILTER_DUTY_CYCLE = 4;
  var filterIntervalMs = MIN_FILTER_INTERVAL_MS;
  var lastFilterMs = -Infinity;
  var pendingFilter = null;

  // How long after the figure was last panned or zoomed to treat the gesture as still going.
  var FIGURE_SETTLE_MS = 150;
  var lastFigureMoveMs = -Infinity;
  var figurePointerDown = false;

  // Only a figure the pointer drags a view around in has anything to be disturbed by a redraw landing mid-drag.
  // Where it does, a drag reports nothing until it has actually moved, and a redraw in that gap takes the data
  // layers out from under the gesture, dropping it for good rather than merely stuttering it -- hence watching for
  // the press itself, not just for the movement it goes on to report.
  if (HAS_DRAGGABLE_VIEW) {
    figure.on('plotly_relayouting', function() { lastFigureMoveMs = performance.now(); });

    figure.addEventListener('pointerdown', function() {
      figurePointerDown = true;
      updateWindowDivStyle();
    });

    ['pointerup', 'pointercancel'].forEach(function(name) {
      document.addEventListener(name, function() {
        if (!figurePointerDown) return;
        figurePointerDown = false;
        lastFigureMoveMs = performance.now();
      });
    });
  }

  function isFigureBusy() {
    return figurePointerDown || (performance.now() - lastFigureMoveMs) < FIGURE_SETTLE_MS;
  }

  // Redraws are held while the figure is being moved, so playback holds with them. Letting the clock run on
  // against a figure that isn't being redrawn to match would read as the vehicle having stopped there, which is
  // worse than briefly not advancing at all.
  function isPlaybackHeld() {
    return playing && isFigureBusy();
  }

  // The slider itself is redrawn right away -- it is a handful of style writes, and it is what the pointer is
  // following. The figure is rate-limited (see applyFilter()), leading edge first so that a one-off change lands
  // immediately rather than waiting out an interval set by some earlier redraw.
  function scheduleFilter() {
    updateWindowDivStyle();
    if (pendingFilter !== null) return;
    pendingFilter = setTimeout(runFilter, Math.max(0, filterIntervalMs - (performance.now() - lastFilterMs)));
  }

  function runFilter() {
    // Let the figure's own pan or zoom finish first (see isFigureBusy()).
    if (isFigureBusy()) {
      pendingFilter = setTimeout(runFilter, FIGURE_SETTLE_MS);
      return;
    }

    pendingFilter = null;
    applyFilter();
  }

  // The figure's own controls can rewrite a filtered field out from under us -- the sky plot's "Color By C/N0"
  // button, for instance, restyles in a full-length per-point color array. Re-snapshot whatever came back at full
  // length and re-apply the window, otherwise those values would line up against the wrong points.
  function recaptureFields() {
    for (var i = 0; i < ORIGINAL_TRACES.length; i++) {
      var orig = ORIGINAL_TRACES[i];
      POINT_FIELDS.forEach(function(path) {
        var value = toPlainArray(getField(figure.data[i], path));
        if (value === null) {
          // No longer stored per point (a single color for the whole trace, say).
          orig.fields[path] = null;
        } else if (value.length === orig.num_points) {
          orig.fields[path] = value;
        }
        // Anything shorter is the filter's own output, so keep the snapshot we already have.
      });
    }
  }

  figure.on('plotly_restyle', function(event) {
    if (pending_self_restyles > 0) {
      pending_self_restyles--;
      return;
    }

    var update = (event && event[0]) || {};
    var touches_filtered_field = Object.keys(update).some(function(key) {
      return POINT_FIELDS.some(function(path) {
        return path === key || path.indexOf(key + '.') === 0 || key.indexOf(path + '.') === 0;
      });
    });
    if (!touches_filtered_field) return;

    recaptureFields();
    applyFilter();
  });

  var dragMode = null, dragStartX = 0, dragWinStart = 0, dragWinEnd = 0, dragViewMin = 0, dragViewMax = 0;
  // How far the cursor has to travel before a press counts as a drag rather than a click, so that a click that
  // wanders by a pixel doesn't wipe out the current range.
  var SELECT_DRAG_THRESHOLD_PX = 3;
  // `true` once the press has travelled that far.
  var dragMoved = false;

  function onPointerMove(evt) {
    if (!dragMode) return;

    // Nothing a drag computes means anything until the track has been laid out and has a width to measure
    // against.
    var rect = trackDiv.getBoundingClientRect();
    if (rect.width <= 0) return;

    if (Math.abs(evt.clientX - dragStartX) >= SELECT_DRAG_THRESHOLD_PX) dragMoved = true;

    if (dragMode === 'view') {
      var view_span = dragViewMax - dragViewMin;
      var view_delta_sec = ((evt.clientX - dragStartX) / rect.width) * view_span;
      setViewRange(dragViewMin - view_delta_sec, dragViewMax - view_delta_sec);
      return;
    }

    if (dragMode === 'left') {
      stepIndex = -1;
      winStart = Math.max(P1_TIME_MIN, Math.min(pixelToTime(evt.clientX), winEnd - MIN_WINDOW_SEC));
    } else if (dragMode === 'right') {
      stepIndex = -1;
      winEnd = Math.min(P1_TIME_MAX, Math.max(pixelToTime(evt.clientX), winStart + MIN_WINDOW_SEC));
    } else if (dragMode === 'move') {
      var delta_sec = ((evt.clientX - dragStartX) / rect.width) * (view_max - view_min);
      // A window locked to a single step stays locked while it's dragged, moving from step to step as the
      // cursor passes them rather than sliding off the data entirely.
      if (stepIndex >= 0) {
        setStepWindow(nearestStepIndex(0.5 * (dragWinStart + dragWinEnd) + delta_sec));
        return;
      }

      var width = dragWinEnd - dragWinStart;
      var newStart = dragWinStart + delta_sec, newEnd = dragWinEnd + delta_sec;
      if (newStart < P1_TIME_MIN) { newStart = P1_TIME_MIN; newEnd = newStart + width; }
      if (newEnd > P1_TIME_MAX) { newEnd = P1_TIME_MAX; newStart = newEnd - width; }
      winStart = newStart;
      winEnd = newEnd;
    } else if (dragMode === 'select') {
      if (!dragSelecting && !dragMoved) return;
      dragSelecting = true;
      stepIndex = -1;

      var from = pixelToTime(dragStartX), to = pixelToTime(evt.clientX);
      winStart = Math.min(from, to);
      winEnd = Math.max(winStart + MIN_WINDOW_SEC, Math.max(from, to));
    }
    scheduleFilter();
  }

  function onPointerUp(evt) {
    // A click while a single step is selected jumps straight to the step under the cursor, rather than having to
    // walk to it. Playback, if running, carries on from there.
    if (!dragMoved && dragMode !== 'view' && stepIndex >= 0) {
      setStepWindow(nearestStepIndex(pixelToTime(evt.clientX)));
    }

    dragMode = null;
    dragSelecting = false;
    dragMoved = false;
    reseatPlayback();
    updateWindowDivStyle();
    document.removeEventListener('mousemove', onPointerMove);
    document.removeEventListener('mouseup', onPointerUp);
  }

  function beginDrag(mode) {
    return function(evt) {
      evt.preventDefault();
      evt.stopPropagation();
      dragMode = mode;
      dragMoved = false;
      dragStartX = evt.clientX;
      dragWinStart = winStart;
      dragWinEnd = winEnd;
      dragViewMin = view_min;
      dragViewMax = view_max;
      document.addEventListener('mousemove', onPointerMove);
      document.addEventListener('mouseup', onPointerUp);
    };
  }

  leftHandle.addEventListener('mousedown', beginDrag('left'));
  rightHandle.addEventListener('mousedown', beginDrag('right'));
  // Dragging from inside the selection slides it through the log, and dragging from anywhere else on the track
  // picks out a new range -- except when the selection already covers the whole log, where there is nothing to
  // slide and any drag is a new range. Holding shift pans the time scale instead, which only does anything once
  // ctrl+scroll has zoomed in far enough that there is something off screen to pan to.
  trackDiv.addEventListener('mousedown', function(evt) {
    if (evt.target === leftHandle || evt.target === rightHandle) return;
    if (evt.shiftKey) {
      beginDrag('view')(evt);
      return;
    }

    var from_selection = (evt.target === windowDiv) && !isFullRangeWindow();
    beginDrag(from_selection ? 'move' : 'select')(evt);
  });

  // Double-clicking the selection picks out the single step under the cursor, and double-clicking it again goes
  // back to the whole log -- on the sky plot in particular, where each step is an independent snapshot of the sky,
  // that makes it possible to walk through the log and watch the constellation change.
  //
  // Away from the selection, double-clicking puts the whole log back on the time scale, the way double-clicking a
  // Plotly figure undoes a zoom. That leaves the selection itself alone, and is how a selection that a zoom left
  // off screen is found again.
  trackDiv.addEventListener('dblclick', function(evt) {
    var on_selection = (evt.target === windowDiv || evt.target === leftHandle || evt.target === rightHandle);
    if (!on_selection && isScaleZoomedIn()) {
      setViewRange(P1_TIME_MIN, P1_TIME_MAX);
      return;
    }

    if (stepIndex >= 0 || STEPS.length === 0) {
      resetWindow();
    } else {
      setStepWindow(nearestStepIndex(pixelToTime(evt.clientX)));
    }
    reseatPlayback();
  });

  // `true` when the time scale shows less than the whole log, so there is something off screen.
  function isScaleZoomedIn() {
    return (view_max - view_min) < (P1_TIME_MAX - P1_TIME_MIN) - 1e-9;
  }

  function setViewRange(new_min, new_max) {
    var span = Math.min(P1_TIME_MAX - P1_TIME_MIN, Math.max(MIN_VIEW_SPAN_SEC, new_max - new_min));
    view_min = new_min;
    view_max = new_min + span;
    if (view_min < P1_TIME_MIN) { view_min = P1_TIME_MIN; view_max = view_min + span; }
    if (view_max > P1_TIME_MAX) { view_max = P1_TIME_MAX; view_min = view_max - span; }
    resizeCanvas();
    updateWindowDivStyle();
  }

  // Ctrl+scroll zooms the time scale about the cursor, so a range can be picked far more precisely than the full
  // log's worth of pixels allows. Shift+scroll, or a horizontal scroll, pans a zoomed-in scale. A plain vertical
  // scroll is left alone for scrolling the page.
  trackDiv.addEventListener('wheel', function(evt) {
    var is_horizontal = Math.abs(evt.deltaX) > Math.abs(evt.deltaY);
    var zooming = evt.ctrlKey || evt.metaKey;
    if (!zooming && !evt.shiftKey && !is_horizontal) return;
    evt.preventDefault();

    // The delta comes in lines or pages rather than pixels on some browsers, so scale it back to a comparable
    // number of pixels before using it as a rate. A shifted scroll is reported on whichever axis the device
    // decided to put it on.
    var delta = is_horizontal ? evt.deltaX : evt.deltaY;
    var delta_px = delta * (evt.deltaMode === 1 ? 16 : evt.deltaMode === 2 ? 400 : 1);
    var span = view_max - view_min;

    if (zooming) {
      var anchor = pixelToTime(evt.clientX);
      var anchorFrac = timeToFrac(anchor);
      var zoomed_span = Math.min(P1_TIME_MAX - P1_TIME_MIN,
                                 Math.max(MIN_VIEW_SPAN_SEC, span * Math.exp(delta_px * 0.002)));
      setViewRange(anchor - anchorFrac * zoomed_span, anchor - anchorFrac * zoomed_span + zoomed_span);
    } else {
      var shift_sec = (delta_px / trackWidthPx) * span;
      setViewRange(view_min + shift_sec, view_max + shift_sec);
    }
  }, {passive: false});

  // Playback: a virtual clock runs forward through the log at the selected multiple of real time, dragging the
  // window along with it. A window locked to a single step jumps from step to step as the clock reaches them, so
  // the figure always shows one complete step rather than a partial blend of two. The time scale stays where
  // it was left, so on a zoomed-in scale the window simply passes through the visible stretch of the log.
  var playing = false;
  var playTime = 0;
  var lastFrameMs = 0;
  var animationHandle = null;

  // `true` when the window spans the whole log, so there is no room left to slide it.
  function isFullRangeWindow() {
    return (winEnd - winStart) >= (P1_TIME_MAX - P1_TIME_MIN) - 1e-9;
  }

  function canPlay() {
    return STEPS.length > 0 || !isFullRangeWindow();
  }

  var playEnabled = null;

  function updatePlayEnabled() {
    var enabled = canPlay();
    if (enabled === playEnabled) return;
    playEnabled = enabled;

    playButton.disabled = !enabled;
    playButton.style.opacity = enabled ? '1' : '0.4';
    playButton.style.cursor = enabled ? 'pointer' : 'default';
    playButton.title = enabled ? 'Animate the displayed time range forward through the log (space bar).' :
      'There is nothing to animate.';
  }

  // Pick playback up from wherever the window is now. Choosing a range while it runs carries on from there rather
  // than snapping back to where the clock had got to, so only the space bar and the play button stop it.
  function reseatPlayback() {
    if (!playing) return;

    // Selecting the whole log leaves nothing to animate, so let playback end there rather than sit frozen.
    if (stepIndex < 0 && isFullRangeWindow()) {
      stopPlayback();
      return;
    }

    playTime = (stepIndex >= 0) ? STEPS[stepIndex].center : winStart;
  }

  function onFrame(nowMs) {
    if (!playing) return;

    // Hold the clock while the window is being dragged, so that playback isn't fighting the drag for it, and
    // while the figure is being moved (see isPlaybackHeld()). The readout is still refreshed, since what it says
    // changes when playback goes on hold.
    if (dragMode !== null || isFigureBusy()) {
      lastFrameMs = nowMs;
      updateWindowDivStyle();
      animationHandle = requestAnimationFrame(onFrame);
      return;
    }

    // Cap the step so returning to a backgrounded tab doesn't jump the whole log at once.
    var dt_sec = Math.min(0.25, (nowMs - lastFrameMs) / 1000.0);
    lastFrameMs = nowMs;
    playTime += dt_sec * parseFloat(speedSelect.value);

    // Playback runs to the end of the log and stops there, leaving the last of it on screen. Starting over is
    // the play button again, from wherever the window is left.
    if (stepIndex >= 0) {
      var last_step = STEPS.length - 1;
      var index = Math.min(last_step, stepIndexAtOrBefore(playTime));
      if (index !== stepIndex) setStepWindow(index);
      if (playTime >= STEPS[last_step].center) {
        stopPlayback();
        return;
      }
    } else {
      var width = winEnd - winStart;
      winStart = Math.min(playTime, P1_TIME_MAX - width);
      winEnd = winStart + width;
      scheduleFilter();
      if (playTime >= P1_TIME_MAX - width) {
        stopPlayback();
        return;
      }
    }

    animationHandle = requestAnimationFrame(onFrame);
  }

  function startPlayback() {
    if (playing || !canPlay()) return;
    // With the whole log selected there is nothing to slide, so step through it one step at a time instead.
    if (stepIndex < 0 && isFullRangeWindow()) {
      setStepWindow(0);
    }
    playing = true;
    playTime = (stepIndex >= 0) ? STEPS[stepIndex].center : winStart;
    lastFrameMs = performance.now();
    playButton.textContent = PAUSE_GLYPH;
    animationHandle = requestAnimationFrame(onFrame);
  }

  function stopPlayback() {
    if (!playing) return;
    playing = false;
    if (animationHandle !== null) cancelAnimationFrame(animationHandle);
    animationHandle = null;
    playButton.textContent = PLAY_GLYPH;
  }

  function togglePlayback() {
    if (playing) stopPlayback(); else startPlayback();
  }

  playButton.addEventListener('click', togglePlayback);

  // Step the window back and forth with the arrow keys: one step at a time when it is locked to a single step,
  // otherwise a tenth of its own width, which stays a useful step whatever range is selected. The figure's pages
  // don't scroll, so the arrow keys and the space bar have nothing else to do here.
  var ARROW_STEP_FRACTION = 0.1;

  function stepWindow(direction) {
    if (stepIndex >= 0) {
      setStepWindow(stepIndex + direction);
      reseatPlayback();
      return;
    }

    // As in startPlayback(), a window covering the whole log has nowhere to slide to, so start stepping through
    // its steps from whichever end the key is heading away from.
    if (isFullRangeWindow() && STEPS.length > 0) {
      setStepWindow(direction > 0 ? 0 : STEPS.length - 1);
      reseatPlayback();
      return;
    }

    var width = winEnd - winStart;
    var step_sec = direction * ARROW_STEP_FRACTION * width;
    winStart = Math.max(P1_TIME_MIN, Math.min(P1_TIME_MAX - width, winStart + step_sec));
    winEnd = winStart + width;
    reseatPlayback();
    scheduleFilter();
  }

  document.addEventListener('keydown', function(evt) {
    var is_arrow = (evt.key === 'ArrowLeft' || evt.key === 'ArrowRight');
    var is_space = (evt.key === ' ' || evt.key === 'Spacebar');
    if (!is_arrow && !is_space) return;

    // Leave these keys wherever they already mean something: text entry takes both, the play button answers the
    // space bar itself rather than toggling playback twice, and the speed selector takes the arrow keys to move
    // between its speeds. The space bar is taken back off the selector, though -- once it has been clicked it
    // keeps the focus, and opening its list again is a small thing to lose beside the space bar meaning play
    // wherever you happen to have clicked last.
    var target = evt.target;
    if (!target) return;
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) return;
    if (is_space && target === playButton) return;
    if (is_arrow && target.tagName === 'SELECT') return;

    evt.preventDefault();
    if (is_space) {
      togglePlayback();
    } else {
      stepWindow(evt.key === 'ArrowRight' ? 1 : -1);
    }
  });

  window.addEventListener('resize', function() {
    setTimeout(function() { Plotly.Plots.resize(figure); resizeCanvas(); updateWindowDivStyle(); }, 0);
  });

  // The canvas and the selection window are both sized in pixels, so they have to be redrawn whenever the track's
  // own width changes -- including the first time it has one at all, which can be after this script has run.
  if (typeof ResizeObserver === 'function') {
    new ResizeObserver(function() { resizeCanvas(); updateWindowDivStyle(); }).observe(trackDiv);
  }

  resizeCanvas();
  updateWindowDivStyle();

  // The <head> <style> block (see Analyzer._TIME_SLIDER_HEAD_CSS) starts the figure hidden (visibility:hidden, not
  // display:none, so it still occupies its final layout space) and already-shrunk to make room for the slider --
  // so the slider and readout below are correctly positioned from the very first paint. But Plotly.newPlot()'s
  // initial autosize pass computes its internal plot dimensions from the window size, not the (already-correct)
  // container box, and -- worse, for a WebGL/mapbox trace -- doesn't finish reflecting a resize() call in the same
  // tick it's called, so revealing the figure right away (even after calling resize() synchronously) can still
  // show a visible moment of it at the wrong (window-sized) dimensions before catching up. Instead, reveal only
  // once Plotly itself reports a completed (re)draw following the resize -- debounced, in case that triggers more
  // than one -- with a fixed fallback delay in case 'plotly_afterplot' never fires for some reason (so the figure
  // is never stuck invisible).
  var revealTimer = null;
  function scheduleReveal(delay_ms) {
    if (revealTimer !== null) {
      clearTimeout(revealTimer);
    }
    revealTimer = setTimeout(function() {
      figure.style.visibility = 'visible';
      // The slider's own geometry is measured in pixels, so re-measure it here too -- the very first pass runs
      // before the figure has been laid out, when the track has no width to measure yet.
      resizeCanvas();
      updateWindowDivStyle();
    }, delay_ms);
  }
  figure.on('plotly_afterplot', function() { scheduleReveal(50); });
  scheduleReveal(500);

  Plotly.Plots.resize(figure);
  resizeCanvas();
})();
