var figure = document.getElementsByClassName("plotly-graph-div js-plotly-plot")[0];

// Build a "<Y axis title>: <value>" hover line straight from the point's own axis, so callers don't need to
// hardcode a plot-specific label/unit/precision.
// @param options.precision If set, number of digits after the decimal point (toFixed()). Defaults to 6 significant
//        digits (toPrecision()), which reads better across very different Y axis scales.
// @param options.label Override for the Y axis title, if the default isn't appropriate (e.g. no title set).
function BuildAxisValueHoverText(point, options) {
  options = options || {};
  let label = options.label || (point.yaxis.title && point.yaxis.title.text) || 'Value';
  let value = point.y;
  if (typeof value === 'number') {
    value = (typeof options.precision === 'number') ? value.toFixed(options.precision) : value.toPrecision(6);
  }
  return `${label}: ${value}`;
}

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

// PROTOTYPE: a custom tooltip drawn directly by us, positioned at the hovered point via
// 'plotly_hover'/'plotly_unhover', instead of relying on Plotly's native hover label + ChangeHoverText(). Plotly
// renders its own hover label as part of its internal mousemove handling, separately from our injected
// 'plotly_hover' listener -- there's no guaranteed order between "Plotly reads fullData.text to draw its label"
// and "our handler mutates fullData.text", so on plots with many traces (more work for Plotly's internal
// hit-testing, more timing variance) the label sometimes renders before our mutation lands, showing stale or no
// extra text until the next mousemove. Drawing our own tooltip synchronously inside the same handler that computes
// the text eliminates that race entirely -- there's nothing left for an external renderer to read at the wrong
// time. Requires hoverinfo='none' on the trace so Plotly's native label doesn't also try to draw at the same time.
//
// Styled to resemble Plotly's own hover label: background matches the trace's color, font matches
// layout.hoverlabel.font, and it's positioned like Plotly's does -- an arrow-and-box to the right of the point,
// flipping to the left near the plot's right edge, vertically centered on the point.
var _customTooltipDiv = null;
var _customTooltipArrowDiv = null;
var _customTooltipArrowBorderDiv = null;
const _CUSTOM_TOOLTIP_ARROW_SIZE = 6;
const _CUSTOM_TOOLTIP_GAP = 2;
const _CUSTOM_TOOLTIP_BORDER_WIDTH = 1;

function _GetCustomTooltipDiv() {
  if (_customTooltipDiv === null) {
    _customTooltipDiv = document.createElement('div');
    _customTooltipDiv.style.position = 'fixed';
    _customTooltipDiv.style.pointerEvents = 'none';
    _customTooltipDiv.style.borderRadius = '2px';
    _customTooltipDiv.style.border = _CUSTOM_TOOLTIP_BORDER_WIDTH + 'px solid black';
    _customTooltipDiv.style.padding = '2px 4px';
    _customTooltipDiv.style.zIndex = '10000';
    _customTooltipDiv.style.display = 'none';
    _customTooltipDiv.style.whiteSpace = 'nowrap';
    document.body.appendChild(_customTooltipDiv);

    // Drawn one size larger and directly behind the fill arrow below, so only a 1px black rim peeks out along the
    // two slanted edges. Its flat (base) edge lines up exactly with the fill's, staying hidden behind/flush with
    // the box's own border.
    _customTooltipArrowBorderDiv = document.createElement('div');
    _customTooltipArrowBorderDiv.style.position = 'fixed';
    _customTooltipArrowBorderDiv.style.pointerEvents = 'none';
    _customTooltipArrowBorderDiv.style.width = '0';
    _customTooltipArrowBorderDiv.style.height = '0';
    _customTooltipArrowBorderDiv.style.zIndex = '10000';
    _customTooltipArrowBorderDiv.style.display = 'none';
    document.body.appendChild(_customTooltipArrowBorderDiv);

    _customTooltipArrowDiv = document.createElement('div');
    _customTooltipArrowDiv.style.position = 'fixed';
    _customTooltipArrowDiv.style.pointerEvents = 'none';
    _customTooltipArrowDiv.style.width = '0';
    _customTooltipArrowDiv.style.height = '0';
    _customTooltipArrowDiv.style.borderTop = _CUSTOM_TOOLTIP_ARROW_SIZE + 'px solid transparent';
    _customTooltipArrowDiv.style.borderBottom = _CUSTOM_TOOLTIP_ARROW_SIZE + 'px solid transparent';
    _customTooltipArrowDiv.style.zIndex = '10000';
    _customTooltipArrowDiv.style.display = 'none';
    document.body.appendChild(_customTooltipArrowDiv);
  }
  return _customTooltipDiv;
}

// Resolve an arbitrary CSS color string (hex, rgb(), named color, ...) to a readable text color (black or white),
// the same way Plotly picks contrasting text for its own colored hover labels.
function _GetContrastingTextColor(css_color) {
  let probe = document.createElement('div');
  probe.style.display = 'none';
  probe.style.color = css_color;
  document.body.appendChild(probe);
  let computed = getComputedStyle(probe).color;
  document.body.removeChild(probe);

  let m = computed.match(/\d+/g);
  if (!m || m.length < 3) {
    return '#000';
  }
  let luminance = (0.299 * m[0] + 0.587 * m[1] + 0.114 * m[2]) / 255;
  return luminance > 0.6 ? '#000' : '#fff';
}

function GetCustomTooltipHTML(name, value, other_text) {
  let tooltip = ``;
  if (name) {
    tooltip += `<b>${name}</b>`;
  }
  if (value) {
    if (tooltip) {
      tooltip += `<br>`;
    }
    tooltip += `${value}`;
  }
  if (other_text) {
    if (tooltip) {
      tooltip += `<br>`;
    }
    tooltip += `${other_text}`;
  }
  return tooltip;
}

// @param point A point from a 'plotly_hover' event (data.points[i]) -- used for its data value (to compute pixel
//        position via point.xaxis/yaxis) and its trace's color (point.data.marker/line.color).
// @param html_text The tooltip content.
function ShowCustomTooltip(point, html_text) {
  let div = _GetCustomTooltipDiv();
  let arrow = _customTooltipArrowDiv;
  let arrow_border = _customTooltipArrowBorderDiv;
  const B = _CUSTOM_TOOLTIP_BORDER_WIDTH;

  let bgcolor = (point.data.marker && point.data.marker.color) || (point.data.line && point.data.line.color) ||
               '#444';
  let hoverlabel_font = (figure._fullLayout.hoverlabel && figure._fullLayout.hoverlabel.font) || {};

  div.innerHTML = html_text;
  div.style.backgroundColor = bgcolor;
  div.style.color = _GetContrastingTextColor(bgcolor);
  div.style.fontFamily = hoverlabel_font.family || 'Arial, sans-serif';
  div.style.fontSize = (hoverlabel_font.size || 13) + 'px';

  // Compute the point's own pixel position (not just wherever the mouse currently is) so the box and arrow align
  // precisely with the marker, the way Plotly's native label does.
  let rect = figure.getBoundingClientRect();
  // d2l() converts the raw data value (a plain number for linear axes, but a formatted date string for date axes)
  // into the axis's internal linearized coordinate that l2p() expects -- passing point.x/point.y to l2p() directly
  // works for numeric axes but silently yields NaN on a date axis (e.g. UTC time), leaving the tooltip unpositioned.
  let x_px = rect.left + point.xaxis.l2p(point.xaxis.d2l(point.x)) + point.xaxis._offset;
  let y_px = rect.top + point.yaxis.l2p(point.yaxis.d2l(point.y)) + point.yaxis._offset;

  // Render invisibly first so we can measure its size before deciding where to place it.
  div.style.visibility = 'hidden';
  div.style.display = 'block';
  let box_width = div.offsetWidth;
  let box_height = div.offsetHeight;

  let draw_right = (x_px + _CUSTOM_TOOLTIP_ARROW_SIZE + _CUSTOM_TOOLTIP_GAP + box_width) <= rect.right;

  let box_left, arrow_left, border_left;
  arrow_border.style.borderTop = (_CUSTOM_TOOLTIP_ARROW_SIZE + B) + 'px solid transparent';
  arrow_border.style.borderBottom = (_CUSTOM_TOOLTIP_ARROW_SIZE + B) + 'px solid transparent';
  if (draw_right) {
    box_left = x_px + _CUSTOM_TOOLTIP_ARROW_SIZE + _CUSTOM_TOOLTIP_GAP;
    arrow_left = x_px + _CUSTOM_TOOLTIP_GAP;
    border_left = arrow_left - B;
    arrow.style.borderLeft = '';
    arrow.style.borderRight = _CUSTOM_TOOLTIP_ARROW_SIZE + 'px solid ' + bgcolor;
    arrow_border.style.borderLeft = '';
    arrow_border.style.borderRight = (_CUSTOM_TOOLTIP_ARROW_SIZE + B) + 'px solid black';
  } else {
    box_left = x_px - _CUSTOM_TOOLTIP_ARROW_SIZE - _CUSTOM_TOOLTIP_GAP - box_width;
    arrow_left = x_px - _CUSTOM_TOOLTIP_ARROW_SIZE - _CUSTOM_TOOLTIP_GAP;
    border_left = arrow_left;
    arrow.style.borderRight = '';
    arrow.style.borderLeft = _CUSTOM_TOOLTIP_ARROW_SIZE + 'px solid ' + bgcolor;
    arrow_border.style.borderRight = '';
    arrow_border.style.borderLeft = (_CUSTOM_TOOLTIP_ARROW_SIZE + B) + 'px solid black';
  }

  div.style.left = box_left + 'px';
  div.style.top = (y_px - box_height / 2) + 'px';
  div.style.visibility = 'visible';

  arrow.style.left = arrow_left + 'px';
  arrow.style.top = (y_px - _CUSTOM_TOOLTIP_ARROW_SIZE) + 'px';
  arrow.style.display = 'block';

  arrow_border.style.left = border_left + 'px';
  arrow_border.style.top = (y_px - _CUSTOM_TOOLTIP_ARROW_SIZE - B) + 'px';
  arrow_border.style.display = 'block';
}

function HideCustomTooltip() {
  if (_customTooltipDiv !== null) {
    _customTooltipDiv.style.display = 'none';
    _customTooltipArrowDiv.style.display = 'none';
    _customTooltipArrowBorderDiv.style.display = 'none';
  }
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
