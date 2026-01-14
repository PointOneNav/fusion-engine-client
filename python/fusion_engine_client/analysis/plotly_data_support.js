var figure = document.getElementsByClassName("plotly-graph-div js-plotly-plot")[0];

function GetTimeText(time_sec) {
  if (p1_time_axis_rel) {
    return `Rel: ${time_sec.toFixed(3)} sec (P1: ${(time_sec + p1_t0_sec).toFixed(3)} sec)`;
  }
  else {
    return `Rel: ${(time_sec - p1_t0_sec).toFixed(3)} sec (P1: ${time_sec.toFixed(3)} sec)`;
  }
}

function ChangeHoverText(point, new_text) {
  // Note: Technically calling restyle() is more correct, however it can only restyle an entire trace, not just one
  // point in a trace, and in practice it's very sluggish. Manually modifying fullData.text is much faster. Both options
  // seem to have a small race condition and occasionally the text does not change before the hover div becomes visible.
  // Nothing we can do about that right now.
  // let text_array = point.data.text;
  // text_array[point.pointNumber] = new_text;
  // Plotly.restyle(d, {'text': text_array}, [point.curveNumber]);
  point.fullData.text = new_text;
}

function GetCustomData(point, row) {
  let customdata = point.data.customdata.hasOwnProperty("_inputArray") ?
                   point.data.customdata._inputArray :
                   point.data.customdata;
  return customdata[row][point.pointNumber];
}
