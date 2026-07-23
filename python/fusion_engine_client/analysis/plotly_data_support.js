var figure = document.getElementsByClassName("plotly-graph-div js-plotly-plot")[0];

function GetTimeText(time_sec) {
  if (p1_time_axis_rel) {
    return `Rel: ${time_sec.toFixed(3)} sec (P1: ${(time_sec + p1_t0_sec).toFixed(3)} sec)`;
  }
  else {
    return `Rel: ${(time_sec - p1_t0_sec).toFixed(3)} sec (P1: ${time_sec.toFixed(3)} sec)`;
  }
}

// Convert whatever Plotly hands back for a 'date'-type axis point -- a plain number (milliseconds since the Unix
// epoch), a Date, or a "YYYY-MM-DD HH:MM:SS.ffffff"-ish string, depending on context -- into seconds since the Unix
// epoch.
function _DateAxisValueToPosixSec(x_value) {
  if (typeof x_value === 'number') {
    return x_value / 1000.0;
  }
  if (x_value instanceof Date) {
    return x_value.getTime() / 1000.0;
  }
  return new Date(String(x_value).replace(' ', 'T') + 'Z').getTime() / 1000.0;
}

// Build multi-format hover text (relative, P1, UTC, GPS week:tow) for a point whose X axis is time_axis_type
// ('relative', 'p1', 'gps', or 'utc') and whose customdata carries whichever of P1/GPS time is NOT reflected
// (directly, or via the constant offsets below) by x_value -- see Analyzer._time_hover_customdata().
//
// Note that the P1 vs GPS/UTC time relationship can change as the clock model is adjusted, so it is not a constant
// offset.
//
// Note: gps_posix_offset_sec is computed once per log so it includes the log's current leap second count. For
// simplicity, we assume logs do not span leap second changes. See time_provider.py for details.
function BuildTimeHoverText(x_value, other_time_sec) {
  let p1_time_sec, gps_time_sec;
  let have_offset = (typeof gps_posix_offset_sec === 'number');
  if (time_axis_type === 'relative') {
    p1_time_sec = x_value + p1_t0_sec;
    gps_time_sec = other_time_sec;
  }
  else if (time_axis_type === 'p1') {
    p1_time_sec = x_value;
    gps_time_sec = other_time_sec;
  }
  else if (time_axis_type === 'gps') {
    gps_time_sec = x_value;
    p1_time_sec = other_time_sec;
  }
  else { // 'utc'
    gps_time_sec = have_offset ? (_DateAxisValueToPosixSec(x_value) - gps_posix_offset_sec) : NaN;
    p1_time_sec = other_time_sec;
  }

  return BuildTimeHoverTextFromTimes(p1_time_sec, gps_time_sec);
}

// Same as BuildTimeHoverText(), but for hover text on a plot whose X/Y axes are not time at all (e.g. a topocentric
// East/North plot), where neither P1 nor GPS time can be recovered from the point's axis position -- both must be
// supplied directly (e.g. via customdata).
function BuildTimeHoverTextFromTimes(p1_time_sec, gps_time_sec) {
  let have_offset = (typeof gps_posix_offset_sec === 'number');
  let lines = [];

  if (p1_time_sec !== undefined && p1_time_sec !== null && !isNaN(p1_time_sec)) {
    let rel_sec = p1_time_sec - p1_t0_sec;
    lines.push(`Rel: ${rel_sec.toFixed(3)} sec (P1: ${p1_time_sec.toFixed(3)} sec)`);
  }

  if (gps_time_sec !== undefined && gps_time_sec !== null && !isNaN(gps_time_sec)) {
    if (have_offset) {
      let utc_date = new Date((gps_time_sec + gps_posix_offset_sec) * 1000.0);
      lines.push(`UTC: ${utc_date.toISOString().replace('T', ' ').replace('Z', '')}`);
    }

    const SECONDS_PER_WEEK = 7 * 24 * 3600.0;
    let week = Math.floor(gps_time_sec / SECONDS_PER_WEEK);
    let tow_sec = gps_time_sec - week * SECONDS_PER_WEEK;
    lines.push(`GPS: ${week}:${tow_sec.toFixed(3)} (${gps_time_sec.toFixed(3)} sec)`);
  }

  return lines.join('<br>');
}

// Build hover text for a point on a device system-time axis (relative or absolute, per Analyzer.time_type).
// Unlike BuildTimeHoverText(), there's no GPS-like alternate domain to convert to/from here -- system_t0_sec is a
// constant offset for the whole log, so the absolute value is always recoverable from x_value alone, with no
// per-point customdata needed.
function BuildSystemTimeHoverText(x_value) {
  if (typeof system_t0_sec !== 'number') {
    return `System Time: ${x_value.toFixed(3)} sec`;
  }
  else {
    return `System Time: ${(x_value + system_t0_sec).toFixed(3)} sec`;
  }
}

function ChangeHoverText(point, new_text) {
  // Note: Technically calling restyle() is more correct, however it can only restyle an entire trace, not just one
  // point in a trace, and in practice it's very sluggish. Manually modifying fullData.text is much faster.
  //
  // fullData.text must stay an array indexed by pointNumber, not a single string -- Plotly treats a plain string as
  // shared text for every point in the trace. Setting it that way here previously caused the hover box to always
  // display whichever point was hovered *previously*: hovering point A set the whole trace's text to A's value: only
  // on the *next* hover (now on point B) would it be overwritten, by which point the still-stale text for A had
  // already been rendered. Mutating a single array slot for this point avoids touching every other point's entry.
  if (!Array.isArray(point.fullData.text)) {
    point.fullData.text = [];
  }
  point.fullData.text[point.pointNumber] = new_text;
}

function GetCustomData(point, row) {
  let customdata = point.data.customdata.hasOwnProperty("_inputArray") ?
                   point.data.customdata._inputArray :
                   point.data.customdata;
  return customdata[row][point.pointNumber];
}

// Plotly doesn't support a custom per-tick label formatter function for numeric axes (only D3 format strings), and
// tickmode='array' with precomputed tick positions/labels doesn't regenerate on zoom/pan -- it only shows whichever
// of the fixed positions fall in the current view, which can leave a zoomed-in time axis with no visible ticks at
// all. So instead, for GPS-time axes we let Plotly auto-generate normal (zoom-aware) numeric ticks, then rewrite the
// already-rendered tick label text into GPS week:tow format after every redraw (initial render, zoom, and pan all
// trigger 'plotly_afterplot').
function _ReformatGpsAxisTicks() {
  if (time_axis_type !== 'gps') {
    return;
  }
  // Plotly names each subplot's X axis tick class after its axis number: 'xtick' for xaxis, 'x2tick' for xaxis2,
  // etc. -- a plain '.xtick' selector only catches the first subplot.
  document.querySelectorAll('[class^="x"][class$="tick"] text').forEach(function(el) {
    // This can run more than once on the same tick across a single zoom/pan (Plotly may fire 'plotly_afterplot'
    // more than once, reusing the same DOM element). Only reformat plain numbers -- an already-reformatted
    // "week:tow" string would otherwise get re-parsed and corrupted (parseFloat stops at the ':').
    let match = el.textContent.match(/^-?([\d,]+)(\.(\d+))?$/);
    if (!match) {
      return;
    }
    let raw_value = parseFloat(el.textContent.replace(/,/g, ''));
    if (!isNaN(raw_value)) {
      const SECONDS_PER_WEEK = 7 * 24 * 3600.0;
      let week = Math.floor(raw_value / SECONDS_PER_WEEK);
      let tow_sec = raw_value - week * SECONDS_PER_WEEK;
      // Match whatever decimal precision Plotly's own tick text already had, rather than always rounding to whole
      // seconds -- otherwise, zoomed in past 1 second, every tick in view would round to the same displayed value.
      let decimals = match[3] ? match[3].length : 0;
      el.textContent = `${week}:${tow_sec.toFixed(decimals)}`;
    }
  });
}
