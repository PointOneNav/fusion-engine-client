#!/usr/bin/env python3

from typing import Union, List, Any, Optional

from collections import namedtuple, defaultdict
import copy
import inspect
import json
import os
import sys
import webbrowser

from gpstime import gpstime, gps2unix
from palettable.tableau import Tableau_20
import plotly
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from pymap3d import geodetic2ecef

# If running as a script, add fusion-engine-client/ to the Python import path and correct __package__ to enable relative
# imports.
if __name__ == "__main__" and (__package__ is None or __package__ == ''):
    root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '../..'))
    sys.path.append(root_dir)
    __package__ = "fusion_engine_client.analysis"

from ..messages import *
from ..messages.timestamp import SECONDS_PER_WEEK
from .attitude import get_enu_rotation_matrix
from .data_loader import DataLoader, MessageData, TimeRange
from .reference import ReferenceData, _OWN_LOG_STATISTICS
from ..parsers.file_index import HostTimeIndexMap
from ..utils import trace as logging
from ..utils.argument_parser import ArgumentParser, ExtendedBooleanAction, TriStateBooleanAction, CSVAction
from ..utils.log import define_cli_arguments as define_log_search_arguments, locate_log
from ..utils.numpy_utils import find_first
from ..utils.time_provider import TimeProvider
from ..utils.trace import HighlightFormatter


_logger = logging.getLogger('point_one.fusion_engine.analysis.analyzer')

SolutionTypeInfo = namedtuple('SolutionTypeInfo', ['name', 'style'])

_SOLUTION_TYPE_MAP = {
    SolutionType.Invalid: SolutionTypeInfo(name='Invalid', style={'color': 'black'}),
    SolutionType.Integrate: SolutionTypeInfo(name='Integrated', style={'color': 'cyan'}),
    SolutionType.AutonomousGPS: SolutionTypeInfo(name='Standalone', style={'color': 'red'}),
    SolutionType.DGPS: SolutionTypeInfo(name='DGPS', style={'color': 'blue'}),
    SolutionType.RTKFloat: SolutionTypeInfo(name='RTK Float', style={'color': 'green'}),
    SolutionType.RTKFixed: SolutionTypeInfo(name='RTK Fixed', style={'color': 'orange'}),
    SolutionType.PPP: SolutionTypeInfo(name='PPP', style={'color': 'pink'}),
    SolutionType.External: SolutionTypeInfo(name='External', style={'color': 'purple'}),
}


def _data_to_table(col_titles: List[str], values: List[List[Any]], row_major: bool = False, id='table'):
    if row_major:
        # If values is row major (outer index is the table rows), transpose it.
        col_values = list(map(list, zip(*values)))
    else:
        col_values = values

    table_html = f'''\
<table id={id}>
  <tbody style="vertical-align: top">
    <tr style="background-color: #a2c4fa">
'''
    for title in col_titles:
        table_html += f'<th>{title}</th>'
    table_html += '</tr>'
    num_rows = min([len(l) for l in col_values])
    for row_idx in range(num_rows):
        table_html += '<tr>'

        separator_row = col_values[0][row_idx] is None
        for col_data in col_values:
            if separator_row:
                table_html += '<td><hr></td>'
            else:
                table_html += f'<td>{col_data[row_idx]}</td>'

        table_html += '</tr>'
    table_html += '''\
  </tbody>
</table>
'''
    return table_html.replace('\n', '')


_page_template = '''\
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
  <meta content="text/html; charset=ISO-8859-1" http-equiv="content-type">
  <title>%(title)s</title>
</head>
<body>
  %(body)s
</body>
</html>
'''


class Analyzer(object):
    logger = _logger

    LONG_LOG_DURATION_SEC = 2 * 3600.0
    HIGH_MEASUREMENT_RATE_HZ = 40.0

    # Registers _ReformatGpsAxisTicks() to run after every redraw  (see plotly_data_support.js). Needed by any plot
    # whose X axis can be in 'gps' mode, whether or not it uses _TIME_HOVER_JS below for hover text.
    _GPS_TICK_REFORMAT_JS = """\
figure.on('plotly_afterplot', _ReformatGpsAxisTicks);
// The initial render's 'plotly_afterplot' can fire before tick label text is finalized, so also run once more on
// the next tick, after the very first render has fully settled.
setTimeout(_ReformatGpsAxisTicks, 0);
"""

    # Generic hover JS for traces whose customdata is whichever timestamp (P1 or GPS) is not already reflected by the
    # X axis (see BuildTimeHoverText() in plotly_data_support.js, and _time_hover_customdata() below). Plots needing
    # additional custom hover logic (e.g., decoding a status bitmask) should not use this directly -- build a custom
    # 'plotly_hover' handler instead, but still append _GPS_TICK_REFORMAT_JS to it.
    #
    # If customdata is omitted, the hover text will just show the X axis value (absolute or relative time).
    _TIME_HOVER_JS = """\
figure.on('plotly_hover', function(data) {
  for (let i = 0; i < data.points.length; ++i) {
    let point = data.points[i];
    if (point.data.customdata) {
      ChangeHoverText(point, BuildTimeHoverText(point.x, GetCustomData(point, 0)));
    }
    else {
      ChangeHoverText(point, BuildTimeHoverText(point.x));
    }
  }
});
""" + _GPS_TICK_REFORMAT_JS

    # Generic hover JS for traces on a device system-time axis (see BuildSystemTimeHoverText() in
    # plotly_data_support.js). Unlike _TIME_HOVER_JS, no customdata is needed -- system time has no GPS-like alternate
    # domain, so the value not shown on the X axis (relative vs. absolute) is always a constant offset (system_t0_sec)
    # away, not a per-point value.
    _SYSTEM_TIME_HOVER_JS = """\
figure.on('plotly_hover', function(data) {
  for (let i = 0; i < data.points.length; ++i) {
    let point = data.points[i];
    ChangeHoverText(point, BuildSystemTimeHoverText(point.x));
  }
});
"""

    def __init__(self,
                 file: Union[DataLoader, str], ignore_index: bool = False,
                 output_dir: str = None, prefix: str = '',
                 time_range: TimeRange = None, max_messages: int = None,
                 time_type: str = 'utc',
                 truncate_long_logs: bool = True, source_id: Optional[List[int]] = None):
        """!
        @brief Create an analyzer for the specified log.

        @param file A @ref DataLoader instance, or the path to a file to be loaded.
        @param ignore_index If `True`, do not use the `.p1i` index file if present, and instead regenerate it from the
               `.p1log` data file.
        @param output_dir The directory where output will be stored.
        @param prefix An optional prefix to be appended to the generated filenames.
        @param time_range An optional @ref TimeRange object specifying desired start and end time bounds of the data to
               be read. See @ref TimeRange for more details.
        @param max_messages If set, read up to the specified maximum number of messages. Applies across all message
               types.
        @param time_type Specify the way in which time will be plotted:
               - `utc` - UTC date/time, if available (falls back to P1 time otherwise)
               - `gps` - GPS time (week and time of week), if available (falls back to P1 time otherwise)
               - `p1` - Absolute P1 (or system) time
               - `relative` - Elapsed time since the start of the log
        @param truncate_long_logs If `True`, reduce or skip certain plots if the log extremely long (as defined by
               @ref LONG_LOG_DURATION_SEC).
        """
        if isinstance(file, str):
            self.reader = DataLoader(file, ignore_index=ignore_index)
            self.host_time_mapper = HostTimeIndexMap.from_data_path(self.reader.get_index(), file)
            if self.host_time_mapper is not None:
                _logger.info('Loaded host time map.')
        else:
            self.reader = file
            self.host_time_mapper = None


        self.output_dir = output_dir
        self.prefix = prefix

        self.params = {
            'time_range': time_range,
            'max_messages': max_messages,
            'show_progress': True,
            'return_numpy': True
        }

        # If source ID was unspecified, use _all_ source IDs found in the log. If source ID _was_ specified, use the
        # intersection of the requested source ID(s) and the available source IDs.
        if source_id is None:
            self.source_ids = self.reader.get_available_source_ids()
        else:
            source_ids = set(source_id)
            unavailable_source_ids = source_ids.difference(self.reader.get_available_source_ids())
            if len(unavailable_source_ids) > 0:
                self.logger.warning('Not all source IDs requested are available. Cannot extract the following '
                                    'source IDs: {}'.format(unavailable_source_ids))

            self.source_ids = source_ids.intersection(self.reader.get_available_source_ids())
            # If the requested pose source IDs are unavailable, warn.
            if len(self.source_ids) == 0:
                self.logger.warning('Requested source IDs unavailable. Cannot extract pose data.')

        if len(self.source_ids) > 0:
            self.default_source_id = min(self.source_ids)
        else:
            self.default_source_id = 0

        # Load the P1/GPS time correspondence for this log, used to support time_type 'gps' and 'utc'.
        self.time_provider = TimeProvider()
        self.time_provider.set_reference_data(self.reader, source_id=self.default_source_id)

        if time_type not in ('utc', 'gps', 'p1', 'relative'):
            raise ValueError(f"Unsupported time type specifier '{time_type}'.")
        elif time_type in ('gps', 'utc') and not self.time_provider.has_gps_reference():
            _logger.warning("No GPS time reference available in this log. Falling back to P1 time.")
            time_type = 'p1'

        self.time_type = time_type

        if self.time_type == 'relative':
            self.system_t0 = self.reader.get_system_t0()
            if self.system_t0 is None:
                self.system_t0 = np.nan
        else:
            self.system_t0 = 0.0

        # The time domain -- `p1` (covers both relative and absolute P1 time) or `gps` (covers both GPS and UTC) --
        # implied by @c self.time_type, used by @ref _resolve_x_axis() and the default of _time_hover_customdata()'s
        # `x_domain` argument. Some plots may use a different X axis regardles of self.time_type, and may override this.
        self._default_x_domain = 'p1' if self.time_type in ('relative', 'p1') else 'gps'

        self.plots = {}
        self.summary = ''

        self._mapbox_token_missing = False

        self._gnss_signals_data = {}
        self._gnss_antenna_source_ids = None
        self._pose_source_ids = None

        if self.output_dir is not None:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)

        # Determine if this is a long log. In practice, some plots can be extremely slow to generate for long logs
        # because of plotly limitations when handling a lot of traces (signal status, sky plot), or some may generate
        # HTML files, but may fail to load in the browser because of plotly call stack errors:
        #   Uncaught RangeError: Maximum call stack size exceeded
        #
        # To get around this, those plots may be reduced in scope, downsampled, or disabled entirely unless the user
        # says not to.
        _, processing_duration_sec = self._calculate_duration()
        self.long_log_detected = processing_duration_sec > self.LONG_LOG_DURATION_SEC
        self.truncate_data = False
        if self.long_log_detected:
            if truncate_long_logs:
                _logger.warning('Log duration very long (%.1f hours > %.1f hours). Some plots may be reduced or '
                                'disabled.' %
                                (processing_duration_sec / 3600.0, self.LONG_LOG_DURATION_SEC / 3600.0))
                self.truncate_data = True
            else:
                _logger.warning('Log duration very long (%.1f hours > %.1f hours). Some plots may be very slow to '
                                'generate or load.' %
                                (processing_duration_sec / 3600.0, self.LONG_LOG_DURATION_SEC / 3600.0))

    def plot_time_scale(self):
        if self.output_dir is None:
            return

        # Setup the figure. This plot's X axis is always P1 time (relative or absolute), regardless of
        # self.time_type -- see _resolve_x_axis(..., ignore_gps=True) below.
        axis_layout = self._x_axis_layout(ignore_gps=True)
        time_axis_str = 'Relative Time' if self.time_type == 'relative' else 'P1/System Time'
        p1_time_axis_str = axis_layout['title'].replace(' (sec)', '')
        figure = make_subplots(rows=2, cols=1, print_grid=False, shared_xaxes=True,
                               subplot_titles=[f'Device Time vs. {time_axis_str}',
                                               f'Pose Message Interval vs. {p1_time_axis_str}'])

        figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'])
        figure['layout']['xaxis1'].update(title=f"{time_axis_str} (sec)", showticklabels=True)
        figure['layout']['xaxis2'].update(showticklabels=True, **axis_layout)
        figure['layout']['yaxis1'].update(title="Absolute Time",
                                          ticktext=['P1/GPS Time', 'System Time'],
                                          tickvals=[1, 2])
        figure['layout']['yaxis2'].update(title="Interval (sec)", rangemode="tozero")

        # Read the pose data to get P1 and GPS timestamps.
        result = self.reader.read(message_types=[PoseMessage], source_ids=self.default_source_id, **self.params)
        pose_data = result[PoseMessage.MESSAGE_TYPE]

        if len(pose_data.p1_time) > 0:
            time, _ = self._resolve_x_axis(p1_time=pose_data.p1_time, gps_time=pose_data.gps_time, ignore_gps=True)

            # Calculate time intervals, rounded to the nearest 0.1 ms.
            dp1_time = np.diff(time, prepend=np.nan)
            dp1_time = np.round(dp1_time * 1e4) * 1e-4

            dgps_time = np.diff(pose_data.gps_time, prepend=np.nan)
            dgps_time = np.round(dgps_time * 1e4) * 1e-4

            # plotly starts to struggle with > 3 hours of data and won't display mouseover text, so decimate if
            # necessary.
            decimation_limit_sec = 3 * 3600.0
            dt_sec = time[-1] - time[0]
            dp1_stats = None
            dgps_stats = None
            if dt_sec >= decimation_limit_sec:
                step = math.ceil(dt_sec / decimation_limit_sec)
                idx = np.full_like(time, False, dtype=bool)
                idx[0::step] = True

                time = time[idx]
                p1_time = pose_data.p1_time[idx]
                gps_time = pose_data.gps_time[idx]

                # Since we are going to decimate the data, we first calculate min/max values for all epochs in each step
                # size. That way we can plot min/max, in addition to the value that does not get dropped, to avoid
                # hiding outliers that do get dropped (e.g., missing a gap of 0.2 seconds (1x 10 Hz output dropped) when
                # decimating by 3).
                def _calc_stats(input):
                    num_remaining = len(idx) % step
                    if num_remaining == 0:
                        subset = input
                    else:
                        subset = input[:-num_remaining]

                    grouped = subset.reshape((-1, step))
                    stats = {
                        'max': np.nanmax(grouped, axis=1),
                        'min': np.nanmin(grouped, axis=1)
                    }

                    if num_remaining != 0:
                        stats['max'] = np.append(stats['max'], np.nanmax(input[-num_remaining:]))
                        stats['min'] = np.append(stats['min'], np.nanmin(input[-num_remaining:]))

                    return stats

                dp1_stats = _calc_stats(dp1_time)
                dgps_stats = _calc_stats(dgps_time)

                dp1_time = dp1_time[idx]
                dgps_time = dgps_time[idx]

                figure.layout.annotations[0].text += "<br>Decimated %dx" % step
                figure.layout.annotations[1].text += "<br>Decimated %dx" % step
            else:
                p1_time = pose_data.p1_time
                gps_time = pose_data.gps_time

            # This plot's X axis is always P1 time (relative or absolute), regardless of self.time_type, since its
            # purpose is comparing P1/GPS/System clocks against a common elapsed timeline. So customdata only needs
            # GPS time -- BuildTimeHoverText() (see plotly_data_support.js) recovers P1 time from the X value itself.
            customdata = self._time_hover_customdata(p1_time=p1_time, gps_time=gps_time, x_domain='p1')
            figure.add_trace(go.Scattergl(x=time, y=np.full_like(time, 1), name='P1/GPS Time', customdata=customdata,
                                          mode='markers', marker={'color': 'blue'}),
                             1, 1)

            figure.add_trace(go.Scattergl(x=time, y=dp1_time, name='P1 Time Interval', customdata=customdata,
                                          mode='markers', marker={'color': 'red'}),
                             2, 1)
            if dp1_stats is not None:
                figure.add_trace(go.Scattergl(x=time, y=dp1_stats['max'], name='P1 Time Interval (Max)',
                                              mode='markers', marker={'symbol': 'triangle-up-open'}),
                                 2, 1)
                figure.add_trace(go.Scattergl(x=time, y=dp1_stats['min'], name='P1 Time Interval (Min)',
                                              mode='markers', marker={'symbol': 'triangle-down-open'}),
                                 2, 1)

            figure.add_trace(go.Scattergl(x=time, y=dgps_time, name='GPS Time Interval', customdata=customdata,
                                          mode='markers', marker={'color': 'green'}),
                             2, 1)
            if dgps_stats is not None:
                figure.add_trace(go.Scattergl(x=time, y=dgps_stats['max'], name='GPS Time Interval (Max)',
                                              mode='markers', marker={'symbol': 'triangle-up-open'}),
                                 2, 1)
                figure.add_trace(go.Scattergl(x=time, y=dgps_stats['min'], name='GPS Time Interval (Min)',
                                              mode='markers', marker={'symbol': 'triangle-down-open'}),
                                 2, 1)

        # Read system timestamps from event notifications and profiling data, if present.
        result = self.reader.read(message_types=[EventNotificationMessage], **self.params)
        event_data = result[EventNotificationMessage.MESSAGE_TYPE]
        system_time_sec = None
        if len(event_data.system_time) > 0:
            system_time_sec = event_data.system_time

        # Plot the result.
        if system_time_sec is not None:
            time, _ = self._resolve_x_axis(system_time=system_time_sec, time_source='system')

            # plotly starts to struggle with > 2 hours of data and won't display mouseover text, so decimate if
            # necessary.
            dt_sec = time[-1] - time[0]
            if dt_sec > 7200.0:
                step = math.ceil(dt_sec / 7200.0)
                idx = np.full_like(time, False, dtype=bool)
                idx[0::step] = True
                time = time[idx]

            figure.add_trace(go.Scattergl(x=time, y=np.full_like(time, 2), name='System Time',
                                          mode='markers', marker={'color': 'purple'}),
                             1, 1)

        # P1/GPS time points carry customdata (see BuildTimeHoverText()), system time points don't.
        _TIME_SCALE_HOVER_JS = """\
figure.on('plotly_hover', function(data) {
  let point = data.points[0];
  let time_text = point.data.customdata ? BuildTimeHoverText(point.x, GetCustomData(point, 0)) :
                                          BuildSystemTimeHoverText(point.x);
  let value_text = BuildAxisValueHoverText(point);
  ShowCustomTooltip(point, GetCustomTooltipHTML(point.data.name, value_text, time_text));
});
figure.on('plotly_unhover', function(data) {
  HideCustomTooltip();
});
"""

        self._add_figure(name="time_scale", figure=figure, title="Time Scale", custom_hover=True,
                         inject_js=_TIME_SCALE_HOVER_JS,
                         time_axis_type='relative' if self.time_type == 'relative' else 'p1')

    def plot_latency(self):
        if self.output_dir is None:
            return

        if self.host_time_mapper is None:
            return

        # Read the pose data to get P1 and GPS timestamps.
        # The message_index will be used to map back to the host times the message data was received.
        # This will then be compared to the GPS time, assuming the host time was synchronized to GPS time.
        result = self.reader.read(message_types=[PoseMessage], return_message_index=True,
                                  source_ids=self.default_source_id, **self.params)
        pose_data = result[PoseMessage.MESSAGE_TYPE]

        valid_idx = ~np.isnan(pose_data.gps_time)

        if np.sum(valid_idx) == 0:
            return

        p1_time = pose_data.p1_time[valid_idx]
        gps_time = pose_data.gps_time[valid_idx]
        message_index = pose_data.message_index[valid_idx]

        last_gps_time = gps_time[-1]

        time, axis_layout = self._resolve_x_axis(p1_time=p1_time, gps_time=gps_time)
        customdata = self._time_hover_customdata(p1_time=p1_time, gps_time=gps_time)

        # Setup the figure.
        figure = make_subplots(rows=1, cols=1, print_grid=False, shared_xaxes=True,
                               subplot_titles=[f'Pose Message Latency'])

        figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'])
        figure['layout']['xaxis1'].update(showticklabels=True, **axis_layout)
        figure['layout']['yaxis1'].update(title="Latency (sec)")

        # Use the last GPS Time to get the offset between UNIX and GPS time. This includes the epoch difference and the
        # current leap second.
        gps_posix_offset = gps2unix(last_gps_time) - last_gps_time
        gps_posix_times = ((gps_time + gps_posix_offset) * 1e9).astype('datetime64[ns]')

        host_posix_times = self.host_time_mapper.get_host_timestamps(message_index)

        # NOTE: The difference between host_posix_times and gps_posix_times is a combination of:
        # 1. The time the positioning engine took to generate the message
        # 2. The time the message took to be sent over the transport (e.x. TCP)
        # 3. The time the delay before the host was able to generate the timestamp (may be large/noisy if the data was
        #    timestamped in user space instead of in hardware or the kernel)
        # 4. The accuracy of the host's timestamping clock.
        #
        # This absolute latency value is only reliable if the host clock was synced to GPS time.
        latency_sec = (host_posix_times - gps_posix_times).astype(float) / 1e9

        figure.add_trace(go.Scattergl(x=time, y=latency_sec, customdata=customdata, name='Pose Message Latency',
                                      mode='markers', marker={'color': 'blue'}),
                         1, 1)

        figure.update_layout(title_text='NOTE: Latency assumes the host system clock is synced to GPS time. '
                                        'Any error will impact the latency computation.')
        self._add_figure(name="host_latency", figure=figure, title="Host Received Latency", custom_hover=True,
                         inject_js=self._custom_tooltip_js())

    def plot_reset_timing(self):
        if self.output_dir is None:
            return

        # Find reset events.
        result = self.reader.read(message_types=[EventNotificationMessage], return_message_index=True, **self.params)
        event_data = result[EventNotificationMessage.MESSAGE_TYPE]

        reset_idx = event_data.event_type == EventType.RESET
        if not np.any(reset_idx):
            self.logger.info('No reset events detected. Skipping reset timing type plot.')
            return

        self.logger.info('Calculating reset recovery times...')

        # Note that events contain system time, not P1 time. We'll assume system time is close enough to P1 time for
        # purposes of calculating elapsed reset time below. In the future, we'll have a mechanism for accurately
        # converting between system and P1 time.
        reset_system_time_sec = event_data.system_time[reset_idx]

        reset_idx = np.where(reset_idx)[0]
        reset_message_indices = [event_data.message_index[i] for i in reset_idx]

        # For each reset in the log, try to find the pose messages immediately following the reset where the solution
        # type first goes invalid, and then where it goes valid again.
        dt_reset_to_valid = np.full(reset_idx.shape, np.nan)
        dt_reset_to_invalid = np.full(reset_idx.shape, np.nan)
        dt_invalid_to_valid = np.full(reset_idx.shape, np.nan)
        unstarted_resets = []

        log_reader = self.reader.get_log_reader()
        for i, reset_index in enumerate(reset_message_indices):
            next_reset_index = reset_message_indices[i + 1] if i < len(reset_message_indices) - 1 else None

            # Filter to all pose messages _after_ the reset event.
            log_reader.clear_filters()
            log_reader.rewind()
            log_reader.filter_in_place(slice(reset_index + 1, next_reset_index, 1))
            log_reader.filter_in_place(self.params['time_range'])
            log_reader.filter_in_place(PoseMessage)
            log_reader.set_show_progress(False)

            # Find the pose where the solution went invalid after the reset, then where it went valid after that.
            invalid_p1_time = None
            valid_p1_time = None
            while True:
                try:
                    _, message, pose_index = self.reader.read_next(return_message_index=True)
                except StopIteration:
                    break

                if invalid_p1_time is None:
                    if message.solution_type == SolutionType.Invalid:
                        invalid_p1_time = message.get_p1_time()
                        invalid_p1_time_sec = float(invalid_p1_time)
                        if invalid_p1_time_sec >= reset_system_time_sec[i]:
                            dt_reset_to_invalid[i] = invalid_p1_time_sec - reset_system_time_sec[i]
                        else:
                            dt_reset_to_invalid[i] = 0.0
                else:
                    if message.solution_type != SolutionType.Invalid:
                        valid_p1_time = message.get_p1_time()
                        valid_p1_time_sec = float(valid_p1_time)
                        invalid_p1_time_sec = float(invalid_p1_time)

                        if valid_p1_time_sec >= reset_system_time_sec[i]:
                            dt_reset_to_valid[i] = valid_p1_time_sec - reset_system_time_sec[i]
                        else:
                            dt_reset_to_valid[i] = 0.0

                        dt_invalid_to_valid[i] = valid_p1_time_sec - invalid_p1_time_sec

                        self.logger.info('  Processed %d/%d resets.' % (i + 1, len(reset_message_indices)))
                        break

            if invalid_p1_time is None:
                self.logger.warning('Unable to determine start time for reset %d at system time %.3f sec.' %
                                    (i, reset_system_time_sec[i]))
                unstarted_resets.append(i)
            elif valid_p1_time is None:
                self.logger.warning('Unable to calculate recovery time for reset %d at system time %.3f sec.' %
                                    (i, reset_system_time_sec[i]))

        # Setup the figure.
        figure = make_subplots(rows=1, cols=1, print_grid=False, shared_xaxes=True,
                               subplot_titles=['Reset Recovery Time'])

        time, axis_layout = self._resolve_x_axis(system_time=reset_system_time_sec, time_source='system')

        figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'])
        figure['layout']['xaxis1'].update(showticklabels=True, **axis_layout)
        figure['layout']['yaxis1'].update(title="Elapsed Time (sec)", rangemode="tozero")

        figure.add_trace(go.Scattergl(x=time, y=dt_reset_to_valid,
                                      name='Command -> Valid', mode='markers'),
                         1, 1)
        figure.add_trace(go.Scattergl(x=time, y=dt_reset_to_invalid,
                                      name='Command -> Invalid', mode='markers'),
                         1, 1)
        figure.add_trace(go.Scattergl(x=time, y=dt_invalid_to_valid,
                                      name='Invalid -> Valid', mode='markers'),
                         1, 1)

        if len(unstarted_resets) > 0:
            idx = np.array(unstarted_resets)
            time = time[idx]
            figure.add_trace(go.Scattergl(x=time, y=np.zeros_like(time),
                                          name='Unstarted Resets', mode='markers'),
                             1, 1)

        self._add_figure(name="reset_timing", figure=figure, title="Reset Recovery Timing", custom_hover=True,
                         inject_js=self._custom_tooltip_js(time_source='system'))

    def plot_pose(self):
        """!
        @brief Plot position/attitude solution data.
        """
        if self.output_dir is None:
            return

        # Read the pose data.
        result = self.reader.read(message_types=[PoseMessage], source_ids=self.default_source_id, **self.params)
        pose_data = result[PoseMessage.MESSAGE_TYPE]

        if len(pose_data.p1_time) == 0:
            self.logger.info('No pose data available. Skipping pose vs. time plot.')
            return

        time, axis_layout = self._resolve_x_axis(p1_time=pose_data.p1_time, gps_time=pose_data.gps_time)
        customdata = self._time_hover_customdata(p1_time=pose_data.p1_time, gps_time=pose_data.gps_time)

        valid_idx = np.logical_and(~np.isnan(pose_data.p1_time), pose_data.solution_type != SolutionType.Invalid)
        if not np.any(valid_idx):
            self.logger.info('No valid position solutions detected.')
            return

        first_idx = find_first(valid_idx)
        # If there are no valid indices, use the last index.
        if first_idx < 0:
            first_idx = len(valid_idx) - 1

        c_enu_ecef = get_enu_rotation_matrix(*pose_data.lla_deg[0:2, first_idx], deg=True)

        # Setup the figure.
        figure = make_subplots(rows=2, cols=3, print_grid=False, shared_xaxes=True,
                               subplot_titles=['Attitude (YPR)', 'ENU Displacement', 'Body Velocity',
                                               'Attitude Std', 'ENU Position Std', 'Velocity Std'])

        figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'])
        for i in range(6):
            figure['layout']['xaxis%d' % (i + 1)].update(showticklabels=True, matches='x', **axis_layout)
        figure['layout']['yaxis1'].update(title="Degrees")
        figure['layout']['yaxis2'].update(title="Meters")
        figure['layout']['yaxis3'].update(title="Meters/Second")
        figure['layout']['yaxis4'].update(title="Degrees")
        figure['layout']['yaxis5'].update(title="Meters")
        figure['layout']['yaxis6'].update(title="Meters/Second")

        # Plot YPR.
        figure.add_trace(go.Scattergl(x=time, y=pose_data.ypr_deg[0, :], customdata=customdata, name='Yaw',
                                      legendgroup='yaw', mode='lines', line={'color': 'red'}),
                         1, 1)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.ypr_deg[1, :], customdata=customdata, name='Pitch',
                                      legendgroup='pitch', mode='lines', line={'color': 'green'}),
                         1, 1)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.ypr_deg[2, :], customdata=customdata, name='Roll',
                                      legendgroup='roll', mode='lines', line={'color': 'blue'}),
                         1, 1)

        figure.add_trace(go.Scattergl(x=time, y=pose_data.ypr_std_deg[0, :], customdata=customdata, name='Yaw',
                                      legendgroup='yaw', showlegend=False, mode='lines', line={'color': 'red'}),
                         2, 1)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.ypr_std_deg[1, :], customdata=customdata, name='Pitch',
                                      legendgroup='pitch', showlegend=False, mode='lines', line={'color': 'green'}),
                         2, 1)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.ypr_std_deg[2, :], customdata=customdata, name='Roll',
                                      legendgroup='roll', showlegend=False, mode='lines', line={'color': 'blue'}),
                         2, 1)

        # Plot position/displacement.
        position_ecef_m = np.array(geodetic2ecef(lat=pose_data.lla_deg[0, :], lon=pose_data.lla_deg[1, :],
                                                 alt=pose_data.lla_deg[2, :], deg=True))
        displacement_ecef_m = position_ecef_m - position_ecef_m[:, first_idx].reshape(3, 1)
        displacement_enu_m = c_enu_ecef.dot(displacement_ecef_m)
        figure.add_trace(go.Scattergl(x=time, y=displacement_enu_m[0, :], customdata=customdata, name='East',
                                      legendgroup='e', mode='lines', line={'color': 'red'}),
                         1, 2)
        figure.add_trace(go.Scattergl(x=time, y=displacement_enu_m[1, :], customdata=customdata, name='North',
                                      legendgroup='n', mode='lines', line={'color': 'green'}),
                         1, 2)
        figure.add_trace(go.Scattergl(x=time, y=displacement_enu_m[2, :], customdata=customdata, name='Up',
                                      legendgroup='u', mode='lines', line={'color': 'blue'}),
                         1, 2)

        figure.add_trace(go.Scattergl(x=time, y=pose_data.position_std_enu_m[0, :], customdata=customdata,
                                      name='East', legendgroup='e', showlegend=False, mode='lines',
                                      line={'color': 'red'}),
                         2, 2)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.position_std_enu_m[1, :], customdata=customdata,
                                      name='North', legendgroup='n', showlegend=False, mode='lines',
                                      line={'color': 'green'}),
                         2, 2)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.position_std_enu_m[2, :], customdata=customdata,
                                      name='Up', legendgroup='u', showlegend=False, mode='lines',
                                      line={'color': 'blue'}),
                         2, 2)

        # Plot velocity.
        figure.add_trace(go.Scattergl(x=time, y=pose_data.velocity_body_mps[0, :], customdata=customdata, name='X',
                                      legendgroup='x', mode='lines', line={'color': 'red'}),
                         1, 3)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.velocity_body_mps[1, :], customdata=customdata, name='Y',
                                      legendgroup='y', mode='lines', line={'color': 'green'}),
                         1, 3)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.velocity_body_mps[2, :], customdata=customdata, name='Z',
                                      legendgroup='z', mode='lines', line={'color': 'blue'}),
                         1, 3)
        figure.add_trace(go.Scattergl(x=time, y=np.linalg.norm(pose_data.velocity_body_mps, axis=0),
                                      customdata=customdata, name='3D',
                                      mode='lines', line={'color': 'orange', 'dash': 'dash'}),
                         1, 3)

        figure.add_trace(go.Scattergl(x=time, y=pose_data.velocity_std_body_mps[0, :], customdata=customdata,
                                      name='X', legendgroup='x', showlegend=False, mode='lines',
                                      line={'color': 'red'}),
                         2, 3)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.velocity_std_body_mps[1, :], customdata=customdata,
                                      name='Y', legendgroup='y', showlegend=False, mode='lines',
                                      line={'color': 'green'}),
                         2, 3)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.velocity_std_body_mps[2, :], customdata=customdata,
                                      name='Z', legendgroup='z', showlegend=False, mode='lines',
                                      line={'color': 'blue'}),
                         2, 3)

        self._add_figure(name="pose", figure=figure, title="Vehicle Pose vs. Time", custom_hover=True,
                         inject_js=self._custom_tooltip_js())

    def plot_calibration(self):
        """!
        @brief Plot the calibration progress over time.
        """
        if self.output_dir is None:
            return

        # Read the pose data.
        result = self.reader.read(message_types=[CalibrationStatus], **self.params)
        cal_data = result[CalibrationStatus.MESSAGE_TYPE]

        if len(cal_data.p1_time) == 0:
            self.logger.info('No calibration data available. Skipping calibration plot.')
            return

        time, axis_layout = self._resolve_x_axis(p1_time=cal_data.p1_time)
        time_customdata = self._time_hover_customdata(p1_time=cal_data.p1_time)

        # Map calibration stage enum values onto a [0, N) range for plotting.
        stage_map = {e.value: i for i, e in enumerate(CalibrationStage)}
        calibration_stage = [stage_map[s] for s in cal_data.calibration_stage]

        # Setup the figure.
        figure = make_subplots(rows=4, cols=1, print_grid=False, shared_xaxes=True,
                               subplot_titles=['<- Percent Complete // Stage ->', 'Mounting Angles',
                                               'Mounting Angle Standard Deviation', 'Travel Distance'],
                               specs=[[{"secondary_y": True}], [{}], [{}], [{}]])

        figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'])
        for i in range(4):
            figure['layout']['xaxis%d' % (i + 1)].update(showticklabels=True, **axis_layout)
        figure['layout']['yaxis1'].update(title="Percent Complete", range=[0, 100])
        figure['layout']['yaxis2'].update(ticktext=['%s' % e.name for e in CalibrationStage],
                                          tickvals=list(range(len(stage_map))))
        figure['layout']['yaxis3'].update(title="Degrees")
        figure['layout']['yaxis4'].update(title="Degrees")
        figure['layout']['yaxis5'].update(title="Meters")

        # Plot calibration stage and completion percentages.
        figure.add_trace(go.Scattergl(x=time, y=cal_data.gyro_bias_percent_complete, customdata=time_customdata,
                                      name='Gyro Bias Completion',
                                      mode='lines', line={'color': 'red'}),
                         1, 1)
        figure.add_trace(go.Scattergl(x=time, y=cal_data.accel_bias_percent_complete, customdata=time_customdata,
                                      name='Accel Bias Completion',
                                      mode='lines', line={'color': 'green'}),
                         1, 1)
        figure.add_trace(go.Scattergl(x=time, y=cal_data.mounting_angle_percent_complete, customdata=time_customdata,
                                      name='Mounting Angle Completion',
                                      mode='lines', line={'color': 'blue'}),
                         1, 1)

        figure.add_trace(go.Scattergl(x=time, y=calibration_stage, name='Stage', customdata=time_customdata,
                                      mode='lines', line={'color': 'black', 'dash': 'dash'}),
                         1, 1, secondary_y=True)

        # Plot mounting angles.
        figure.add_trace(go.Scattergl(x=time, y=cal_data.ypr_deg[0, :], name='Yaw', legendgroup='y',
                                      customdata=time_customdata, mode='lines', line={'color': 'red'}),
                         2, 1)
        figure.add_trace(go.Scattergl(x=time, y=cal_data.ypr_deg[1, :], name='Pitch', legendgroup='p',
                                      customdata=time_customdata, mode='lines', line={'color': 'green'}),
                         2, 1)
        figure.add_trace(go.Scattergl(x=time, y=cal_data.ypr_deg[2, :], name='Roll', legendgroup='r',
                                      customdata=time_customdata, mode='lines', line={'color': 'blue'}),
                         2, 1)

        figure.add_trace(go.Scattergl(x=time, y=cal_data.ypr_std_dev_deg[0, :], name='Yaw Std Dev', legendgroup='y',
                                      customdata=time_customdata, mode='lines', line={'color': 'red'}),
                         3, 1)
        figure.add_trace(go.Scattergl(x=time, y=cal_data.ypr_std_dev_deg[1, :], name='Pitch Std Dev', legendgroup='p',
                                      customdata=time_customdata, mode='lines', line={'color': 'green'}),
                         3, 1)
        figure.add_trace(go.Scattergl(x=time, y=cal_data.ypr_std_dev_deg[2, :], name='Roll Std Dev', legendgroup='r',
                                      customdata=time_customdata, mode='lines', line={'color': 'blue'}),
                         3, 1)

        # Threshold reference lines only have 2 points (first/last time), so they don't get per-point hover data.
        thresh_time = time[np.array((0, -1))]
        figure.add_trace(go.Scattergl(x=thresh_time, y=[cal_data.mounting_angle_max_std_dev_deg[0]] * 2,
                                      name='Max Yaw Std Dev', legendgroup='y',
                                      mode='lines', line={'color': 'red', 'dash': 'dash'}),
                         3, 1)
        figure.add_trace(go.Scattergl(x=thresh_time, y=[cal_data.mounting_angle_max_std_dev_deg[1]] * 2,
                                      name='Max Pitch Std Dev', legendgroup='p',
                                      mode='lines', line={'color': 'green', 'dash': 'dash'}),
                         3, 1)
        figure.add_trace(go.Scattergl(x=thresh_time, y=[cal_data.mounting_angle_max_std_dev_deg[2]] * 2,
                                      name='Max Roll Std Dev', legendgroup='r',
                                      mode='lines', line={'color': 'blue', 'dash': 'dash'}),
                         3, 1)

        # Plot travel distance.
        figure.add_trace(go.Scattergl(x=time, y=cal_data.travel_distance_m, name='Travel Distance',
                                      customdata=time_customdata, mode='lines', line={'color': 'blue'}),
                         4, 1)
        figure.add_trace(go.Scattergl(x=thresh_time, y=[cal_data.min_travel_distance_m] * 2,
                                      name='Min Travel Distance',
                                      mode='lines', line={'color': 'black', 'dash': 'dash'}),
                         4, 1)

        self._add_figure(name="calibration", figure=figure, title="Calibration Status", custom_hover=True,
                         inject_js=self._custom_tooltip_js())

    def plot_solution_type(self):
        """!
        @brief Plot the solution type over time.
        """
        if self.output_dir is None:
            return

        # Read the pose data.
        result = self.reader.read(message_types=[PoseMessage], source_ids=self.default_source_id, **self.params)
        pose_data = result[PoseMessage.MESSAGE_TYPE]

        if len(pose_data.p1_time) == 0:
            self.logger.info('No pose data available. Skipping solution type plot.')
            return

        # Setup the figure.
        figure = make_subplots(rows=1, cols=1, print_grid=False, shared_xaxes=True, subplot_titles=['Solution Type'])
        figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'])
        figure['layout']['xaxis'].update(**self._x_axis_layout())
        figure['layout']['yaxis1'].update(title="Solution Type",
                                          ticktext=['%s (%d)' % (e.name, e.value) for e in SolutionType],
                                          tickvals=[e.value for e in SolutionType])

        is_gnss_rx = (pose_data.flags & PoseMessage.FLAG_RECEIVER_SOLUTION) != 0
        is_nav_engine = ~is_gnss_rx

        # Plot nav engine solutions.
        if np.any(is_nav_engine):
            idx = is_nav_engine
            p1_time = pose_data.p1_time[idx]
            gps_time = pose_data.gps_time[idx]
            time, _ = self._resolve_x_axis(p1_time=p1_time, gps_time=gps_time)
            customdata = self._time_hover_customdata(p1_time=p1_time, gps_time=gps_time)
            figure.add_trace(go.Scattergl(x=time, y=pose_data.solution_type[idx], customdata=customdata,
                                          name='Nav Engine', mode='markers'),
                             1, 1)

        # Plot GNSS receiver solutions, if any.
        if np.any(is_gnss_rx):
            idx = is_gnss_rx
            p1_time = pose_data.p1_time[idx]
            gps_time = pose_data.gps_time[idx]
            time, _ = self._resolve_x_axis(p1_time=p1_time, gps_time=gps_time)
            customdata = self._time_hover_customdata(p1_time=p1_time, gps_time=gps_time)
            figure.add_trace(go.Scattergl(x=time, y=pose_data.solution_type[idx], customdata=customdata,
                                          name='Receiver Solution',
                                          mode='markers', marker={'color': 'red', 'symbol': 'diamond-open'}),
                             1, 1)

        self._add_figure(name="solution_type", figure=figure, title="Solution Type", custom_hover=True,
                         inject_js=self._custom_tooltip_js())

    def plot_stationary_status(self):
        """!
        @brief Plot the stationary status over time.
        """
        if self.output_dir is None:
            return

        # Read the pose data.
        result = self.reader.read(message_types=[PoseMessage], source_ids=self.default_source_id, **self.params)
        pose_data = result[PoseMessage.MESSAGE_TYPE]

        if len(pose_data.p1_time) == 0:
            self.logger.info('No pose data available. Skipping solution type plot.')
            return

        # Set up the figure.
        figure = make_subplots(rows=1, cols=1, print_grid=False, shared_xaxes=True,
                               subplot_titles=['Stationary Status'])

        figure['layout']['yaxis1'].update(title="Stationary Status",
                                          ticktext=['Moving', 'Stationary'],
                                          tickvals=[0, PoseMessage.FLAG_STATIONARY])

        time, axis_layout = self._resolve_x_axis(p1_time=pose_data.p1_time, gps_time=pose_data.gps_time)
        customdata = self._time_hover_customdata(p1_time=pose_data.p1_time, gps_time=pose_data.gps_time)
        figure['layout']['xaxis'].update(**axis_layout)

        # Extract the stationary status from the pose data flags.
        stationary_status = pose_data.flags & PoseMessage.FLAG_STATIONARY

        figure.add_trace(go.Scattergl(x=time, y=stationary_status, customdata=customdata, mode='markers'), 1, 1)

        self._add_figure(name="stationary_status", figure=figure, title="Stationary Status", custom_hover=True,
                         inject_js=self._custom_tooltip_js())

    def _plot_displacement(self, source, p1_time, solution_type, displacement_enu_m, std_enu_m, gps_time=None,
                           title='Displacement'):
        """!
        @brief Generate a topocentric (top-down) plot of position displacement, as well as plot of displacement over
               time.
        """
        if self.output_dir is None:
            return

        # Note: _resolve_x_axis() can do this internally, but we also need it for the topo customdata below.
        if gps_time is None:
            gps_time = self.time_provider.p1_to_gps(p1_time)

        time, axis_layout = self._resolve_x_axis(p1_time=p1_time, gps_time=gps_time)
        time_customdata = self._time_hover_customdata(p1_time=p1_time, gps_time=gps_time)

        # The topocentric plot's axes are spatial (East/North), not time, so unlike time_customdata above (which
        # carries only whichever of P1/GPS time is not already reflected by the X axis), its hover text needs both
        # times directly -- neither is recoverable from a point's X/Y position.
        topo_customdata = np.vstack((p1_time, gps_time, displacement_enu_m, std_enu_m))
        time_customdata = np.vstack((time_customdata, displacement_enu_m, std_enu_m))

        # Setup the figure.
        topo_figure = make_subplots(rows=1, cols=1, print_grid=False, shared_xaxes=False, subplot_titles=[title])
        topo_figure['layout']['xaxis1'].update(title="East (m)")
        topo_figure['layout']['yaxis1'].update(title="North (m)")

        time_figure = make_subplots(rows=4, cols=1, print_grid=False, shared_xaxes=True,
                                    subplot_titles=['3D', 'East', 'North', 'Up'])
        time_figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'])
        for i in range(4):
            time_figure['layout']['xaxis%d' % (i + 1)].update(showticklabels=True, **axis_layout)
        time_figure['layout']['yaxis1'].update(title=f"{title} (m)")
        time_figure['layout']['yaxis2'].update(title=f"{title} (m)")
        time_figure['layout']['yaxis3'].update(title=f"{title} (m)")
        time_figure['layout']['yaxis4'].update(title=f"{title} (m)")

        # Remove invalid solutions.
        valid_idx = np.logical_and(~np.isnan(p1_time), solution_type != SolutionType.Invalid)
        if not np.any(valid_idx):
            self.logger.info('No valid position solutions detected. Skipping displacement plots.')
            return

        # Add statistics to the figure title.
        format = 'Mean: %(mean).2f m, Median: %(median).2f m, Min: %(min).2f m, Max: %(max).2f m, Std Dev: %(std).2f m'
        displacement_3d_m = np.linalg.norm(displacement_enu_m, axis=0)
        extra_text = '[All] ' + format % {
            'mean': np.mean(displacement_3d_m),
            'median': np.median(displacement_3d_m),
            'min': np.min(displacement_3d_m),
            'max': np.max(displacement_3d_m),
            'std': np.std(displacement_3d_m),
        }

        idx = solution_type == SolutionType.RTKFixed
        if np.any(idx):
            displacement_3d_m = np.linalg.norm(displacement_enu_m[:, idx], axis=0)
            extra_text += '<br>[Fixed] ' + format % {
                'mean': np.mean(displacement_3d_m),
                'median': np.median(displacement_3d_m),
                'min': np.min(displacement_3d_m),
                'max': np.max(displacement_3d_m),
                'std': np.std(displacement_3d_m),
            }

        topo_figure.update_layout(title_text=extra_text)
        time_figure.update_layout(title_text=extra_text)

        # Plot the data.
        max_3d_diff_m = [0.0]
        def _plot_data(name, idx, marker_style=None):
            style = {'mode': 'markers', 'marker': {'size': 8}, 'showlegend': True, 'legendgroup': name}
            if marker_style is not None:
                style['marker'].update(marker_style)

            if np.any(idx):
                topo_cd = topo_customdata[:, idx]
                time_cd = time_customdata[:, idx]
                topo_figure.add_trace(go.Scattergl(x=displacement_enu_m[0, idx], y=displacement_enu_m[1, idx],
                                                   name=name, customdata=topo_cd, **style), 1, 1)

                displacement_3d_m = np.linalg.norm(displacement_enu_m[:, idx], axis=0)
                max_3d_diff_m[0] = max(max_3d_diff_m[0], np.nanmax(displacement_3d_m))
                time_figure.add_trace(go.Scattergl(x=time[idx], y=displacement_3d_m,
                                                   name=name, customdata=time_cd, **style), 1, 1)
                style['showlegend'] = False
                time_figure.add_trace(go.Scattergl(x=time[idx], y=displacement_enu_m[0, idx], name=name,
                                                   customdata=time_cd, **style), 2, 1)
                time_figure.add_trace(go.Scattergl(x=time[idx], y=displacement_enu_m[1, idx], name=name,
                                                   customdata=time_cd, **style), 3, 1)
                time_figure.add_trace(go.Scattergl(x=time[idx], y=displacement_enu_m[2, idx], name=name,
                                                   customdata=time_cd, **style), 4, 1)
            else:
                # If there's no data, draw a dummy trace so it shows up in the legend anyway.
                topo_figure.add_trace(go.Scattergl(x=[np.nan], y=[np.nan], name=name, visible='legendonly', **style),
                                      1, 1)
                time_figure.add_trace(go.Scattergl(x=[np.nan], y=[np.nan], name=name, visible='legendonly', **style),
                                      1, 1)

        for type, info in _SOLUTION_TYPE_MAP.items():
            _plot_data(info.name, solution_type == type, marker_style=info.style)

        # Set the 3D displacement Y-axis limits to start at 0 and encompass the data.
        max_y = 1.2 * max_3d_diff_m[0]
        if max_y == 0.0:
            max_y = 1.0
        time_figure['layout']['yaxis1'].update(range=[0, max_y])

        name = source.replace(' ', '_').lower()

        # Topocentric hover: X/Y are spatial (East/North), not time, so both P1 and GPS time must come directly from
        # customdata (rows 0/1) rather than from the point's axis position -- see BuildTimeHoverTextFromTimes().
        _DISPLACEMENT_TOPO_HOVER_JS = """\
figure.on('plotly_hover', function(data) {
  let point = data.points[0];
  if (!point.data.customdata) {
    return;
  }
  let new_text = BuildTimeHoverTextFromTimes(GetCustomData(point, 0), GetCustomData(point, 1));
  new_text += `<br>Delta (ENU): (${GetCustomData(point, 2).toFixed(2)}, ${GetCustomData(point, 3).toFixed(2)}, ` +
              `${GetCustomData(point, 4).toFixed(2)}) m`;
  new_text += `<br>Std (ENU): (${GetCustomData(point, 5).toFixed(2)}, ${GetCustomData(point, 6).toFixed(2)}, ` +
              `${GetCustomData(point, 7).toFixed(2)}) m`;
  ShowCustomTooltip(point, GetCustomTooltipHTML(point.data.name, undefined, new_text));
});
figure.on('plotly_unhover', function(data) {
  HideCustomTooltip();
});
        """

        # Time-series hover: like _custom_tooltip_js(), but with extra Delta/Std (ENU) customdata rows appended.
        _DISPLACEMENT_TIME_HOVER_JS = """\
figure.on('plotly_hover', function(data) {
  let point = data.points[0];
  if (!point.data.customdata) {
    return;
  }
  let new_text = BuildTimeHoverText(point.x, GetCustomData(point, 0));
  new_text += `<br>Delta (ENU): (${GetCustomData(point, 1).toFixed(2)}, ${GetCustomData(point, 2).toFixed(2)}, ` +
              `${GetCustomData(point, 3).toFixed(2)}) m`;
  new_text += `<br>Std (ENU): (${GetCustomData(point, 4).toFixed(2)}, ${GetCustomData(point, 5).toFixed(2)}, ` +
              `${GetCustomData(point, 6).toFixed(2)}) m`;
  ShowCustomTooltip(point, GetCustomTooltipHTML(point.data.name, undefined, new_text));
});
figure.on('plotly_unhover', function(data) {
  HideCustomTooltip();
});
        """ + self._GPS_TICK_REFORMAT_JS

        self._add_figure(name=f"{name}_top_down", figure=topo_figure, title=f"{source}: Top-Down (Topocentric)",
                         custom_hover=True, inject_js=_DISPLACEMENT_TOPO_HOVER_JS)
        self._add_figure(name=f"{name}_vs_time", figure=time_figure, title=f"{source}: vs. Time",
                         custom_hover=True, inject_js=_DISPLACEMENT_TIME_HOVER_JS)

    def plot_pose_error(self, reference: ReferenceData):
        """!
        @brief Plot position error vs. a truth reference.

        Position error is plotted both top-down (topocentric) and over time.

        @param reference The truth reference to compare against.
        """
        return self._plot_pose_displacement(reference=reference)

    def plot_position_displacement(self, reference_type: str):
        """!
        @brief Plot position displacement over time compared with a fixed reference from the log data (first position,
               median, etc.).

        @param reference_type The desired reference type name.
        """
        # Default to the median position taken from this log's own data (we use median instead of centroid just in
        # case there are one or two huge outliers).
        reference = ReferenceData.resolve_cli_argument(reference=reference_type, loader=self.reader,
                                                       source_id=self.default_source_id)
        if reference is None:
            self.logger.info('No valid position solutions detected. Skipping displacement plots.')
            return None
        else:
            return self._plot_pose_displacement(reference=reference)

    def _plot_pose_displacement(self, reference: Optional[ReferenceData] = None):
        """!
        @brief Generate a topocentric (top-down) plot of position displacement (or error, if `reference` is an
               independent truth source -- see @ref ReferenceData) vs a reference position, as well as a plot of
               displacement/error over time.

        @param reference The reference to compare against. If `None`, defaults to the median position taken from
               this log's own data.
        """
        if self.output_dir is None:
            return None

        # Read the pose data.
        result = self.reader.read(message_types=[PoseMessage], source_ids=self.default_source_id, **self.params)
        pose_data = result[PoseMessage.MESSAGE_TYPE]

        if len(pose_data.p1_time) == 0:
            self.logger.info('No pose data available. Skipping displacement plots.')
            return None

        # Remove invalid solutions.
        valid_idx = np.logical_and(~np.isnan(pose_data.p1_time), pose_data.solution_type != SolutionType.Invalid)
        if not np.any(valid_idx):
            self.logger.info('No valid position solutions detected. Skipping displacement plots.')
            return None

        p1_time = pose_data.p1_time[valid_idx]
        gps_time = pose_data.gps_time[valid_idx]
        solution_type = pose_data.solution_type[valid_idx]
        lla_deg = pose_data.lla_deg[:, valid_idx]
        std_enu_m = pose_data.position_std_enu_m[:, valid_idx]

        position_ecef_m = np.array(geodetic2ecef(lat=lla_deg[0, :], lon=lla_deg[1, :], alt=lla_deg[2, :], deg=True))

        # Interpolate the reference position onto this log's GPS timestamps, warning if the reference does not fully
        # cover this log's time range. Any timestamps that fall outside the reference's coverage (or that could not
        # be interpolated, e.g. due to a gap in the reference data) are dropped below.
        valid_ref_idx = reference.get_coverage_mask(gps_time)
        reference_ecef_m = reference.interpolate_position_ecef_m(gps_time)
        valid_ref_idx = np.logical_and(valid_ref_idx, ~np.any(np.isnan(reference_ecef_m), axis=0))
        if not np.any(valid_ref_idx):
            self.logger.warning(f"Reference data '{reference.description}' does not overlap with this log's time "
                                f"range. Skipping displacement plots.")
            return None
        elif not np.all(valid_ref_idx):
            p1_time = p1_time[valid_ref_idx]
            gps_time = gps_time[valid_ref_idx]
            solution_type = solution_type[valid_ref_idx]
            lla_deg = lla_deg[:, valid_ref_idx]
            std_enu_m = std_enu_m[:, valid_ref_idx]
            position_ecef_m = position_ecef_m[:, valid_ref_idx]
            reference_ecef_m = reference_ecef_m[:, valid_ref_idx]

        displacement_ecef_m = position_ecef_m - reference_ecef_m
        c_enu_ecef = get_enu_rotation_matrix(*lla_deg[0:2, 0], deg=True)
        displacement_enu_m = c_enu_ecef.dot(displacement_ecef_m)

        axis_title = reference.displacement_label
        source = f'Position {axis_title} vs. {"Reference" if reference.is_truth else reference.description}'

        self._plot_displacement(source=source, title=axis_title,
                                p1_time=p1_time, gps_time=gps_time, solution_type=solution_type,
                                displacement_enu_m=displacement_enu_m, std_enu_m=std_enu_m)

        return displacement_enu_m

    def plot_relative_position(self):
        """!
        @brief Generate a topocentric (top-down) plot of relative position vs base station, as well as plot of relative
               position over time.
        """
        if self.output_dir is None:
            return

        # Read the pose data.
        result = self.reader.read(message_types=[RelativeENUPositionMessage], **self.params)
        relative_position_data = result[RelativeENUPositionMessage.MESSAGE_TYPE]

        if len(relative_position_data.p1_time) == 0:
            self.logger.info('No relative ENU data available. Skipping relative position vs. base station plots.')
            return

        # Remove invalid solutions.
        valid_idx = ~np.isnan(relative_position_data.relative_position_enu_m[0, :])

        if not np.any(valid_idx):
            self.logger.info('No valid position solutions detected. Skipping relative position vs. base station plots.')
            return

        p1_time = relative_position_data.p1_time[valid_idx]
        gps_time = relative_position_data.gps_time[valid_idx]
        solution_type = relative_position_data.solution_type[valid_idx]
        displacement_enu_m = relative_position_data.relative_position_enu_m[:, valid_idx]
        std_enu_m = relative_position_data.position_std_enu_m[:, valid_idx]

        self._plot_displacement('Position vs. Base Station', p1_time=p1_time, gps_time=gps_time,
                                solution_type=solution_type, displacement_enu_m=displacement_enu_m,
                                std_enu_m=std_enu_m)

    def plot_map(self, mapbox_token):
        """!
        @brief Plot a map of the position data.
        """
        pose_source_ids = self._get_pose_source_ids()
        if self.output_dir is None or len(pose_source_ids) == 0:
            return

        mapbox_token = self.get_mapbox_token(mapbox_token)
        if mapbox_token is None or mapbox_token == "":
            self.logger.info('*' * 80 + '\n\n' +
                             'Mapbox token not specified. Disabling satellite imagery. For satellite imagery,\n'
                             'please provide a Mapbox token using --mapbox-token or by setting the\n'
                             'MAPBOX_ACCESS_TOKEN environment variable.' +
                             '\n\n' + '*' * 80)
            self._mapbox_token_missing = True
            mapbox_token = None

        # Plotly's Mapbox/WebGL map trace hover renderer reads hover content from calcdata, baked in at plot time, and
        # does not pick up a later client-side mutation of fullData.text the way cartesian (Scatter/Scattergl) traces
        # do, so we cannot inject a plotly_hover() function like we do for most other plots. Instead, we have to use
        # Plotly's `hovertemplate` function.
        #
        # hovertemplate can't apply date/time formatting to a bare *numeric* customdata value (that only works for a
        # `%{x}` tied to a real date-typed axis) -- but a customdata entry with no format spec at all is substituted
        # verbatim, so we precompute the UTC string in Python (cheap, vectorized) and reference it that way.
        _POSITION_HOVERTEMPLATE = (
            "LLA: %{lat:.8f}, %{lon:.8f}, %{customdata[4]:.2f}<br>"
            "Rel: %{customdata[0]:.3f} sec (P1: %{customdata[1]:.3f} sec)<br>"
            "UTC: %{customdata[8]}<br>"
            "GPS: %{customdata[2]:.0f}:%{customdata[3]:.3f}<br>"
            "Std (ENU): (%{customdata[5]:.2f}, %{customdata[6]:.2f}, %{customdata[7]:.2f}) m"
        )

        def _build_position_customdata(p1_time: np.ndarray, gps_time: np.ndarray,
                                       lla_deg: np.ndarray, std_enu_m: np.ndarray) -> list:
            rel_time = p1_time - float(self.reader.t0)
            gps_week = np.floor(gps_time / SECONDS_PER_WEEK)
            gps_tow_sec = gps_time - gps_week * SECONDS_PER_WEEK

            utc_times = self.time_provider.gps_sec_to_datetime64_array(gps_time)
            utc_strs = np.where(np.isnat(utc_times), 'N/A',
                                np.datetime_as_string(utc_times, unit='ms'))
            utc_strs = np.char.replace(utc_strs, 'T', ' ')

            # Note: unlike the field-major (num_fields x N) arrays built by _time_hover_customdata() for use with our
            # own GetCustomData() JS helper, Plotly's native `hovertemplate` expects customdata in the opposite,
            # point-major layout -- one row per point, indexed as customdata[pointIndex][fieldIndex].
            #
            # utc_strs is a string column mixed in with the numeric ones above, so this can't be a single numpy
            # array (that would coerce every column to strings, breaking the numeric %{customdata[N]:.3f}-style
            # formatting for the rest); build it as a plain list of per-point rows instead.
            numeric = np.column_stack((rel_time, p1_time, gps_week, gps_tow_sec, lla_deg[2], std_enu_m[0],
                                       std_enu_m[1], std_enu_m[2]))
            return [row.tolist() + [utc_str] for row, utc_str in zip(numeric, utc_strs)]

        # Add data to the map.
        map_data = []
        indices_by_engine = defaultdict(list)

        def _plot_data(name, selected_idx, flags, source_id, lla_deg, customdata_all, marker_style=None):
            style = {'mode': 'markers', 'marker': {'size': 8}, 'showlegend': True}
            if marker_style is not None:
                style['marker'].update(marker_style)

            # Only put default source ID on map by default.
            legendgroup = None if len(pose_source_ids) == 1 else source_id
            visible = None if source_id == min(pose_source_ids) else 'legendonly'

            if np.any(selected_idx):
                is_nav_engine = np.logical_and(selected_idx, flags & PoseMessage.FLAG_RECEIVER_SOLUTION == 0)
                is_gnss_rx = np.logical_and(selected_idx, flags & PoseMessage.FLAG_RECEIVER_SOLUTION != 0)

                if np.any(is_nav_engine):
                    idx = is_nav_engine
                    map_data.append(go.Scattermapbox(lat=lla_deg[0, idx], lon=lla_deg[1, idx], name=name,
                                                     customdata=[customdata_all[i] for i in np.nonzero(idx)[0]],
                                                     hovertemplate=_POSITION_HOVERTEMPLATE,
                                                     legendgroup=legendgroup, visible=visible, **style))
                    indices_by_engine['Nav Engine'].append(len(map_data) - 1)

                if np.any(is_gnss_rx):
                    idx = is_gnss_rx
                    style['marker']['opacity'] = 0.5
                    style['marker']['size'] = 5
                    map_data.append(go.Scattermapbox(lat=lla_deg[0, idx], lon=lla_deg[1, idx],
                                                     name=name + ' (Receiver Solution)',
                                                     customdata=[customdata_all[i] for i in np.nonzero(idx)[0]],
                                                     hovertemplate=_POSITION_HOVERTEMPLATE,
                                                     legendgroup=legendgroup, visible=visible, **style))
                    indices_by_engine['Receiver Solution'].append(len(map_data) - 1)

            else:
                # If there's no data, draw a dummy trace so it shows up in the legend anyway.
                map_data.append(go.Scattermapbox(lat=[np.nan], lon=[np.nan], name=name, legendgroup=legendgroup,
                                                 visible='legendonly', **style))
                indices_by_engine['Nav Engine'].append(len(map_data) - 1)

        # Read the pose data.
        have_pose_data = False
        for source_id in pose_source_ids:
            result = self.reader.read(message_types=[PoseMessage], source_ids=[source_id], **self.params)
            pose_data = result[PoseMessage.MESSAGE_TYPE]

            if len(pose_data.p1_time) == 0:
                self.logger.info('No pose data available for source ID {}. Skipping.'.format(source_id))
                continue

            # Remove invalid solutions.
            valid_idx = np.logical_and(~np.isnan(pose_data.p1_time), pose_data.solution_type != SolutionType.Invalid)
            if not np.any(valid_idx):
                self.logger.info('No valid position solutions detected for source ID {}.'.format(source_id))
                continue

            have_pose_data = True

            solution_type = pose_data.solution_type[valid_idx]
            flags = pose_data.flags[valid_idx]
            lla_deg = pose_data.lla_deg[:, valid_idx]
            std_enu_m = pose_data.position_std_enu_m[:, valid_idx]

            customdata_all = _build_position_customdata(p1_time=pose_data.p1_time[valid_idx],
                                                        gps_time=pose_data.gps_time[valid_idx],
                                                        lla_deg=lla_deg, std_enu_m=std_enu_m)

            for type, info in _SOLUTION_TYPE_MAP.items():
                if len(pose_source_ids) > 1:
                    name = info.name + ' [source_id=' + str(source_id) + ']'
                else:
                    name = info.name
                _plot_data(name=name, selected_idx=solution_type == type, flags=flags, source_id=source_id,
                           lla_deg=lla_deg, customdata_all=customdata_all, marker_style=info.style)

        if not have_pose_data:
            return

        # Create the map.
        title = 'Vehicle Trajectory'
        if mapbox_token is None:
            title += '<br>For satellite imagery, please provide a Mapbox token using --mapbox-token or by setting ' \
                     'MAPBOX_ACCESS_TOKEN.'

        layout = go.Layout(
            autosize=True,
            hovermode='closest',
            title=title,
            mapbox=dict(
                accesstoken=mapbox_token,
                bearing=0,
                center=dict(
                    lat=lla_deg[0, 0],
                    lon=lla_deg[1, 0],
                ),
                pitch=0,
                zoom=18,
                style='open-street-map' if mapbox_token is None else 'satellite-streets',
            ),
        )

        figure = go.Figure(data=map_data, layout=layout)
        figure['layout'].update(showlegend=True)

        # Add quality selection buttons.
        num_traces = len(figure.data)
        buttons = [dict(label='All', method='restyle', args=['visible', [True] * num_traces])]
        for name, indices in sorted(indices_by_engine.items()):
            if len(indices) == 0:
                continue
            visible = np.full((num_traces,), False)
            visible[indices] = True
            buttons.append(dict(label=name, method='restyle', args=['visible', visible]))
        figure['layout']['updatemenus'] = [{
            'type': 'buttons',
            'direction': 'left',
            'buttons': buttons,
            'x': 0.0,
            'xanchor': 'left',
            'y': 1.1,
            'yanchor': 'top'
        }]

        self._add_figure(name="map", figure=figure, title="Vehicle Trajectory (Map)", config={'scrollZoom': True})

    def plot_gnss_skyplot(self, decimate=True):
        for source_id in self._get_gnss_antenna_source_ids():
            self._plot_gnss_skyplot_for_source(source_id, decimate=decimate)

    def _plot_gnss_skyplot_for_source(self, source_id: int, decimate=True):
        label = self._gnss_antenna_label(source_id)

        # Read the GNSS signal data.
        data = self._get_gnss_signals_data(source_id)
        if len(data.messages) == 0:
            self.logger.info(f'No GNSS signal data available for source ID {source_id}. Skipping sky plot.')
            return
        have_gnss_signals_message = not data.using_legacy_satellite_message

        # Setup the figure.
        figure = go.Figure()
        figure['layout'].update(title=f'{label} GNSS Sky Plot')
        figure['layout']['polar']['radialaxis'].update(range=[90, 0])
        figure['layout']['polar']['angularaxis'].update(visible=False)

        # Assign colors by PRN.
        sv_hashes = np.unique(data.sv_data['sv_hash'])
        prns = np.unique([get_prn(h) for h in sv_hashes])
        color_by_prn = self._assign_colors(prns)

        # List the available signal types for each SV.
        signal_hashes = np.unique(data.signal_data['signal_hash'])
        signal_types_by_sv = defaultdict(list)
        for signal_hash in signal_hashes:
            signal_type = get_signal_type(signal_hash)
            signal_types_by_sv[get_satellite_hash(signal_hash)].append(signal_type)

        # Convert the full list of signals for all time epochs to corresponding satellites.
        all_signal_sv_hashes = np.array([get_satellite_hash(s) for s in data.signal_data['signal_hash']])

        # Plot each satellite.
        indices_by_system = defaultdict(list)
        color_by_sv_format = []
        color_by_cn0_format = []
        for sv_hash in sv_hashes:
            sv_id = SatelliteID(sv_hash=sv_hash)
            name = sv_id.to_string(short=False)
            system = sv_id.get_satellite_type()

            idx = data.sv_data['sv_hash'] == sv_hash
            p1_time = data.sv_data['p1_time'][idx]
            az_deg = data.sv_data['azimuth_deg'][idx]
            el_deg = data.sv_data['elevation_deg'][idx]

            # Get the C/N0 data for all signals from this satellite, then find the max at each epoch. We'll use that to
            # set the color-by-C/N0 scale.
            #
            # Reference: https://stackoverflow.com/a/43094244
            idx = all_signal_sv_hashes == sv_hash
            cn0_per_epoch = np.split(data.signal_data['cn0_dbhz'][idx],
                                     np.unique(data.signal_data['p1_time'][idx], return_index=True)[1][1:])
            max_cn0_dbhz = np.array([max(cn0) for cn0 in cn0_per_epoch])

            if have_gnss_signals_message:
                sv_signal_types = signal_types_by_sv[sv_hash]
                signal_type_str = ", ".join([pretty_print_gnss_enum(t, omit_satellite_type=True,
                                                                    omit_component_hint=True)
                                             for t in sv_signal_types])
                name_str = f'{name} ({signal_type_str})'
            else:
                name_str = name

            # Decimate the data to 30 second intervals.
            if decimate and len(p1_time) > 1:
                interval_sec = 30.0
                dt_sec = np.round(np.min(np.diff(p1_time)) / 0.1) * 0.1
                if dt_sec < interval_sec:
                    rounded_time = np.round(p1_time / interval_sec) * interval_sec
                    idx = np.where(np.diff(rounded_time, prepend=rounded_time[0]) > 0.01)[0]

                    # If this satellite appears for < interval_sec and all of its timestamps happen to round to the same
                    # time, idx will be empty. Pick the first point where az/el is available.
                    if len(idx) == 0:
                        idx = [find_first(~np.isnan(el_deg))]
                        if idx[0] < 0:
                            continue

                    p1_time = p1_time[idx]
                    az_deg = az_deg[idx]
                    el_deg = el_deg[idx]
                    max_cn0_dbhz = max_cn0_dbhz[idx]

                    # If we never had ephemeris for this satellite, or were otherwise not able to compute az/el, we
                    # can't put this satellite on the sky plot.
                    if np.all(np.isnan(el_deg)):
                        continue

            # Plot the data. We set styles for both coloring by SV and by C/N0. We'll add buttons below to switch
            # between styles.
            color_by_sv_format.append({'color': color_by_prn[sv_id.get_prn()]})
            color_by_cn0_format.append({'cmin': 20, 'cmax': 55, 'colorscale': 'RdBu', 'showscale': True,
                                        'colorbar': {'x': 0}, 'color': max_cn0_dbhz})

            text = ['P1: %.1f sec<br>(Az, El): (%.2f, %.2f) deg<br>C/N0: %.1f dB-Hz' %
                    (t, a, e, c) for t, a, e, c in zip(p1_time, az_deg, el_deg, max_cn0_dbhz)]
            figure.add_trace(go.Scatterpolargl(r=el_deg, theta=(90 - az_deg), text=text,
                                               name=name_str, hoverinfo='name+text',
                                               mode='markers', marker=color_by_sv_format[-1]))
            indices_by_system[system].append(len(figure.data) - 1)

        # Add selection buttons for each system and for choosing between coloring by SV and C/N0.
        num_traces = len(figure.data)
        num_svs = len(sv_hashes)
        buttons = [dict(label=f'All ({num_svs})', method='restyle', args=['visible', [True] * num_traces])]
        for system, indices in sorted(indices_by_system.items()):
            if len(indices) == 0:
                continue
            visible = np.full((num_traces,), False)
            visible[indices] = True
            buttons.append(dict(label=f'{str(system)} ({len(indices)})', method='restyle', args=['visible', visible]))
        updatemenus = [{
            'type': 'buttons',
            'direction': 'left',
            'buttons': buttons,
            'x': 0.0,
            'xanchor': 'left',
            'y': 1.1,
            'yanchor': 'top'
        }]

        updatemenus += [{
            'type': 'buttons',
            'direction': 'left',
            'buttons': [
                dict(label='Color By SV', method='restyle', args=['marker', color_by_sv_format]),
                dict(label='Color By C/N0', method='restyle', args=['marker', color_by_cn0_format])
            ],
            'x': 0.0,
            'xanchor': 'left',
            'y': 1.045,
            'yanchor': 'top'
        }]

        figure['layout']['updatemenus'] = updatemenus

        name = self._gnss_plot_filename('gnss_skyplot', source_id)
        self._add_figure(name=name, figure=figure, title=f'{label} GNSS Sky Plot')

    def plot_gnss_cn0(self):
        for source_id in self._get_gnss_antenna_source_ids():
            self._plot_gnss_cn0_for_source(source_id)

    def _plot_gnss_cn0_for_source(self, source_id: int):
        label = self._gnss_antenna_label(source_id)

        # Read the GNSS signal data.
        data = self._get_gnss_signals_data(source_id)
        if len(data.messages) == 0:
            self.logger.info(f'No GNSS signal data available for source ID {source_id}. Skipping C/N0 plot.')
            return
        have_gnss_signals_message = not data.using_legacy_satellite_message

        # Setup the figure.
        title = 'C/N0'
        if not have_gnss_signals_message:
            title += ' (L1 Only)'
        figure = make_subplots(
            rows=1, cols=1,  print_grid=False, shared_xaxes=True,
            subplot_titles=[title])

        figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'])
        figure['layout']['xaxis1'].update(showticklabels=True, **self._x_axis_layout())
        figure['layout']['yaxis1'].update(title="C/N0 (dB-Hz)")

        # Assign colors by PRN.
        signal_hashes = np.unique(data.signal_data['signal_hash'])
        prns = np.unique([get_prn(h) for h in signal_hashes])
        color_by_prn = self._assign_colors(prns)

        # Plot each signal.
        indices_by_signal_type = defaultdict(list)
        for signal_hash in signal_hashes:
            signal = SignalID(signal_hash=signal_hash)
            name = signal.to_string(short=False)

            idx = data.signal_data['signal_hash'] == signal_hash
            p1_time = data.signal_data['p1_time'][idx]
            gps_time = data.signal_data['gps_time'][idx]
            cn0_dbhz = data.signal_data['cn0_dbhz'][idx]

            time, _ = self._resolve_x_axis(p1_time=p1_time, gps_time=gps_time)
            customdata = self._time_hover_customdata(p1_time=p1_time, gps_time=gps_time)
            figure.add_trace(go.Scattergl(x=time, y=cn0_dbhz, customdata=customdata, name=name,
                                          mode='markers', marker={'color': color_by_prn[signal.get_prn()]}),
                             1, 1)
            indices_by_signal_type[signal.signal_type].append(len(figure.data) - 1)

        # Add signal type selection buttons.
        num_traces = len(figure.data)
        buttons = [dict(label=f'All ({len(signal_hashes)})', method='restyle', args=['visible', [True] * num_traces])]
        for signal_type, indices in sorted(indices_by_signal_type.items()):
            if len(indices) == 0:
                continue
            visible = np.full((num_traces,), False)
            visible[indices] = True
            buttons.append(dict(label=f'{pretty_print_gnss_enum(signal_type)} ({len(indices)})', method='restyle',
                                args=['visible', visible]))
        figure['layout']['updatemenus'] = [{
            'type': 'buttons',
            'direction': 'left',
            'buttons': buttons,
            'x': 0.0,
            'xanchor': 'left',
            'y': 1.1,
            'yanchor': 'top'
        }]

        name = self._gnss_plot_filename('gnss_cn0', source_id)
        self._add_figure(name=name, figure=figure, title=f'{label} GNSS C/N0 vs Time', custom_hover=True,
                         inject_js=self._custom_tooltip_js(precision=2))

    def plot_gnss_azimuth_elevation(self):
        """!
        @brief Plot GNSS azimuth/elevation angles.
        """
        for source_id in self._get_gnss_antenna_source_ids():
            self._plot_gnss_azimuth_elevation_for_source(source_id)

    def _plot_gnss_azimuth_elevation_for_source(self, source_id: int):
        label = self._gnss_antenna_label(source_id)

        # Read the GNSS signal data.
        data = self._get_gnss_signals_data(source_id)
        if len(data.messages) == 0:
            self.logger.info(f'No GNSS signal data available for source ID {source_id}. Skipping azimuth/elevation '
                             'time series plot.')
            return

        # Set up the figure.
        figure = make_subplots(
            rows=2, cols=1,  print_grid=False, shared_xaxes=True,
            subplot_titles=["Azimuth Angle",
                            "Elevation Angle"])
        figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'])
        axis_layout = self._x_axis_layout()
        figure['layout']['xaxis1'].update(showticklabels=True, **axis_layout)
        figure['layout']['xaxis2'].update(showticklabels=True, **axis_layout)
        figure['layout']['yaxis1'].update(title="Degrees")
        figure['layout']['yaxis2'].update(title="Degrees")

        # Assign colors by PRN.
        sv_hashes = np.unique(data.sv_data['sv_hash'])
        prns = np.unique([get_prn(h) for h in sv_hashes])
        color_by_prn = self._assign_colors(prns)

        # Plot each satellite.
        svs_by_system = defaultdict(set)
        indices_by_system = defaultdict(list)
        for sv_hash in sv_hashes:
            sv_id = SatelliteID(sv_hash=sv_hash)
            name = sv_id.to_string(short=False)
            system = sv_id.get_satellite_type()
            svs_by_system[system].add(sv_hash)

            idx = data.sv_data['sv_hash'] == sv_hash
            p1_time = data.sv_data['p1_time'][idx]
            gps_time = data.sv_data['gps_time'][idx]
            az_deg = data.sv_data['azimuth_deg'][idx]
            el_deg = data.sv_data['elevation_deg'][idx]

            time, _ = self._resolve_x_axis(p1_time=p1_time, gps_time=gps_time)
            customdata = self._time_hover_customdata(p1_time=p1_time, gps_time=gps_time)

            # Plot the data.
            color = color_by_prn[sv_id.get_prn()]
            figure.add_trace(go.Scattergl(x=time, y=az_deg, customdata=customdata,
                                          name=name,
                                          mode='markers',
                                          marker={'color': color, 'symbol': 'circle', 'size': 8},
                                          showlegend=True,
                                          legendgroup=name),
                                1, 1)
            indices_by_system[system].append(len(figure.data) - 1)
            figure.add_trace(go.Scattergl(x=time, y=el_deg, customdata=customdata,
                                          name=name,
                                          mode='markers',
                                          marker={'color': color, 'symbol': 'circle', 'size': 8},
                                          showlegend=False,
                                          legendgroup=name),
                                2, 1)
            indices_by_system[system].append(len(figure.data) - 1)

        # Add signal type selection buttons.
        num_traces = len(figure.data)
        buttons = [dict(label=f'All ({len(sv_hashes)})', method='restyle', args=['visible', [True] * num_traces])]
        for system, indices in sorted(indices_by_system.items()):
            if len(indices) == 0:
                continue
            visible = np.full((num_traces,), False)
            visible[indices] = True
            buttons.append(dict(label=f'{str(system)} ({len(svs_by_system[system])})', method='restyle',
                                args=['visible', visible]))
        figure['layout']['updatemenus'] = [{
            'type': 'buttons',
            'direction': 'left',
            'buttons': buttons,
            'x': 0.0,
            'xanchor': 'left',
            'y': 1.1,
            'yanchor': 'top'
        }]

        name = self._gnss_plot_filename('gnss_azimuth_elevation', source_id)
        self._add_figure(name=name, figure=figure, title=f'{label} GNSS Azimuth & Elevation vs Time',
                         custom_hover=True, inject_js=self._custom_tooltip_js())

    def plot_gnss_signal_status(self):
        for source_id in self._get_gnss_antenna_source_ids():
            self._plot_gnss_signal_status_for_source(source_id)

    def _plot_gnss_signal_status_for_source(self, source_id: int):
        label = self._gnss_antenna_label(source_id)
        filename = self._gnss_plot_filename('gnss_signal_status', source_id)
        figure_title = f'{label} GNSS Signal Status'

        # Read the GNSS signal data.
        data = self._get_gnss_signals_data(source_id)
        if len(data.messages) == 0:
            self.logger.info(f'No GNSS signal data available for source ID {source_id}. Skipping signal status '
                             'plot.')
            return
        have_gnss_signals_message = not data.using_legacy_satellite_message

        # Count the number of satellites/signals used in each epoch.
        all_p1_time = data.p1_time

        def _count_selected(selected_p1_times, return_nonzero_time=False):
            selected_p1_time, p1_time_idx, count_per_time = np.unique(selected_p1_times, return_index=True,
                                                                      return_counts=True)
            count = np.full_like(all_p1_time, 0, dtype=int)
            count[np.isin(all_p1_time, selected_p1_time)] = count_per_time
            if return_nonzero_time:
                return count, selected_p1_time, p1_time_idx
            else:
                return count

        num_svs = _count_selected(data.sv_data["p1_time"])
        num_signals = _count_selected(data.signal_data["p1_time"])

        is_used_mask = (GNSSSignalInfo.STATUS_FLAG_USED_PR | GNSSSignalInfo.STATUS_FLAG_USED_DOPPLER |
                        GNSSSignalInfo.STATUS_FLAG_USED_CARRIER)
        idx = (np.bitwise_and(data.signal_data['status_flags'], is_used_mask) != 0)
        num_used_signals, used_p1_time, used_p1_time_idx = _count_selected(data.signal_data['p1_time'][idx],
                                                                           return_nonzero_time=True)

        used_signal_hashes = data.signal_data['signal_hash'][idx]
        used_sv_hashes = np.array([get_satellite_hash(h) for h in used_signal_hashes])
        used_sv_hashes_per_epoch = np.split(used_sv_hashes, used_p1_time_idx[1:])
        num_used_svs_only = np.array([len(np.unique(svs)) for svs in used_sv_hashes_per_epoch])
        num_used_svs = np.full_like(all_p1_time, 0, dtype=int)
        num_used_svs[np.isin(data.p1_time, used_p1_time)] = num_used_svs_only

        idx = (np.bitwise_and(data.signal_data['status_flags'],
                              GNSSSignalInfo.STATUS_FLAG_CARRIER_AMBIGUITY_RESOLVED) != 0)
        num_fixed_signals = _count_selected(data.signal_data["p1_time"][idx])

        # Setup the figure.
        colors = {'unused': 'black', 'is_pivot': 'purple',
                  'pr': 'red', 'pr_diff': 'deepskyblue',
                  'float': 'green', 'fixed': 'orange'}

        if have_gnss_signals_message:
            title = '''\
Signal Status<br>
Black=Unused, Red=Pseudorange, Light Blue=Differential Pseudorange<br>
Green=Float, Orange=Integer (Fixed)'''
        else:
            # The legacy GNSSSatelliteMessage contains data per satellite, not per signal, and only includes in-use
            # status. It does not elaborate on _how_ the signal was used for navigation.
            title = '''\
Satellite Status<br>
Black=Unused, Red=Used'''

        figure = make_subplots(
            rows=5, cols=1,  print_grid=False, shared_xaxes=True,
            subplot_titles=[title,
                            None, None, None,
                            'Satellite/Signal Count'],
            specs=[[{'rowspan': 4}],
                   [None],
                   [None],
                   [None],
                   [{}]])
        figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'])
        axis_layout = self._x_axis_layout()
        figure['layout']['xaxis1'].update(**axis_layout)
        figure['layout']['xaxis2'].update(**axis_layout)
        figure['layout']['yaxis1'].update(title='Signal' if have_gnss_signals_message else 'Satellite')
        figure['layout']['yaxis2'].update(title=f"# SVs/Signals", rangemode='tozero')

        # Plot the signal counts.
        time, _ = self._resolve_x_axis(p1_time=data.p1_time, gps_time=data.gps_time)
        customdata = self._time_hover_customdata(p1_time=data.p1_time, gps_time=data.gps_time)
        figure.add_trace(go.Scattergl(x=time, y=num_svs, customdata=customdata, name=f'# SVs',
                                      mode='lines', line={'color': 'black', 'dash': 'dash'}),
                         5, 1)
        if have_gnss_signals_message:
            figure.add_trace(go.Scattergl(x=time, y=num_signals, customdata=customdata, name=f'# Signals',
                                          mode='lines', line={'color': 'gray', 'dash': 'dash'}),
                             5, 1)

        figure.add_trace(go.Scattergl(x=time, y=num_used_svs, customdata=customdata, name=f'# Used SVs',
                                      mode='lines', line={'color': 'green'}),
                         5, 1)
        if have_gnss_signals_message:
            figure.add_trace(go.Scattergl(x=time, y=num_used_signals, customdata=customdata, name=f'# Used Signals',
                                          mode='lines', line={'color': 'red'}),
                             5, 1)
            figure.add_trace(go.Scattergl(x=time, y=num_fixed_signals, customdata=customdata, name=f'# Fixed Signals',
                                          mode='lines', line={'color': 'orange'}),
                             5, 1)

        num_count_traces = len(figure.data)

        # In practice, the signal status plot can be _VERY_ slow to generate for really long logs (multiple hours)
        # because plotly doesn't handle figures with lots of traces very efficiently. If we think the log is very
        # long, we'll skip this plot.
        #
        # The legacy GNSSSatelliteMessage status plot doesn't seem to suffer nearly as much since A) it has fewer
        # elements (# SVs vs # signals), and B) it only supports at most 2 traces per element since it doesn't
        # convey usage type.
        if self.truncate_data:
            _logger.warning('Skipping signal status plot for very long log. Rerun with --truncate=false to '
                            'generate this plot.')
            self._add_figure(name=filename, title=f'{figure_title} (Skipped - Long Log Detected)')
            return

        if have_gnss_signals_message:
            conditions = [
                # Signal used for standalone pseudorange
                {
                    'cond': lambda status_flags, have_corrections: np.logical_and(
                        np.bitwise_and(status_flags, GNSSSignalInfo.STATUS_FLAG_USED_PR) != 0,
                        ~have_corrections),
                    'marker': {'color': colors['pr'], 'symbol': 'circle', 'size': 8}
                },
                # Signal used for differential pseudorange (but not carrier phase)
                {
                    'cond': lambda status_flags, have_corrections: np.logical_and(
                        np.bitwise_and(status_flags, range_used_mask) == GNSSSignalInfo.STATUS_FLAG_USED_PR,
                        have_corrections),
                    'marker': {'color': colors['pr_diff'], 'symbol': 'circle', 'size': 8}
                },
                # Signal used for float carrier phase
                {
                    'cond': lambda status_flags, have_corrections: np.logical_and(
                        np.bitwise_and(status_flags, cp_used_mask) == GNSSSignalInfo.STATUS_FLAG_USED_CARRIER,
                        have_corrections),
                    'marker': {'color': colors['float'], 'symbol': 'circle', 'size': 8}
                },
                # Signal used for fixed carrier phase
                {
                    'cond': lambda status_flags, have_corrections: np.logical_and(
                        np.bitwise_and(status_flags, cp_used_mask) == cp_used_mask,
                        have_corrections),
                    'marker': {'color': colors['fixed'], 'symbol': 'circle', 'size': 8}
                },
                # Signal not used
                {
                    'cond': lambda status_flags, _: np.bitwise_and(status_flags, is_used_mask) == 0,
                    'marker': {'color': colors['unused'], 'symbol': 'x', 'size': 8}
                },
            ]

            # At the moment, the signals message does not have a flag to indicate if RTK corrections are available. For
            # now, we will say that they are available if _any_ signal in the epoch used carrier phase. If we use PR
            # corrections but do not use carrier phase on any signals, it will display as uncorrected.
            used_cp = np.bitwise_and(data.signal_data['status_flags'], GNSSSignalInfo.STATUS_FLAG_USED_CARRIER) != 0
            _, idx, rev_idx = np.unique(data.signal_data['p1_time'], return_index=True, return_inverse=True)
            used_cp_per_epoch = np.split(used_cp, idx[1:])
            have_corrections_per_epoch = np.array([any(used) for used in used_cp_per_epoch], dtype=bool)
            have_corrections = have_corrections_per_epoch[rev_idx]

            range_used_mask = (GNSSSignalInfo.STATUS_FLAG_USED_PR | GNSSSignalInfo.STATUS_FLAG_USED_CARRIER)
            cp_used_mask = (GNSSSignalInfo.STATUS_FLAG_USED_CARRIER |
                            GNSSSignalInfo.STATUS_FLAG_CARRIER_AMBIGUITY_RESOLVED)
        else:
            conditions = [
                # Signal used
                {
                    'cond': lambda status_flags, _: np.bitwise_and(status_flags, is_used_mask) != 0,
                    'marker': {'color': colors['pr'], 'symbol': 'circle', 'size': 8}
                },
                # Signal not used
                {
                    'cond': lambda status_flags, _: np.bitwise_and(status_flags, is_used_mask) == 0,
                    'marker': {'color': colors['unused'], 'symbol': 'x', 'size': 8}
                },
            ]
            have_corrections = None

        # Plot each signal. Plot in reverse order so G01 is at the top of the Y axis.
        signal_hashes = np.unique(data.signal_data['signal_hash'])
        indices_by_signal_type = defaultdict(list)
        signals_by_type = defaultdict(list)
        tick_text = []
        for signal_hash in signal_hashes[::-1]:
            signal = SignalID(signal_hash=signal_hash)
            name = signal.to_string(short=False)
            signals_by_type[signal.signal_type].append(signal)

            # Extract data for this signal.
            idx = data.signal_data['signal_hash'] == signal_hash
            p1_time = data.signal_data['p1_time'][idx]
            gps_time = data.signal_data['gps_time'][idx]
            cn0_dbhz = data.signal_data['cn0_dbhz'][idx]
            status_flags = data.signal_data['status_flags'][idx]
            signal_has_corrections = None if have_corrections is None else have_corrections[idx]
            time, _ = self._resolve_x_axis(p1_time=p1_time, gps_time=gps_time)
            # The time value NOT already reflected by the X axis, one row, to include in this signal's customdata.
            other_time = self._time_hover_customdata(p1_time=p1_time, gps_time=gps_time)[0]

            # Find the satellite elevation for the times this signal was present.
            sv_idx = data.sv_data['sv_hash'] == int(signal.get_satellite_id())
            time_idx = np.isin(data.sv_data['p1_time'][sv_idx], p1_time)
            elev_deg = data.sv_data['elevation_deg'][sv_idx][time_idx]

            shown = False
            y_offset = len(tick_text)
            for cond in conditions:
                idx = cond['cond'](status_flags, signal_has_corrections)
                if np.any(idx):
                    figure.add_trace(go.Scattergl(x=time[idx], y=[y_offset] * np.sum(idx),
                                                  customdata=np.vstack((other_time[idx],
                                                                        status_flags[idx],
                                                                        cn0_dbhz[idx],
                                                                        elev_deg[idx])),
                                                  name=name,
                                                  showlegend=False, legendgroup=int(signal_hash),
                                                  mode='markers', marker=cond['marker']),
                                     1, 1)
                    indices_by_signal_type[signal.signal_type].append(len(figure.data) - 1)
                    shown = True

            if shown:
                tick_text.append(signal.to_string(short=True))

        figure['layout']['yaxis1'].update(tickmode='array', tickvals=np.arange(0, len(tick_text)),
                                          ticktext=tick_text, automargin=True)

        # Add signal type selection buttons.
        num_traces = len(figure.data)
        num_signals = np.max(num_signals) if len(num_signals) > 0 else 0
        buttons = [dict(label=f'All ({num_signals})', method='restyle', args=['visible', [True] * num_traces])]
        for signal_type, indices in sorted(indices_by_signal_type.items()):
            if len(indices) == 0:
                continue
            visible = np.full((num_traces,), False)
            visible[:num_count_traces] = True
            visible[indices] = True
            buttons.append(dict(label=f'{pretty_print_gnss_enum(signal_type)} ({len(signals_by_type[signal_type])})',
                                method='restyle', args=['visible', visible]))
        figure['layout']['updatemenus'] = [{
            'type': 'buttons',
            'direction': 'left',
            'buttons': buttons,
            'x': 0.0,
            'xanchor': 'left',
            'y': 1.1,
            'yanchor': 'top'
        }]

        hover_js = f"""\
function SetSignalStatusHover(point) {{
  let other_time = GetCustomData(point, 0);
  let status_flags = GetCustomData(point, 1);
  let cn0_dbhz = GetCustomData(point, 2);
  let elev_deg = GetCustomData(point, 3);

  let tracking = [];
  if (status_flags & {GNSSSignalInfo.STATUS_FLAG_VALID_PR}) {{
    tracking.push("PR");
  }}
  if (status_flags & {GNSSSignalInfo.STATUS_FLAG_CARRIER_LOCKED}) {{
    tracking.push("CP");
  }}
  if (status_flags & {GNSSSignalInfo.STATUS_FLAG_VALID_DOPPLER}) {{
    tracking.push("Doppler");
  }}

  let used = [];
  if (status_flags & {GNSSSignalInfo.STATUS_FLAG_USED_PR}) {{
    used.push("PR");
  }}
  if (status_flags & {GNSSSignalInfo.STATUS_FLAG_USED_CARRIER}) {{
    if (status_flags & {GNSSSignalInfo.STATUS_FLAG_CARRIER_AMBIGUITY_RESOLVED}) {{
      used.push("CP (fixed)");
    }}
    else {{
      used.push("CP");
    }}
  }}
  if (status_flags & {GNSSSignalInfo.STATUS_FLAG_USED_DOPPLER}) {{
    used.push("Doppler");
  }}

  let features = [];
  if (status_flags & {GNSSSignalInfo.STATUS_FLAG_HAS_EPHEM}) {{
    features.push("Ephemeris");
  }}
  if (status_flags & {GNSSSignalInfo.STATUS_FLAG_HAS_SBAS}) {{
    features.push("SBAS");
  }}
  if (status_flags & {GNSSSignalInfo.STATUS_FLAG_HAS_RTK}) {{
    features.push("RTK");
  }}

  let new_text = BuildTimeHoverText(point.x, other_time);
  new_text += "<br>C/N0: " + cn0_dbhz.toFixed(2) + " dB-Hz";
  new_text += "<br>Elevation: " + elev_deg.toFixed(1) + " deg";
  new_text += "<br>Status mask: 0x" + status_flags.toString(16);
  new_text += "<br>Available: " + tracking.join(", ");
  new_text += "<br>Used: " + used.join(", ");
  new_text += "<br>Features: " + features.join(", ");
  ShowCustomTooltip(point, GetCustomTooltipHTML(point.data.name, undefined, new_text));
}}

figure.on('plotly_hover', function(data) {{
  let point = data.points[0];
  if (point.curveNumber >= {num_count_traces}) {{
    SetSignalStatusHover(point);
  }}
  else {{
    let time_text = BuildTimeHoverText(point.x, GetCustomData(point, 0));
    let value_text = BuildAxisValueHoverText(point);
    ShowCustomTooltip(point, GetCustomTooltipHTML(point.data.name, value_text, time_text));
  }}
}});
figure.on('plotly_unhover', function(data) {{
  HideCustomTooltip();
}});
""" + self._GPS_TICK_REFORMAT_JS

        self._add_figure(name=filename, figure=figure, title=figure_title, custom_hover=True, inject_js=hover_js)

    def _get_pose_source_ids(self) -> List[int]:
        """!
        @brief Get the source IDs, restricted to known pose-producing identifiers, present in this log.

        `self.source_ids` includes every source ID seen across all message types, so it isn't specific to pose
        sources. Restrict it here to the reserved pose range so we don't attempt (and log about) a PoseMessage
        read for unrelated source IDs, e.g. GNSS antennas or IMUs.
        """
        if self._pose_source_ids is None:
            # 0-99 is reserved for pose solutions.
            self._pose_source_ids = sorted(sid for sid in self.source_ids if 0 <= sid <= 99)
        return self._pose_source_ids

    def _get_gnss_antenna_source_ids(self) -> List[int]:
        """!
        @brief Get the source IDs, restricted to known GNSS antenna identifiers, present in this log.

        `self.source_ids` includes every source ID seen across all message types (and may be further restricted by
        the user's --source-id argument), so it isn't specific to GNSS antennas. Restrict it here to the known
        antenna identifiers so we don't attempt (and skip) a GNSS signal read for unrelated source IDs, e.g. ones
        only used for IMU or wheel speed data.
        """
        if self._gnss_antenna_source_ids is None:
            # 0/1 are the legacy primary/secondary antenna identifiers, predating the SourceIdentifier reserved
            # ranges. 300-399 is reserved for GNSS receivers/antennae.
            self._gnss_antenna_source_ids = sorted(
                sid for sid in self.source_ids if sid in (0, 1) or 300 <= sid <= 399)
        return self._gnss_antenna_source_ids

    def _gnss_antenna_label(self, source_id: int) -> str:
        if source_id in (0, SourceIdentifier.PRIMARY_GNSS_ANTENNA):
            return 'Primary'
        elif source_id in (1, SourceIdentifier.SECONDARY_GNSS_ANTENNA):
            return 'Secondary'
        else:
            return f'Source {source_id}'

    def _gnss_plot_filename(self, base_name: str, source_id: int) -> str:
        # Keep the primary antenna's filename unsuffixed for backward compatibility with existing links/tooling.
        if source_id in (0, SourceIdentifier.PRIMARY_GNSS_ANTENNA):
            return base_name
        else:
            return f'{base_name}_{self._gnss_antenna_label(source_id).lower().replace(" ", "_")}'

    def _get_gnss_signals_data(self, source_id: int):
        # If we already have data cached, return it.
        if self._gnss_signals_data.get(source_id) is not None:
            return self._gnss_signals_data[source_id]

        # See if we have GNSSSignalsMessages. If so, prefer those.
        params = copy.deepcopy(self.params)
        params['return_numpy'] = False
        params['source_ids'] = {source_id}

        available_source_ids = self.reader.get_available_source_ids()

        # DataLoader/MixedLogReader treat an empty (but non-None) source_ids filter as "no filter" rather than
        # "match nothing", so if this source ID isn't actually present in the log, skip the read entirely instead
        # of getting back every source ID's data.
        if source_id not in available_source_ids:
            data = MessageData(message_type=GNSSSignalsMessage.MESSAGE_TYPE, params=params)
        else:
            result = self.reader.read(message_types=[GNSSSignalsMessage], **params)
            data = result[GNSSSignalsMessage.MESSAGE_TYPE]

        # We store the result now, even if there were no GNSSSignalsMessage messages. That way if we also don't have any
        # GNSSSatelliteMessage messages below, we'll have _something_ to return and we won't try to reload from disk on
        # each call to this function.
        self._gnss_signals_data[source_id] = data
        data.using_legacy_satellite_message = False

        # If we don't have any GNSSSignalsMessages, see if we have the legacy GNSSSatelliteMessage and fall back to
        # that. Current firmware can still emit the legacy message, and does so per-antenna just like
        # GNSSSignalsMessage, so apply the same source ID filtering here.
        if len(data.messages) == 0:
            # The legacy GNSSSatelliteMessage contains data per satellite, not per signal. The plotted C/N0 values will
            # reflect the L1 signal, unless L1 is not being tracked.
            if source_id not in available_source_ids:
                data = MessageData(message_type=GNSSSatelliteMessage.MESSAGE_TYPE, params=params)
            else:
                result = self.reader.read(message_types=[GNSSSatelliteMessage], **params)
                data = result[GNSSSatelliteMessage.MESSAGE_TYPE]

            # Convert to GNSSSignalsMessages. Some of the fields, like signal type and tracking/usage status, will be
            # approximated and may not be plotted.
            #
            # Note that we leave data.message_type as GNSSSatelliteMessage so the plotting functions can determine what
            # information to display. However, we need to change data.message_class so MessageData calls the correct
            # to_numpy() function.
            if len(data.messages) > 0:
                self.logger.warning('Using legacy GNSSSatelliteMessage to approximate per-signal information.')
                data.messages = [m.to_gnss_signals_message() for m in data.messages]
                data.message_type = GNSSSignalsMessage.MESSAGE_TYPE
                data.message_class = GNSSSignalsMessage
                self._gnss_signals_data[source_id] = data
                data.using_legacy_satellite_message = True

        self._gnss_signals_data[source_id].to_numpy()

        return self._gnss_signals_data[source_id]

    def clear_gnss_signal_data_cache(self):
        """!
        @brief Clear cached GNSSSignalsMessage data to free memory when finished plotting.
        """
        self._gnss_signals_data = {}

    def plot_dop(self):
        """!
        @brief Plot dilution of precision (DOP).

        This includes geometric, position, horizontal, and vertical DOP.
        """
        result = self.reader.read(message_types=[GNSSInfoMessage], **self.params)
        data = result[GNSSInfoMessage.MESSAGE_TYPE]

        if len(data.p1_time) == 0:
            self.logger.info('No GNSS info data available. Skipping dilution of precision plot.')
            return

        time, axis_layout = self._resolve_x_axis(p1_time=data.p1_time, gps_time=data.gps_time)
        customdata = self._time_hover_customdata(p1_time=data.p1_time, gps_time=data.gps_time)

        # # Setup the figure.
        figure = make_subplots(
            rows=1, cols=1,  print_grid=False, shared_xaxes=True,
            subplot_titles=['Dilution of Precision (DOP)'])

        figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'])
        figure['layout']['xaxis'].update(**axis_layout)

        dops = [('GDOP', data.gdop), ('PDOP', data.pdop), ('HDOP', data.hdop), ('VDOP', data.vdop)]

        # Assign colors to each DOP type.
        color_by_dop = self._assign_colors([entry[0] for entry in dops])

        # Plot each DOP type.
        for entry in dops:
            name, dop = entry

            figure.add_trace(go.Scattergl(x=time, y=dop, customdata=customdata, name=name,
                                          mode='markers', marker={'color': color_by_dop[name]}),
                             1, 1)

        self._add_figure(name='gnss_dop', figure=figure, title='GNSS Dilution of Precision (DOP) vs. Time',
                         custom_hover=True, inject_js=self._custom_tooltip_js(value_label='DOP'))

    def plot_gnss_corrections_status(self):
        """!
        @brief Plot GNSS corrections status (baseline distance, age, etc.).
        """
        result = self.reader.read(message_types=[GNSSInfoMessage], **self.params)
        data = result[GNSSInfoMessage.MESSAGE_TYPE]

        if len(data.p1_time) == 0:
            self.logger.info('No GNSS info data available. Skipping corrections status plot.')
            return

        # Setup the figure.
        figure = make_subplots(
            rows=4, cols=1,  print_grid=False, shared_xaxes=True,
            subplot_titles=['Distance To Station', 'Corrections Age'],
            specs=[[{'rowspan': 3}],
                   [None],
                   [None],
                   [{}]])
        figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'])
        axis_layout = self._x_axis_layout()
        for i in range(2):
            figure['layout']['xaxis%d' % (i + 1)].update(showticklabels=True, matches='x', **axis_layout)
        figure['layout']['yaxis1'].update(title="Baseline Distance (km)")
        figure['layout']['yaxis2'].update(title="Age (sec)")

        # Find all base stations present in the data and assign a color to each.
        station_ids = np.unique([s for s in data.reference_station_id
                                 if s != GNSSInfoMessage.INVALID_REFERENCE_STATION])
        if len(station_ids) == 0:
            # This may happen if the log has no corrections, or if the GNSSInfoMessages in the log use version 0.
            # Baseline distance and age were added in version 1.
            self.logger.info('GNSS corrections status details not available. Skipping plot.')
            return

        colors = self._assign_colors(station_ids)

        # Now plot data for each base station.
        for station_id in station_ids:
            idx = data.reference_station_id == station_id
            p1_time = data.p1_time[idx]
            gps_time = data.gps_time[idx]
            time, _ = self._resolve_x_axis(p1_time=p1_time, gps_time=gps_time)
            customdata = self._time_hover_customdata(p1_time=p1_time, gps_time=gps_time)
            name = f'Station {station_id}'
            color = colors[station_id]
            figure.add_trace(go.Scattergl(x=time, y=data.baseline_distance_m[idx] * 1e-3, customdata=customdata,
                                          name=name, legendgroup=int(station_id), showlegend=True,
                                          mode='markers', marker={'color': color}),
                             1, 1)
            figure.add_trace(go.Scattergl(x=time, y=data.corrections_age_sec[idx], customdata=customdata,
                                          name=name, legendgroup=int(station_id), showlegend=False,
                                          mode='markers', marker={'color': color}),
                             4, 1)

        self._add_figure(name="gnss_corrections_status", figure=figure, title="GNSS Corrections Status",
                         custom_hover=True, inject_js=self._custom_tooltip_js())

    def plot_wheel_data(self):
        """!
        @brief Plot wheel tick/speed data.
        """
        if self.output_dir is None:
            return

        self._plot_wheel_ticks_or_speeds(source='wheel', type='speed')
        self._plot_wheel_ticks_or_speeds(source='wheel', type='tick')
        self._plot_wheel_ticks_or_speeds(source='vehicle', type='speed')
        self._plot_wheel_ticks_or_speeds(source='vehicle', type='tick')

    def _plot_wheel_ticks_or_speeds(self, source, type):
        """!
        @brief Plot wheel speed or tick data.
        """
        # Read the data. Try to determine which type of wheel output is present in the log (if any):
        # 1. A call to this function may be plotting either speed or tick count data, depending on `type`
        # 2. A call to this function may be plotting data from a single sensor (e.g., VehicleSpeedOutput) or for
        #    multiple differential wheel sensors (e.g., WheelSpeedOutput), depending on `source`
        # 3. This function may plot both corrected (e.g., WheelSpeedOutput) and uncorrected (e.g., RawWheelSpeedOutput)
        #    measurements if both are present in the log
        # 4. (Internal use only) If input messages _to_ the device are present and the corresponding uncorrected output
        #    messages are not, display the input messages
        # 5. For backwards compatibility, this function may read older, deprecated measurements if present in the log
        if type == 'tick':
            filename = '%s_ticks' % source
            figure_title = 'Measurements: %s Encoder Ticks' % source.title()

            if source == 'wheel':
                raw_measurement_type = self._auto_detect_message_type([RawWheelTickOutput, WheelTickInput])
            else:
                raw_measurement_type = self._auto_detect_message_type([RawVehicleTickOutput, VehicleTickInput])

            # Wheel ticks are raw (uncorrected) by definition. There are no corrected wheel ticks.
            measurement_type = None
        else:
            filename = '%s_speed' % source
            figure_title = 'Measurements: %s Speed' % source.title()

            if source == 'wheel':
                measurement_type = self._auto_detect_message_type([WheelSpeedOutput, DeprecatedWheelSpeedMeasurement])
            else:
                measurement_type = self._auto_detect_message_type([VehicleSpeedOutput,
                                                                   DeprecatedVehicleSpeedMeasurement])

            if source == 'wheel':
                raw_measurement_type = self._auto_detect_message_type([RawWheelSpeedOutput, WheelSpeedInput])
            else:
                raw_measurement_type = self._auto_detect_message_type([RawVehicleSpeedOutput, VehicleSpeedInput])

        if measurement_type is None and raw_measurement_type is None:
            self.logger.info('No %s %s data available. Skipping plot.' % (source, type))
            return

        any_measurement_type = measurement_type if measurement_type is not None else raw_measurement_type

        # If the measurement data is very high rate, this plot may be very slow to generate for a multi-hour log.
        if self.long_log_detected and self.truncate_data:
            params = copy.deepcopy(self.params)
            params['max_messages'] = 2
            result = self.reader.read(message_types=any_measurement_type, remove_nan_times=False, **params)
            data = result[any_measurement_type.MESSAGE_TYPE]
            if len(data.measurement_time) == 2:
                dt_sec = data.measurement_time[1] - data.measurement_time[0]
                data_rate_hz = round(1.0 / dt_sec)
                if data_rate_hz > self.HIGH_MEASUREMENT_RATE_HZ:
                    _logger.warning('High rate data detected (%d Hz). Skipping wheel %s plot for very long log. Rerun '
                                    'with --truncate=false to generate this plot.' % (data_rate_hz, type))
                    self._add_figure(name=filename, title=f'{figure_title} (Skipped - Long Log Detected)')
                    return

        # Read the data.
        result = self.reader.read(message_types=[measurement_type, raw_measurement_type],
                                  remove_nan_times=False, **self.params)

        def _extract_data(measurement_type):
            if measurement_type is not None:
                data = result[measurement_type.MESSAGE_TYPE]
                data_signed = False
                if len(data.p1_time) == 0:
                    data = None
                elif type == 'speed':
                    data_signed = np.any(data.is_signed)
            else:
                data = None
                data_signed = False
            return data, data_signed

        data, data_signed = _extract_data(measurement_type)
        raw_data, raw_data_signed = _extract_data(raw_measurement_type)
        if data is None and raw_data is None:
            self.logger.info('No %s %s data available. Skipping plot.' % (source, type))
            return

        # Setup the figure.
        if type == 'tick':
            titles = ['%s Tick Count' % source.title(), '%s Tick Rate' % source.title(), 'Gear/Direction']
        else:
            if data_signed or raw_data_signed:
                titles = ['%s Speed (Signed)' % source.title(), 'Gear/Direction']
            else:
                titles = ['%s Speed (Unsigned)' % source.title(), 'Gear/Direction']
        titles.append('Measurement Interval')

        if data is None:
            titles[0] += f'<br>Messages: {raw_measurement_type.__name__}'
        elif raw_data is None:
            titles[0] += f'<br>Messages: {measurement_type.__name__}'
        else:
            titles[0] += f'<br>Messages: {measurement_type.__name__}, {raw_measurement_type.__name__}'

        figure = make_subplots(rows=len(titles), cols=1, print_grid=False, shared_xaxes=True, subplot_titles=titles)

        figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'])
        # Note: X-axis title set below after determining time source.

        if type == 'tick':
            figure['layout']['yaxis1'].update(title="Tick Count")
            figure['layout']['yaxis2'].update(title="Tick Rate (ticks/s)")
        else:
            figure['layout']['yaxis1'].update(title="Speed (m/s)")

        gear_y_axis = len(titles) - 1
        interval_y_axis = len(titles)
        figure['layout']['yaxis%d' % gear_y_axis].update(title="Gear/Direction",
                                                         ticktext=['%s (%d)' % (e.name, e.value) for e in GearType],
                                                         tickvals=[e.value for e in GearType])
        figure['layout']['yaxis%d' % interval_y_axis].update(title="Interval (sec)")

        # Check if the data has P1 time available. If not, we'll plot in the original source time.
        #
        # All output messages from the device should contain P1 time. We should only ever use a non-P1 time source when
        # plotting logged input messages (uncommon).
        def _get_time_source(meas_type, data):
            if meas_type is None or data is None:
                return None
            # If this data does not have P1 time, use its incoming native time source (system time of reception, etc.).
            elif np.all(np.isnan(data.p1_time)):
                # Check that the time source never changed. Warn if it did.
                if np.any(np.diff(data.measurement_time_source) != 0):
                    self.logger.warning('Detected multiple time source types in %s data.' % meas_type.__name__)

                result = SystemTimeSource(data.measurement_time_source[0])
                self.logger.warning('%s data does not have P1 time available. Plotting in %s time.' %
                                    (meas_type.__name__, self._time_source_to_display_name(result)))
            # P1 time available - use that.
            else:
                result = SystemTimeSource.P1_TIME
            return result

        same_time_source = True
        if raw_measurement_type is None:
            corrected_time_source = _get_time_source(measurement_type, data)
            raw_time_source = None
            common_time_source = corrected_time_source
        elif measurement_type is None:
            corrected_time_source = None
            raw_time_source = _get_time_source(raw_measurement_type, raw_data)
            common_time_source = raw_time_source
        else:
            corrected_time_source = _get_time_source(measurement_type, data)
            raw_time_source = _get_time_source(raw_measurement_type, raw_data)
            if corrected_time_source == raw_time_source:
                common_time_source = corrected_time_source
            else:
                common_time_source = corrected_time_source
                same_time_source = False
                self.logger.warning('Both raw and corrected %s data present, but timestamped with different '
                                    'sources. Plotted data may not align in time.' % source)

        # Time-type-based (relative/P1/GPS/UTC) axis display is only meaningful when all of the data being plotted is
        # natively in P1 time -- there's no P1/GPS correspondence to fall back on for other time sources (system time
        # of reception, etc.), which are only ever used for input messages.
        use_time_type = same_time_source and common_time_source == SystemTimeSource.P1_TIME

        if same_time_source:
            time_name = self._time_source_to_display_name(common_time_source)
            figure['layout']['annotations'][0]['text'] += '<br>Time Source: %s' % time_name

            axis_layout = self._x_axis_layout() if use_time_type else {'title': f'{time_name} Time (sec)'}
            for i in range(len(titles)):
                figure['layout']['xaxis%d' % (i + 1)].update(showticklabels=True, **axis_layout)
        else:
            corrected_time_name = self._time_source_to_display_name(corrected_time_source)
            raw_time_name = self._time_source_to_display_name(raw_time_source)
            figure['layout']['annotations'][0]['text'] += '<br>Time Source: %s (Raw), %s (Corrected)' % \
                                                          (raw_time_name, corrected_time_name)

            time_label = f'{corrected_time_name}/{raw_time_name} Time (sec)'
            for i in range(len(titles)):
                figure['layout']['xaxis%d' % (i + 1)].update(title=time_label, showticklabels=True)

        p1_time_present = (corrected_time_source == SystemTimeSource.P1_TIME or
                           raw_time_source == SystemTimeSource.P1_TIME)

        # If plotting speed data, try to plot the navigation engine's speed estimate for reference.
        #
        # Note: Pose data is not read when plotting ticks (ticks do not plot in meters/second). If the wheel data is not
        # in P1 time, we cannot compare against the pose data, which is.
        if type == 'speed' and p1_time_present:
            nav_engine_p1_time = None
            nav_engine_speed_mps = None

            # If we have pose messages _and_ they contain body velocity, we can use that.
            #
            # Note that we are using this to compare vs wheel speeds, so we're only interested in forward speed here.
            result = self.reader.read(message_types=[PoseMessage], source_ids=self.default_source_id, **self.params)
            pose_data = result[PoseMessage.MESSAGE_TYPE]
            if len(pose_data.p1_time) != 0 and np.any(~np.isnan(pose_data.velocity_body_mps[0, :])):
                nav_engine_p1_time = pose_data.p1_time
                nav_engine_speed_mps = pose_data.velocity_body_mps[0, :]
                if data_signed:
                    nav_engine_speed_name = 'Speed Estimate (Nav Engine)'
                else:
                    nav_engine_speed_mps = np.abs(nav_engine_speed_mps)
                    nav_engine_speed_name = '|Speed Estimate| (Nav Engine)'
            # Otherwise, if we have pose aux messages, read those and use the ENU velocity to estimate speed. Since we
            # don't know attitude, the best we can do is estimate 3D speed and assume it's primarily in the along-track
            # direction. This will also be an absolute value, so may not match the wheel data if it is signed and the
            # vehicle is going backward.
            else:
                result = self.reader.read(message_types=[PoseAuxMessage], source_ids=self.default_source_id,
                                          **self.params)
                pose_aux_data = result[PoseAuxMessage.MESSAGE_TYPE]
                if len(pose_aux_data.p1_time) != 0:
                    self.logger.warning('Body forward velocity not available. Estimating |speed| from ENU velocity. '
                                        'May not match wheel speeds when going backward.')
                    nav_engine_p1_time = pose_aux_data.p1_time
                    nav_engine_speed_mps = np.linalg.norm(pose_aux_data.velocity_enu_mps, axis=0)
                    nav_engine_speed_name = '|3D Speed Estimate| (Nav Engine)'

            if nav_engine_speed_mps is not None:
                if use_time_type:
                    nav_time, _ = self._resolve_x_axis(p1_time=nav_engine_p1_time)
                    nav_kwargs = {'customdata': self._time_hover_customdata(p1_time=nav_engine_p1_time)}
                else:
                    nav_time, _ = self._resolve_x_axis(p1_time=nav_engine_p1_time, ignore_gps=True)
                    nav_kwargs = {}
                figure.add_trace(go.Scattergl(x=nav_time, y=nav_engine_speed_mps, name=nav_engine_speed_name,
                                              mode='lines', line={'color': 'black', 'dash': 'dash'}, **nav_kwargs),
                                 1, 1)

        # Hover text helper functions.
        def _get_time_and_hover_data(abs_time_sec, time_source):
            # If every message being plotted is natively in P1 time, use the current --time-type (relative/P1/GPS/
            # UTC) axis and shared hover text; otherwise fall back to plotting in the message's own raw time source,
            # which has no P1/GPS correspondence to convert from.
            #
            # Returns (time, time_sec, hover_kwargs): `time` is the X axis value to plot (may be a datetime64 array
            # in UTC mode), while `time_sec` is always plain elapsed seconds, suitable for interval/rate calculations.
            if use_time_type:
                time, _ = self._resolve_x_axis(p1_time=abs_time_sec)
                return time, abs_time_sec, {'customdata': self._time_hover_customdata(p1_time=abs_time_sec)}
            else:
                t0 = self._get_t0_for_time_source(time_source)
                time = abs_time_sec - t0
                time_name = self._time_source_to_display_name(time_source)
                text = ["%s Time: %.3f sec" % (time_name, t) for t in abs_time_sec]
                return time, abs_time_sec, {'text': text}

        def _slice_hover_kwargs(hover_kwargs, s):
            # Slice a {'text': ...} or {'customdata': ...} dict (see _get_time_and_hover_data()) down to a subset of
            # points, e.g. for a trace plotted against time[1:] (an interval or rate derived via np.diff()).
            if 'text' in hover_kwargs:
                return {'text': hover_kwargs['text'][s]}
            elif 'customdata' in hover_kwargs:
                return {'customdata': hover_kwargs['customdata'][:, s]}
            else:
                return {}

        # Plot the data.
        def _plot_trace(time, time_sec, data, name, color, text=None, customdata=None, style=None):
            if style is None:
                style = {}
            style.setdefault('mode', 'lines')
            style.setdefault('line', {}).setdefault('color', color)
            kwargs = {'text': text} if text is not None else {'customdata': customdata}

            if type == 'tick':
                figure.add_trace(go.Scattergl(x=time, y=data, name=name, legendgroup=name, **kwargs, **style),
                                 1, 1)

                # Note: Rate is always computed from time_sec (plain seconds), not time -- time may be a datetime64
                # axis (UTC mode), which does not support division.
                dt_sec = np.diff(time_sec)
                ticks_per_sec = np.diff(data) / dt_sec
                rate_kwargs = _slice_hover_kwargs(kwargs, slice(1, None))
                figure.add_trace(go.Scattergl(x=time[1:], y=ticks_per_sec, name=name,
                                              legendgroup=name, showlegend=False,
                                              **rate_kwargs, **style),
                                 2, 1)
            else:
                figure.add_trace(go.Scattergl(x=time, y=data, name=name, legendgroup=name, **kwargs, **style),
                                 1, 1)

        def _plot_wheel_data(data, time_source, is_raw=False, show_gear=False, style=None):
            if data is None:
                return

            if style is None:
                style = {}
            style.setdefault('mode', 'lines')
            if is_raw:
                style.setdefault('line', {}).setdefault('dash', 'dash')

            if type == 'tick':
                var_suffix = 'wheel_ticks'
                name_suffix = ''
            else:
                var_suffix = 'speed_mps'
                name_suffix = ' (Uncorrected)' if is_raw else ' (Corrected)'

            measurement_time = self._get_measurement_time(data, time_source)
            idx = ~np.isnan(measurement_time)
            time, time_sec, hover_kwargs = _get_time_and_hover_data(measurement_time[idx], time_source)

            _plot_trace(time=time, time_sec=time_sec, data=getattr(data, 'front_left_' + var_suffix)[idx],
                        name='Front Left Wheel' + name_suffix, color='red', style=style, **hover_kwargs)
            _plot_trace(time=time, time_sec=time_sec, data=getattr(data, 'front_right_' + var_suffix)[idx],
                        name='Front Right Wheel' + name_suffix, color='green', style=style, **hover_kwargs)
            _plot_trace(time=time, time_sec=time_sec, data=getattr(data, 'rear_left_' + var_suffix)[idx],
                        name='Rear Left Wheel' + name_suffix, color='blue', style=style, **hover_kwargs)
            _plot_trace(time=time, time_sec=time_sec, data=getattr(data, 'rear_right_' + var_suffix)[idx],
                        name='Rear Right Wheel' + name_suffix, color='purple', style=style, **hover_kwargs)

            if show_gear:
                figure.add_trace(go.Scattergl(x=time, y=data.gear[idx], name='Gear (Wheel Data)',
                                              mode='markers', marker={'color': 'red'}, **hover_kwargs),
                                 gear_y_axis, 1)

            name = "Wheel Interval" + name_suffix
            color = 'blue' if is_raw else 'red'
            figure.add_trace(go.Scattergl(x=time[1:], y=np.diff(time_sec), name=name,
                                          mode='markers', marker={'color': color},
                                          **_slice_hover_kwargs(hover_kwargs, slice(1, None))),
                             interval_y_axis, 1)

        def _plot_vehicle_data(data, time_source, is_raw=False, show_gear=False, style=None):
            if data is None:
                return

            if style is None:
                style = {}
            style.setdefault('mode', 'lines')
            if is_raw:
                style.setdefault('line', {}).setdefault('dash', 'dash')

            if type == 'tick':
                var_suffix = 'tick_count'
                name_suffix = ''
            else:
                var_suffix = 'vehicle_speed_mps'
                name_suffix = ' (Uncorrected)' if is_raw else ' (Corrected)'

            measurement_time = self._get_measurement_time(data, time_source)
            idx = ~np.isnan(measurement_time)
            time, time_sec, hover_kwargs = _get_time_and_hover_data(measurement_time[idx], time_source)

            _plot_trace(time=time, time_sec=time_sec, data=getattr(data, var_suffix)[idx],
                        name='Speed Measurement' + name_suffix, color='orange', style=style, **hover_kwargs)

            if show_gear:
                figure.add_trace(go.Scattergl(x=time, y=data.gear[idx], name='Gear (Vehicle Data)',
                                              mode='markers', marker={'color': 'orange'}, **hover_kwargs),
                                 gear_y_axis, 1)

            name = "Vehicle Interval" + name_suffix
            color = 'blue' if is_raw else 'red'
            figure.add_trace(go.Scattergl(x=time[1:], y=np.diff(time_sec), name=name,
                                          mode='markers', marker={'color': color},
                                          **_slice_hover_kwargs(hover_kwargs, slice(1, None))),
                             interval_y_axis, 1)

        # Plot the data. If we have both corrected (e.g., WheelSpeedOutput) and uncorrected (e.g., RawWheelSpeedOutput)
        # messages are present in the log, plot them both for comparison.
        _plot_func = _plot_wheel_data if source == 'wheel' else _plot_vehicle_data
        _plot_func(data, corrected_time_source, is_raw=False, show_gear=True)
        _plot_func(raw_data, raw_time_source, is_raw=True, show_gear=False)

        # Custom hover: like _custom_tooltip_js(), but some points carry a precomputed `text` string (see
        # _get_time_and_hover_data() above) instead of customdata, for measurements not in P1 time (no P1/GPS
        # correspondence to build a full BuildTimeHoverText() from) -- use that verbatim instead when present.
        _WHEEL_HOVER_JS = """\
figure.on('plotly_hover', function(data) {
  let point = data.points[0];
  let time_text;
  if (point.data.customdata) {
    time_text = BuildTimeHoverText(point.x, GetCustomData(point, 0));
  } else if (point.text) {
    time_text = point.text;
  } else {
    time_text = BuildTimeHoverText(point.x);
  }
  let value_text = BuildAxisValueHoverText(point);
  ShowCustomTooltip(point, GetCustomTooltipHTML(point.data.name, value_text, time_text));
});
figure.on('plotly_unhover', function(data) {
  HideCustomTooltip();
});
""" + self._GPS_TICK_REFORMAT_JS

        self._add_figure(name=filename, figure=figure, title=figure_title, custom_hover=True,
                         inject_js=_WHEEL_HOVER_JS)

    def plot_imu(self):
        """!
        @brief Plot the IMU data.
        """
        if self.output_dir is None:
            return

        self._plot_imu_data(message_cls=IMUOutput, filename='imu', figure_title='Measurements: IMU')
        self._plot_imu_data(message_cls=RawIMUOutput, filename='raw_imu',
                            figure_title='Measurements: IMU (Uncorrected)')

    def _plot_imu_data(self, message_cls, filename, figure_title):
        # If the measurement data is very high rate, this plot may be very slow to generate for a multi-hour log.
        if self.truncate_data:
            params = copy.deepcopy(self.params)
            params['max_messages'] = 2
            result = self.reader.read(message_types=[message_cls], **params)
            data = result[message_cls.MESSAGE_TYPE]
            if len(data.p1_time) == 2:
                dt_sec = data.p1_time[1] - data.p1_time[0]
                data_rate_hz = round(1.0 / dt_sec)
                if data_rate_hz > self.HIGH_MEASUREMENT_RATE_HZ:
                    _logger.warning('High rate IMU data detected (%d Hz). Skipping IMU plot for very long log. Rerun '
                                    'with --truncate=false to generate this plot.' % data_rate_hz)
                    self._add_figure(name=filename, title=f'{figure_title} (Skipped - Long Log Detected)')
                    return

        # Read the data.
        result = self.reader.read(message_types=[message_cls], **self.params)
        data = result[message_cls.MESSAGE_TYPE]

        if len(data.p1_time) == 0:
            self.logger.info('No %s data available. Skipping plot.' %
                             ('IMU' if message_cls is IMUOutput else 'raw IMU'))
            return

        time, axis_layout = self._resolve_x_axis(p1_time=data.p1_time)
        customdata = self._time_hover_customdata(p1_time=data.p1_time)

        titles = ['Acceleration', 'Gyro']
        if message_cls == RawIMUOutput:
            titles = [t + ' (Uncorrected)' for t in titles]
        else:
            titles = [t + ' (Corrected)' for t in titles]
        titles.append('Measurement Interval')

        figure = make_subplots(rows=len(titles), cols=1, print_grid=False, shared_xaxes=True, subplot_titles=titles)

        figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'])
        for i in range(3):
            figure['layout']['xaxis%d' % (i + 1)].update(showticklabels=True, **axis_layout)
        figure['layout']['yaxis1'].update(title="Acceleration (m/s^2)")
        figure['layout']['yaxis2'].update(title="Rotation Rate (rad/s)")
        figure['layout']['yaxis3'].update(title="Interval (sec)")

        figure.add_trace(go.Scattergl(x=time, y=data.accel_mps2[0, :], customdata=customdata, name='X',
                                      legendgroup='x', mode='lines', line={'color': 'red'}),
                         1, 1)
        figure.add_trace(go.Scattergl(x=time, y=data.accel_mps2[1, :], customdata=customdata, name='Y',
                                      legendgroup='y', mode='lines', line={'color': 'green'}),
                         1, 1)
        figure.add_trace(go.Scattergl(x=time, y=data.accel_mps2[2, :], customdata=customdata, name='Z',
                                      legendgroup='z', mode='lines', line={'color': 'blue'}),
                         1, 1)

        figure.add_trace(go.Scattergl(x=time, y=data.gyro_rps[0, :], customdata=customdata, name='X',
                                      legendgroup='x', showlegend=False, mode='lines', line={'color': 'red'}),
                         2, 1)
        figure.add_trace(go.Scattergl(x=time, y=data.gyro_rps[1, :], customdata=customdata, name='Y',
                                      legendgroup='y', showlegend=False, mode='lines', line={'color': 'green'}),
                         2, 1)
        figure.add_trace(go.Scattergl(x=time, y=data.gyro_rps[2, :], customdata=customdata, name='Z',
                                      legendgroup='z', showlegend=False, mode='lines', line={'color': 'blue'}),
                         2, 1)

        # Note: Interval is always computed from data.p1_time (plain seconds), not time -- time may be a datetime64
        # axis (UTC mode), which does not support subtraction the same way.
        figure.add_trace(go.Scattergl(x=time[1:], y=np.diff(data.p1_time), customdata=customdata[:, 1:],
                                      name='Interval', mode='markers', marker={'color': 'red'}),
                         3, 1)

        self._add_figure(name=filename, figure=figure, title=figure_title, custom_hover=True,
                         inject_js=self._custom_tooltip_js())

    def plot_gnss_attitude_measurements(self):
        """!
        @brief Generate time series plots for GNSS attitude (degrees) and baseline distance (meters) data.
        """
        if self.output_dir is None:
            return

        # Read the attitude measurement data.
        result = self.reader.read(message_types=[RawGNSSAttitudeOutput, GNSSAttitudeOutput], **self.params)
        raw_heading_data = result[RawGNSSAttitudeOutput.MESSAGE_TYPE]
        heading_data = result[GNSSAttitudeOutput.MESSAGE_TYPE]

        if (len(heading_data.p1_time) == 0) and (len(raw_heading_data.p1_time) == 0):
            self.logger.info('No GNSS attitude measurement data available. Skipping plot.')
            return

        # Note that we read the pose data after attitude, that way we don't bother reading pose data from disk if
        # there's no heading data in the log.
        result = self.reader.read(message_types=[PoseMessage], source_ids=self.default_source_id, **self.params)
        primary_pose_data = result[PoseMessage.MESSAGE_TYPE]
        have_primary = (primary_pose_data is not None and
                        np.any(primary_pose_data.solution_type != SolutionType.Invalid))

        # Extract X axis data to be plotted below.
        if have_primary:
            primary_time, _ = self._resolve_x_axis(p1_time=primary_pose_data.p1_time,
                                                    gps_time=primary_pose_data.gps_time)
            primary_customdata = self._time_hover_customdata(p1_time=primary_pose_data.p1_time,
                                                              gps_time=primary_pose_data.gps_time)

        have_raw = len(raw_heading_data.p1_time) > 0
        if have_raw:
            raw_gps_time = getattr(raw_heading_data, 'gps_time', None)
            raw_time, _ = self._resolve_x_axis(p1_time=raw_heading_data.p1_time, gps_time=raw_gps_time)
            raw_customdata = self._time_hover_customdata(p1_time=raw_heading_data.p1_time, gps_time=raw_gps_time)

        have_corrected = len(heading_data.p1_time) > 0
        if have_corrected:
            corrected_gps_time = getattr(heading_data, 'gps_time', None)
            corrected_time, _ = self._resolve_x_axis(p1_time=heading_data.p1_time, gps_time=corrected_gps_time)
            corrected_customdata = self._time_hover_customdata(p1_time=heading_data.p1_time,
                                                                gps_time=corrected_gps_time)

        # Setup the figure.
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=(
                'Vehicle Heading',
                'Primary->Secondary Antenna ENU Vector + Baseline Distance',
                'Solution Type'
            ),
            shared_xaxes=True,
        )

        fig.update_layout(title='GNSS Attitude Measurements (Multi-Antenna Heading Sensor)',
                          showlegend=True, modebar_add=['v1hovermode'])

        fig.update_xaxes(showticklabels=True, **self._x_axis_layout())
        fig.update_yaxes(title_text='Heading (deg)', rangemode='tozero', row=1, col=1)
        fig.update_yaxes(title_text='Distance (m)', row=2, col=1)
        fig.update_yaxes(
            ticktext=['%s (%d)' % (e.name, e.value) for e in SolutionType],
            tickvals=[e.value for e in SolutionType],
            title_text='Solution Type',
            row=3, col=1
        )

        ########################################
        # Heading
        ########################################

        # Display the navigation engine's heading estimate, if available, for comparison with the heading sensor
        # measurement.
        if have_primary:
            heading_deg = yaw_to_heading(primary_pose_data.ypr_deg[0, :])
            yaw_std_deg = primary_pose_data.ypr_std_deg[0, :]

            # Plotly has a bug where the std dev field will display as "%{customdata[1]}" if it is NAN. To get around
            # this, we set the std dev to -1 when not available.
            yaw_std_deg[np.isnan(yaw_std_deg)] = -1.0

            fig.add_trace(
                go.Scatter(
                    x=primary_time, y=heading_deg,
                    customdata=np.vstack((primary_customdata, yaw_std_deg)),
                    name='Heading: Navigation Engine', legendgroup='nav',
                    mode='lines', line={'color': 'yellow'}
                ),
                row=1, col=1
            )

        # Raw (uncorrected) heading, derived from reported ENU vector.
        if have_raw:
            yaw_deg = np.degrees(np.arctan2(raw_heading_data.relative_position_enu_m[1, :],
                                            raw_heading_data.relative_position_enu_m[0, :]))
            heading_deg = yaw_to_heading(yaw_deg)
            fig.add_trace(
                go.Scatter(
                    x=raw_time, y=heading_deg, customdata=raw_customdata,
                    name='Heading: Raw Measurement', legendgroup='raw',
                    mode='markers', marker={"color": "purple"}
                ),
                row=1, col=1
            )

        # Corrected heading plot
        if have_corrected:
            heading_deg = yaw_to_heading(heading_data.ypr_deg[0, :])
            yaw_std_deg = heading_data.ypr_std_deg[0, :]

            # See explanation above about the Plotly bug when the value is NAN.
            yaw_std_deg[np.isnan(yaw_std_deg)] = -1.0

            fig.add_trace(
                go.Scatter(
                    x=corrected_time, y=heading_deg,
                    customdata=np.vstack((corrected_customdata, yaw_std_deg)),
                    name='Heading: Corrected Measurement', legendgroup='corr',
                    mode='markers', marker={"color": "orange"}
                ),
                row=1, col=1
            )

        ########################################
        # ENU Vector/Baseline Distance
        ########################################

        # Baseline vector from raw attitude measurement.
        if have_raw:
            baseline_distance_m = np.linalg.norm(raw_heading_data.relative_position_enu_m, axis=0)
            fig.add_trace(
                go.Scatter(
                    x=raw_time, y=baseline_distance_m, customdata=raw_customdata,
                    name='Baseline Distance: Raw Measurement', legendgroup='raw',
                    mode='markers', marker={"color": "purple"}
                ),
                row=2, col=1
            )

        # Baseline distance from corrected measurement.
        if have_corrected:
            baseline_distance_m = heading_data.baseline_distance_m
            baseline_std_m = heading_data.baseline_distance_std_m

            # See explanation above about the Plotly bug when the value is NAN.
            baseline_std_m[np.isnan(baseline_std_m)] = -1.0

            fig.add_trace(
                go.Scatter(
                    x=corrected_time, y=baseline_distance_m,
                    customdata=np.vstack((corrected_customdata, baseline_std_m)),
                    name='Baseline Distance: Corrected Measurement', legendgroup='corr',
                    mode='markers', marker={"color": "orange"}
                ),
                row=2, col=1
            )

        # ENU vector from raw attitude measurement.
        if have_raw:
            fig.add_trace(
                go.Scatter(
                    x=raw_time, y=raw_heading_data.relative_position_enu_m[0], customdata=raw_customdata,
                    name='Primary->Secondary (East)',
                    mode='markers', marker={"color": "red"}
                ),
                row=2, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=raw_time, y=raw_heading_data.relative_position_enu_m[1], customdata=raw_customdata,
                    name='Primary->Secondary (North)',
                    mode='markers', marker={"color": "green"}
                ),
                row=2, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=raw_time, y=raw_heading_data.relative_position_enu_m[2], customdata=raw_customdata,
                    name='Primary->Secondary (Up)',
                    mode='markers', marker={"color": "blue"}
                ),
                row=2, col=1
            )

        ########################################
        # Solution Type
        ########################################

        # Display the navigation engine's solution type.
        if have_primary:
            fig.add_trace(
                go.Scatter(
                    x=primary_time, y=primary_pose_data.solution_type, customdata=primary_customdata,
                    name='Solution Type: Navigation Engine', legendgroup='nav',
                    mode='markers', marker={'color': 'yellow'},
                ),
                row=3, col=1
            )

        # Display the raw measurement's solution type.
        if have_raw:
            fig.add_trace(
                go.Scatter(
                    x=raw_time, y=raw_heading_data.solution_type, customdata=raw_customdata,
                    name='Solution Type: Raw Measurement', legendgroup='raw',
                    mode='markers', marker={'color': 'purple'},
                ),
                row=3, col=1
            )

        # Display the corrected measurement's solution type.
        if have_corrected:
            fig.add_trace(
                go.Scatter(
                    x=corrected_time, y=heading_data.solution_type, customdata=corrected_customdata,
                    name='Solution Type: Corrected Measurement', legendgroup='corr',
                    mode='markers', marker={'color': 'orange'},
                ),
                row=3, col=1
            )

        # Custom hover function: like _TIME_HOVER_JS, but some traces carry a second customdata row with a standard
        # deviation value (in degrees for heading traces, meters for baseline distance traces; -1 means not available -
        # see the Plotly NaN customdata bug noted above).
        _ATTITUDE_HOVER_JS = """\
figure.on('plotly_hover', function(data) {
  let point = data.points[0];
  if (!point.data.customdata) {
    return;
  }
  let new_text = BuildAxisValueHoverText(point) + '<br>' +
                 BuildTimeHoverText(point.x, GetCustomData(point, 0));
  let customdata = point.data.customdata.hasOwnProperty("_inputArray") ?
                   point.data.customdata._inputArray : point.data.customdata;
  if (customdata.length > 1) {
    let std = GetCustomData(point, 1);
    if (std >= 0) {
      let units = point.data.name.startsWith('Heading') ? 'deg' : 'm';
      new_text += `<br>Std: ${std.toFixed(2)} ${units}`;
    }
  }
  ShowCustomTooltip(point, GetCustomTooltipHTML(point.data.name, undefined, new_text));
});
figure.on('plotly_unhover', function(data) {
  HideCustomTooltip();
});
        """ + self._GPS_TICK_REFORMAT_JS

        self._add_figure(name='gnss_attitude_measurement', figure=fig,
                         title='Measurements: GNSS Attitude (Multi-Antenna Heading Sensor)',
                         custom_hover=True, inject_js=_ATTITUDE_HOVER_JS)

    def plot_system_status_profiling(self):
        """!
        @brief Plot system status profiling data.
        """
        if self.output_dir is None:
            return

        # Read the data.
        result = self.reader.read(message_types=[SystemStatusMessage], remove_nan_times=False, **self.params)
        data = result[SystemStatusMessage.MESSAGE_TYPE]

        if len(data.p1_time) == 0:
            self.logger.info('No system status data available. Skipping plot.')
            return

        time, axis_layout = self._resolve_x_axis(p1_time=data.p1_time)
        customdata = self._time_hover_customdata(p1_time=data.p1_time)

        # Setup the figure.
        figure = make_subplots(rows=2, cols=1, print_grid=False, shared_xaxes=True,
                               subplot_titles=['GNSS Temperature', 'Positioning Engine CPU Temperature'])

        figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'])
        for i in range(2):
            figure['layout']['xaxis%d' % (i + 1)].update(showticklabels=True, **axis_layout)
        figure['layout']['yaxis1'].update(title="Temp (deg C)")

        # Plot the data.
        figure.add_trace(go.Scattergl(x=time, y=data.gnss_temperature_degc, customdata=customdata,
                                      name='GNSS Temperature',
                                      mode='markers', line={'color': 'red'}),
                         1, 1)
        figure.add_trace(go.Scattergl(x=time, y=data.pe_cpu_temperature_degc, customdata=customdata,
                                      name='PE CPU Temperature',
                                      mode='markers', line={'color': 'orange'}),
                         2, 1)

        self._add_figure(name="profile_system_status", figure=figure, title="Profiling: System Status",
                         custom_hover=True, inject_js=self._custom_tooltip_js())

    def plot_events(self):
        """!
        @brief Generate a table of event notifications.
        """
        if self.output_dir is None:
            return

        # Read the data.
        data = self.reader.read(message_types={MessageType.EVENT_NOTIFICATION} | COMMAND_MESSAGES | RESPONSE_MESSAGES,
                                remove_nan_times=False, return_in_order=True, return_bytes=True, **self.params)

        if len(data.messages) == 0:
            self.logger.info('No event notification data available.')
            return

        times_before_resets = self.extract_times_before_reset()
        table_columns = ['Relative Time (s)', 'System Time (s)', 'Previous P1 Time (s)', 'Event', 'Flags',
                         'Description']

        rows = []
        system_t0_ns = self.reader.get_system_t0_ns()
        max_bytes = 128
        for message, message_bytes in zip(data.messages, data.message_bytes):
            system_time_ns = message.get_system_time_ns()
            if isinstance(message, EventNotificationMessage):
                event_type = message.event_type
                flags = message.event_flags
                description_str = message.event_description_to_string(max_bytes=max_bytes)
            else:
                flags = None
                if message.get_type() in COMMAND_MESSAGES:
                    event_type = EventType.COMMAND
                else:
                    event_type = EventType.COMMAND_RESPONSE
                description_str = "%s\n%s" % \
                                  (repr(message),
                                   EventNotificationMessage._populate_data_byte_string(message_bytes,
                                                                                       max_bytes=max_bytes))

            rows.append([
                f'{(system_time_ns - system_t0_ns) / 1e9:.3f}' if system_time_ns is not None else 'N/A',
                f'{system_time_ns / 1e9:.3f}' if system_time_ns is not None else 'N/A',
                '',
                event_type.to_string(include_value=True),
                f'0x{flags:016X}' if flags is not None else 'N/A',
                description_str.replace('<', '[').replace('>', ']').replace('\n', '<br>'),
            ])

            if isinstance(message, EventNotificationMessage) and message.event_type == EventType.RESET:
                if system_time_ns in times_before_resets:
                    rows[-1][2] = f'{(times_before_resets[system_time_ns]):.3f}'

        table_data = ',\n  '.join([repr(row) for row in rows])
        body_html = """\
<script>
// Reference: https://jsfiddle.net/ej7z5kdc/
class FilteredTable {
  static next_checkbox_id = 0;

  constructor(columns, data, filter_col_indices, filter_placeholder) {
    this.columns = columns;
    this.input_data = data;
    this.filter_col_indices = filter_col_indices;
    this.filter_placeholder = filter_placeholder;
  }

  /** @returns {{match: boolean, $node: Element}[]} */
  search(filter, invert) {
    if (!this.$tbody) {
      return;
    }

    let count = 0;
    let results = this.data.map(entry => {
      const searchable_data = entry.searchable_data;
      const $node = entry.$node;
      let matches = false;
      if (filter === "") {
        matches = true;
      }
      else {
        for (let i = 0; i < searchable_data.length; ++i) {
          if (searchable_data[i].indexOf(filter) >= 0) {
            matches = true;
            break;
          }
        }

        if (invert) {
          matches = !matches;
        }
      }
      if (matches) {
        ++count;
      }
      return {
        match: matches,
        $node,
      };
    });
    return {count: count, results: results};
  }

  getControls() {
    this._createTable();
    return this.$controls;
  }

  getElement() {
    this._createTable();
    return this.$container;
  }

  _createTable() {
    if (!this.$container) {
      const $controls = document.createElement("div");
      this.$controls = $controls;
      let checkbox_id = "__checkbox_" + FilteredTable.next_checkbox_id++;
      $controls.innerHTML = `
<div><input type="text" class="filter" style="width: 100%;" placeholder="${this.filter_placeholder}"></div>
<div>
  <input type="checkbox" class="invert" id="${checkbox_id}">
  <label for="${checkbox_id}"> Invert Selection</label>
</div>
<div>Displaying <div class="count" style="display: inline;"></div>/<div class="total" style="display: inline;"></div> elements.</div>`;

      this.$filter = $controls.querySelector(".filter");
      this.$invert = $controls.querySelector(".invert");
      this.$count = $controls.querySelector(".count");
      this.$total = $controls.querySelector(".total");

      const $container = document.createElement("div");
      this.$container = $container;
      $container.innerHTML = `
<table><tbody style="vertical-align: top"></tbody></table>`;

      this.$tbody = $container.querySelector("tbody");

      // Bind a filter function to the controls.
      const filterData = () => {
        const filter = this.$filter.value.toLowerCase();
        const invert = this.$invert.checked;
        let results = this.search(filter, invert);
        results.results.forEach(entry => entry.$node.style.display = entry.match ? "" : "none");
        this.$count.textContent = results.count;
      };

      this.$filter.addEventListener("blur", filterData);
      var typing_timer;
      this.$filter.addEventListener("keydown", () => {
        clearTimeout(typing_timer);
      });
      this.$filter.addEventListener("keyup", (event) => {
        clearTimeout(typing_timer);
        if (event.key === "Enter") {
          filterData();
        }
        else {
          typing_timer = setTimeout(filterData, 250);
        }
      });
      this.$invert.addEventListener("change", filterData);

      // Populate the table header.
      const $header_tr = document.createElement("tr");
      $header_tr.style = "background-color: #a2c4fa";
      this.columns.map(text => {
        const $td = document.createElement("th");
        $td.innerHTML = text;
        $header_tr.appendChild($td);
      });
      this.$tbody.appendChild($header_tr);

      // Populate the table contents, and save a reference to the DOM row nodes with our data.
      this.data = this.input_data.map(entry => {
        const $tr = document.createElement("tr");
        let searchable_data = [];
        for (let col = 0; col < entry.length; ++col) {
          const $td = document.createElement("td");
          $td.innerHTML = entry[col];
          $tr.appendChild($td);
          if (this.filter_col_indices.indexOf(col) >= 0) {
            searchable_data.push(entry[col].toLowerCase());
          }
        }
        this.$tbody.appendChild($tr);

        return {
          $node: $tr,
          searchable_data: searchable_data,
        };
      });

      this.$count.textContent = this.data.length;
      this.$total.textContent = this.data.length;
    }
  }
}
</script>
""" + f"""\
<h2>Device Event Log</h2>
<div class="controls"></div>
<pre><div class="table"></div></pre>
<script>
const column_headers = {repr(table_columns)};
const table_data = [
{table_data}
];
const filtered_table = new FilteredTable(column_headers, table_data, [3, 5], "Filter by event type or description...");
document.body.querySelector(".controls").appendChild(filtered_table.getControls());
document.body.querySelector(".table").appendChild(filtered_table.getElement());
</script>
"""

        self._add_page(name='event_log', html_body=body_html, title="Event Log")

    def extract_times_before_reset(self):
        # Iterate backwards over indices to extract resets and the P1 times before them.
        curr_reset_time = None
        get_time_before_reset = False

        times_before_resets = {}
        file_index = self.reader.get_index()
        for entry in file_index[::-1]:
            if entry.type == MessageType.EVENT_NOTIFICATION or get_time_before_reset:
                # Parse entry at index for payload.
                header, payload = self.reader.reader.parse_entry_at_index(entry)
                # If entry at index is of a class that isn't recognized, then skip it.
                try:
                    if get_time_before_reset and payload.get_p1_time() is not None:
                        times_before_resets[curr_reset_time] = float(payload.get_p1_time())
                        get_time_before_reset = False

                    # Check if event is a reset.
                    if entry.type == MessageType.EVENT_NOTIFICATION and payload.event_type == EventType.RESET:
                        curr_reset_time = payload.get_system_time_ns()
                        get_time_before_reset = True
                except Exception as e:
                    continue

        return times_before_resets

    def generate_index(self, reference: Optional[ReferenceData] = None, auto_open: bool = True):
        """!
        @brief Generate an `index.html` page with links to all generated figures.

        @param reference Reference data, if loaded.
        @param auto_open If `True`, open the page automatically in a web browser.
        """
        if len(self.plots) == 0:
            self.logger.warning('No plots generated. Index will contain summary only.')

        self._set_data_summary()

        if self._mapbox_token_missing:
            self.summary += """\n
<p style="color: red">
  Warning: Mapbox token not specified. Generated map using Open Street Maps
  street data. For satellite imagery, please request a free access token from
  https://account.mapbox.com/access-tokens, then provide the token by
  specifying --mapbox-token or setting the MAPBOX_ACCESS_TOKEN environment
  variable.
</p>
"""

        index_path = os.path.join(self.output_dir, self.prefix + 'index.html')
        index_dir = os.path.dirname(index_path)

        links = ''
        title_to_name = {e['title']: n for n, e in self.plots.items()}
        titles = sorted(title_to_name.keys())
        for title in titles:
            name = title_to_name[title]
            entry = self.plots[name]
            if entry['path'] is None:
                link = '<br><i>%s</i>' % title
            else:
                link = '<br><a href="%s" target="_blank">%s</a>' % (os.path.relpath(entry['path'], index_dir), title)
            links += link

        body = ''
        if reference is not None:
            body += f'Reference data source: {reference.description}<br>'
        body += links + '\n<pre>' + self.summary.replace('\n', '<br>') + '</pre>'

        index_html = _page_template % {
            'title': 'FusionEngine Output',
            'body': body
        }

        os.makedirs(index_dir, exist_ok=True)
        with open(index_path, 'w') as f:
            self.logger.info('Creating %s...' % index_path)
            f.write(index_html)

        if auto_open:
            self._open_browser(index_path)

    def _calculate_duration(self, return_index=False):
        # Restrict the index to the user-requested time range.
        full_index = self.reader.get_index()
        reduced_index = full_index[self.params['time_range']]

        # Calculate the log duration.
        idx = ~np.isnan(full_index['time'])
        time = full_index['time'][idx]
        if len(time) >= 2:
            log_duration_sec = time[-1] - time[0]
        else:
            log_duration_sec = np.nan

        idx = ~np.isnan(reduced_index['time'])
        time = reduced_index['time'][idx]
        if len(time) >= 2:
            processing_duration_sec = time[-1] - time[0]
        else:
            processing_duration_sec = np.nan

        if return_index:
            return log_duration_sec, processing_duration_sec, reduced_index
        else:
            return log_duration_sec, processing_duration_sec

    def _set_data_summary(self):
        # Calculate the log duration.
        log_duration_sec, processing_duration_sec, reduced_index = self._calculate_duration(return_index=True)

        # Create a table with position solution type statistics.
        result = self.reader.read(message_types=[PoseMessage], source_ids=self.default_source_id, **self.params)
        pose_data = result[PoseMessage.MESSAGE_TYPE]
        num_pose_messages = len(pose_data.solution_type)
        solution_type_count = {}
        for type, info in _SOLUTION_TYPE_MAP.items():
            solution_type_count[info.name] = np.sum(pose_data.solution_type == type)

        types = list(solution_type_count.keys())
        counts = ['%d' % c for c in solution_type_count.values()]
        if num_pose_messages == 0:
            percents = ['N/A' for c in solution_type_count.values()]
        else:
            percents = ['%.1f%%' % (float(c) / num_pose_messages * 100.0) for c in solution_type_count.values()]

        types.append(None)
        counts.append(None)
        percents.append(None)

        types.append('Total')
        counts.append('%d' % num_pose_messages)
        percents.append('')

        solution_type_table = _data_to_table(['Position Type', 'Count', 'Percent'], [types, counts, percents])

        # Determine the GPS start time if pose data is present. GPS time may not appear in the first pose update, and
        # even if it does, t0 may not correspond with the first pose message if something else was output first. So just
        # in case, we'll approximate the GPS time _at_ t0 if needed.
        idx = find_first(~np.isnan(pose_data.gps_time))
        if idx >= 0:
            first_p1_time = self.reader.t0
            dt_p1_sec = pose_data.p1_time[idx] - float(first_p1_time)
            t0_gps = Timestamp(pose_data.gps_time[idx]) - dt_p1_sec
            # If the first pose is pretty close to t0, we'll assume the approximation is reasonably accurate and not
            # bother reporting it.
            t0_is_approx = dt_p1_sec > 10.0
        else:
            t0_gps = Timestamp()
            t0_is_approx = False

        # Find the _processed_ t0, i.e., the first P1 and system times within the requested time range.
        params = copy.deepcopy(self.params)
        params['max_messages'] = 1
        params['return_in_order'] = True

        result = self.reader.read(message_types=None, require_p1_time=True, **params)
        if len(result.messages) > 0:
            processed_t0 = result.messages[0].get_p1_time()
            processed_t0_gps = t0_gps + (processed_t0 - self.reader.t0)
            processed_t0_is_approx = t0_is_approx
        else:
            processed_t0 = Timestamp()
            processed_t0_gps = None
            processed_t0_is_approx = None

        result = self.reader.read(message_types=None, require_system_time=True, **params)
        if len(result.messages) > 0:
            processed_system_t0 = result.messages[0].get_system_time_sec()
        else:
            processed_system_t0 = None

        # Create a table with log times and durations.
        def _time_strings(t0, system_t0, t0_gps, t0_is_approx):
            strings = []
            if t0 is None:
                strings.append('P1: None')
            else:
                strings.append(f'P1: {t0.to_p1_str()}')
            if system_t0 is None:
                strings.append('System: None')
            else:
                strings.append(f"System: {system_time_to_str(system_t0, is_seconds=True).replace(' time', ':')}")
            strings.append(self._gps_sec_to_string(t0_gps, is_approx=t0_is_approx))
            return strings

        descriptions = [
            'Log Start Time',
            '',
            '',
            'Total Log Duration',
            '',
            'Processed Start Time',
            '',
            '',
            'Processed Duration',
        ]
        times = [
            # Log summary.
            *_time_strings(t0=self.reader.t0, system_t0=self.reader.get_system_t0(),
                           t0_gps=t0_gps, t0_is_approx=t0_is_approx),
            log_duration_sec,
            '',
            # Processed data summary.
            *_time_strings(t0=processed_t0, system_t0=processed_system_t0,
                           t0_gps=processed_t0_gps, t0_is_approx=processed_t0_is_approx),
            '%.1f seconds' % processing_duration_sec,
        ]
        time_table = _data_to_table(['Description', 'Time'], [descriptions, times])

        # Create a table with the types and counts of each FusionEngine message type in the log.
        message_types, message_counts = np.unique(reduced_index['type'], return_counts=True)
        message_types = [MessageType.get_type_string(t) for t in message_types]

        message_counts = message_counts.tolist()
        message_types.append(None)
        message_counts.append(None)

        message_types.append('Total')
        message_counts.append(f'{len(self.reader.get_index())}')

        message_table = _data_to_table(['Message Type', 'Count'], [message_types, message_counts])

        params_no_numpy = copy.deepcopy(self.params)
        params_no_numpy['return_numpy'] = False

        # Create a software version table.
        result = self.reader.read(message_types=[VersionInfoMessage.MESSAGE_TYPE], remove_nan_times=False,
                                  **params_no_numpy)
        if len(result[VersionInfoMessage.MESSAGE_TYPE].messages) != 0:
            version = result[VersionInfoMessage.MESSAGE_TYPE].messages[-1]
            version_types = {'fw': 'Firmware', 'engine': 'FusionEngine', 'os': 'OS', 'rx': 'GNSS Receiver'}
            version_values = [str(vars(version)[k + '_version_str']) for k in version_types.keys()]
            version_table = _data_to_table(['Type', 'Version'], [list(version_types.values()), version_values])
        else:
            version_table = 'No version information.'

        # Now populate the summary.
        if self.summary != '':
            self.summary += '\n\n'

        args = {
            'message_table': message_table,
            'version_table': version_table,
            'solution_type_table': solution_type_table,
            'time_table': time_table,
        }

        self.summary += """
%(version_table)s

%(time_table)s

%(solution_type_table)s

%(message_table)s
""" % args

    def _add_page(self, name, html_body, title=None):
        if title is None:
            title = name

        if name in self.plots:
            raise ValueError('Plot "%s" already exists.' % name)
        elif name == 'index':
            raise ValueError('Plot name cannot be index.')

        path = os.path.join(self.output_dir, self.prefix + name + '.html')
        self.logger.info('Creating %s...' % path)

        table_html = _page_template % {
            'title': title,
            'body': html_body
        }

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as fd:
            fd.write(table_html)

        self.plots[name] = {'title': title, 'path': path}

    def _add_figure(self, name, figure=None, title=None, config=None, inject_js: str = None,
                    time_axis_type: Optional[str] = None, custom_hover: bool = False):
        """!
        @brief Generate an HTML file for the specified figure.

        @param name The machine-friendly name of the figure (will be used to generate the HTML filename).
        @param figure A figure object for a supported display library.
        @param title An optional human-friendly display title to be added to the generated @c index.html file.
        @param config An optional dictionary containing Plotly.js figure config options to be included in the generated
               JavaScript.
        @param inject_js Custom Javascript to be injected into the generated HTML file (see @ref
               __write_html_and_inject_js()).
        @param time_axis_type The time domain actually plotted on this figure's X axis (`relative`, `p1`, `gps`, or
               `utc`; see @ref BuildTimeHoverText() in `plotly_data_support.js`). Defaults to `self.time_type`; only
               needs to be overridden by plots (e.g., @ref plot_time_scale()) whose X axis does not follow it.
        @param custom_hover If `True`, set `hoverinfo='none'` on all of this figure's traces so Plotly's native hover
               label never draws, for use with a custom-tooltip `inject_js` (see @ref _custom_tooltip_js()) instead
               of per-trace `hoverinfo='none'` at every `go.Scatter()`/`go.Scattergl()` call site.
        """
        if title is None:
            title = name

        if time_axis_type is None:
            time_axis_type = self.time_type

        if name in self.plots:
            raise ValueError('Plot "%s" already exists.' % name)
        elif name == 'index':
            raise ValueError('Plot name cannot be index.')

        if figure is not None:
            figure.update_traces(hoverlabel_namelength=-1)
            if custom_hover:
                figure.update_traces(hoverinfo='none')

            path = os.path.join(self.output_dir, self.prefix + name + '.html')
            self.logger.info('Creating %s...' % path)

            os.makedirs(os.path.dirname(path), exist_ok=True)

            if inject_js is not None:
                plotly.io.write_html = functools.partial(self.__write_html_and_inject_js, inject_js, time_axis_type)

            plotly.offline.plot(
                figure,
                output_type='file',
                filename=path,
                include_plotlyjs=True,
                auto_open=False,
                show_link=False,
                config=config)

            if inject_js is not None:
                plotly.io.write_html = Analyzer.__original_write_html

        self.plots[name] = {'title': title, 'path': path if figure is not None else None}

    # Support for injecting custom javascript into the generated plotly HTML file.
    def __write_html_and_inject_js(self, inject_js, time_axis_type, *args, **kwargs):
        post_script = kwargs.get("post_script", None)
        if post_script is None:
            post_script = ""

        # Create global variables with the log's t0 timestamp, the (leap-second accurate) GPS/POSIX offset, the
        # system time t0 (see BuildSystemTimeHoverText()), and the time domain plotted on this figure's X axis (see
        # BuildTimeHoverText()). Note: self.reader.t0 and self.system_t0 may each independently be unavailable (e.g.
        # a system-time-only profiling log has no P1 time at all), so both need a 'null' fallback -- plots that
        # don't use one of these domains at all still go through this same code path whenever inject_js is set.
        gps_posix_offset_sec = self.time_provider.get_gps_posix_offset_sec()
        p1_t0_sec = None if self.reader.t0 is None else float(self.reader.t0)
        system_t0_sec = None if np.isnan(self.system_t0) else float(self.system_t0)
        post_script += f"""\
var p1_t0_sec = {p1_t0_sec if p1_t0_sec is not None else 'null'};
var p1_time_axis_rel = {'true' if self.time_type == 'relative' else 'false'};
var gps_posix_offset_sec = {gps_posix_offset_sec if gps_posix_offset_sec is not None else 'null'};
var system_t0_sec = {system_t0_sec if system_t0_sec is not None else 'null'};
var time_axis_type = '{time_axis_type}';
"""

        # Inject common plotly data support functions (GetTimeText(), etc.).
        script_dir = os.path.join(os.path.dirname(__file__))
        with open(os.path.join(script_dir, 'plotly_data_support.js'), 'rt') as f:
            post_script += f.read()

        # Now inject the custom javascript.
        post_script += inject_js

        kwargs["post_script"] = post_script
        return Analyzer.__original_write_html(*args, **kwargs)

    __original_write_html = plotly.io.write_html

    def _open_browser(self, filename):
        try:
            webbrowser.open("file:///" + os.path.abspath(filename))
        except BaseException:
            self.logger.error("Unable to open web browser.")

    @classmethod
    def get_mapbox_token(cls, token=None):
        # If the user specified a token, use that.
        if token is not None:
            return token

        # Otherwise, check for environment variables.
        token = os.environ.get('MAPBOX_ACCESS_TOKEN', None)
        if token is not None:
            return token

        token = os.environ.get('MapboxAccessToken', None)
        if token is not None:
            return token

        return None

    def _get_t0_for_time_source(self, time_source: SystemTimeSource) -> float:
        if time_source == SystemTimeSource.P1_TIME:
            if self.time_type == 'relative':
                return float(self.reader.t0)
            else:
                return 0.0
        elif time_source == SystemTimeSource.GPS_TIME:
            return 0.0
        elif time_source == SystemTimeSource.SENDER_SYSTEM_TIME:
            return 0.0
        elif time_source == SystemTimeSource.TIMESTAMPED_ON_RECEPTION:
            if self.time_type == 'relative':
                return float(self.reader.get_system_t0())
            else:
                return 0.0

    def _x_axis_layout(self, time_source: str = 'p1', ignore_gps: bool = False) -> dict:
        """!
        @brief Get the `go.layout.XAxis` kwargs (including `title`) for the current @c self.time_type.

        @param time_source The native time domain of the data being plotted: `p1` (the default -- P1/relative/GPS/
               UTC, per @c self.time_type) or `system` (device system time). There is no system-time-to-P1/GPS
               mapping yet, so `system` always resolves to plain absolute/relative system time regardless of
               @c self.time_type; once such a mapping exists, it can resolve to p1/gps/utc too, like `p1` below.
        @param ignore_gps If `True`, return relative or absolute P1 time. Do not return GPS or UTC time, regardless of
               @ref self.time_type.

        @return A dict of `go.layout.XAxis` kwargs, e.g. `{'title': ..., 'type': 'date'}`.
        """
        if time_source == 'system':
            if self.time_type == 'relative':
                return {'title': 'Relative Time (sec)'}
            else:
                return {'title': 'System Time (sec)'}

        if self.time_type == 'relative':
            return {'title': 'Relative Time (sec)'}
        elif self.time_type == 'p1' or ignore_gps:
            return {'title': 'P1 Time (sec)'}
        elif self.time_type == 'gps':
            # GPS seconds are large enough that Plotly may otherwise render ticks in scientific/SI-prefix notation,
            # which _ReformatGpsAxisTicks() (see plotly_data_support.js) can't parse back into week:tow. We let
            # Plotly auto-generate normal (zoom-aware) numeric ticks here, and rewrite the rendered tick text into
            # week:tow client-side, rather than computing fixed tick positions/labels ourselves -- those wouldn't
            # regenerate on zoom/pan and could leave a zoomed-in view with no visible ticks at all.
            return {'title': 'GPS Time (week:tow)', 'exponentformat': 'none'}
        else:
            # Plotly serializes a datetime64 array as literal date strings, so (unlike plain milliseconds-since-
            # epoch numbers) they display as given, without being reinterpreted in the browser's local timezone.
            return {'title': 'UTC Time', 'type': 'date'}

    def _resolve_x_axis(self, p1_time: Optional[np.ndarray] = None, gps_time: Optional[np.ndarray] = None,
                        system_time: Optional[np.ndarray] = None, time_source: str = 'p1',
                        ignore_gps: bool = False) -> \
            Tuple[np.ndarray, dict]:
        """!
        @brief Resolve the X axis values and layout to use for a time series, per @c self.time_type.

        @param p1_time The P1 time for each point. Required (and only used) when `time_source` is `p1`.
        @param gps_time The GPS time for each point, if already known (e.g., from a @ref PoseMessage). If `None`, it
               will be computed from `p1_time` via @c self.time_provider when needed. Only used when `time_source`
               is `p1`.
        @param system_time The device system time for each point. Required (and only used) when `time_source` is
               `system`.
        @param time_source The native time domain of `p1_time`/`system_time`: `p1` (the default) or `system` (see
               @ref _x_axis_layout()).
        @param ignore_gps If `True`, return relative or absolute P1 time. Do not return GPS or UTC time, regardless of
               @ref self.time_type.

        @return A tuple `(x, axis_layout)`:
                - `x`: The X axis values to plot.
                - `axis_layout`: `go.layout.XAxis` kwargs needed to display `x` (title, and e.g. `type='date'`).
        """
        axis_layout = self._x_axis_layout(time_source=time_source, ignore_gps=ignore_gps)

        if time_source == 'system':
            # self.system_t0 is set to 0 when self.time_type == 'absolute', so this works for both absolute and relative
            # time axes. See _x_axis_layout().
            return system_time - float(self.system_t0), axis_layout

        if self.time_type == 'relative':
            return p1_time - float(self.reader.t0), axis_layout
        elif self.time_type == 'p1' or ignore_gps:
            return p1_time, axis_layout

        if gps_time is None:
            gps_time = self.time_provider.p1_to_gps(p1_time)

        if self.time_type == 'gps':
            return gps_time, axis_layout
        else:
            utc = self.time_provider.gps_sec_to_datetime64_array(gps_time)
            return utc, axis_layout

    def _time_hover_customdata(self, p1_time: np.ndarray, gps_time: Optional[np.ndarray] = None,
                               x_domain: Optional[str] = None) -> np.ndarray:
        """!
        @brief Build the customdata array needed by `BuildTimeHoverText()` for a trace (see `plotly_data_support.js`).

        Only whichever of P1/GPS time is NOT already reflected by the X axis needs to be included here -- the other
        is recoverable in Javascript from the X value via a constant offset (P1 <-> relative, or GPS <-> UTC).

        @param p1_time The P1 time for each point.
        @param gps_time The GPS time for each point, or `None` if not already known. Computed from `p1_time` via
               @c self.time_provider if `x_domain` is `'p1'` and this is `None`.
        @param x_domain The time domain actually plotted on the X axis: `p1` (covers both relative and absolute P1
               time) or `gps` (covers both GPS and UTC). Defaults to @ref _default_x_domain; only needs to be passed
               explicitly by plots (e.g., @ref plot_time_scale()) whose X axis doesn't follow @c self.time_type.

        @return A customdata array suitable for `go.Scattergl(..., customdata=...)`.
        """
        if x_domain is None:
            x_domain = self._default_x_domain

        if x_domain == 'p1':
            if gps_time is None:
                gps_time = self.time_provider.p1_to_gps(p1_time)
            return np.vstack((gps_time,))
        else:
            return np.vstack((p1_time,))

    def _custom_tooltip_js(self, time_source: str = 'p1', precision: Optional[int] = 3,
                           value_label: Optional[str] = None, show_name: bool = True, show_value: bool = True) -> str:
        """!
        @brief Build hover JS that draws its own tooltip instead of relying on Plotly's native hover label (see
               `ShowCustomTooltip()`/`HideCustomTooltip()` in `plotly_data_support.js`).

        Unlike @ref _TIME_HOVER_JS/@ref _SYSTEM_TIME_HOVER_JS (which mutate `fullData.text` for Plotly's own hover
        label to pick up on its next render), this draws synchronously inside the `'plotly_hover'` handler itself,
        avoiding the race that can otherwise leave the native label blank or stale on plots with many traces/points
        (see @ref plot_gnss_cn0()). Only supports the single-nearest-point case (the default `'closest'` hovermode),
        not `'x'`/`'x unified'`.

        @param time_source The native time domain of the data being plotted, as in @ref _x_axis_layout(): `p1` (the
               default -- P1/relative/GPS/UTC, per @c self.time_type; requires the trace's customdata to be set per
               @ref _time_hover_customdata()) or `system` (device system time; no customdata needed).
        @param precision Number of digits after the decimal point to show for the Y value (see
               `BuildAxisValueHoverText()`).
        @param value_label Override label to show instead of the Y axis title (see `BuildAxisValueHoverText()`).
        @param show_name Show trace names in the tooltip.
        @param show_value Show trace values in the tooltip.

        @return The JS to pass as `inject_js` to @ref _add_figure().
        """
        if time_source == 'p1':
            build_time_text_js = (
                '  let time_text = point.data.customdata ? '
                'BuildTimeHoverText(point.x, GetCustomData(point, 0)) : BuildTimeHoverText(point.x);')
            tick_reformat_js = self._GPS_TICK_REFORMAT_JS
        elif time_source == 'system':
            build_time_text_js = '  let time_text = BuildSystemTimeHoverText(point.x);'
            tick_reformat_js = ''
        else:
            raise ValueError(f"Unsupported time source '{time_source}'.")

        # Room to grow: additional BuildAxisValueHoverText() options can be added here as more callers need them.
        value_options = {}
        if precision is not None:
            value_options['precision'] = precision
        if value_label is not None:
            value_options['label'] = value_label

        name_arg = 'point.data.name' if show_name else 'undefined'
        if show_value:
            value_text_js = f'  let value_text = BuildAxisValueHoverText(point, {json.dumps(value_options)});'
            value_arg = 'value_text'
        else:
            value_text_js = ''
            value_arg = 'undefined'

        return ("""\
figure.on('plotly_hover', function(data) {
  let point = data.points[0];
""" + build_time_text_js + "\n" + value_text_js + """
  ShowCustomTooltip(point, GetCustomTooltipHTML(""" + name_arg + ", " + value_arg + """, time_text));
});
figure.on('plotly_unhover', function(data) {
  HideCustomTooltip();
});
""" + tick_reformat_js)

    def _auto_detect_message_type(self, types: List[MessageType]):
        types = [t.MESSAGE_TYPE if inspect.isclass(t) else t for t in types]

        params = copy.deepcopy(self.params)
        params['max_messages'] = 1
        selected_type = None
        for message_type in types:
            result = self.reader.read(message_types=message_type, remove_nan_times=False, **params)
            data = result[message_type]
            if len(data.p1_time) > 0:
                selected_type = message_type_to_class[message_type]
                break
        return selected_type

    @classmethod
    def _gps_sec_to_string(cls, gps_time_sec, is_approx: bool = False):
        if isinstance(gps_time_sec, Timestamp):
            gps_time_sec = float(gps_time_sec)

        if gps_time_sec is None or np.isnan(gps_time_sec):
            return "GPS: N/A<br>UTC: N/A"
        else:
            week = int(gps_time_sec / SECONDS_PER_WEEK)
            tow_sec = gps_time_sec - week * SECONDS_PER_WEEK
            utc_time = gpstime.fromgps(gps_time_sec)
            approx_str = ' (approximated)' if is_approx else ''
            return "GPS: %d:%.3f (%.3f sec)%s<br>UTC: %s%s" %\
                   (week, tow_sec, gps_time_sec, approx_str,
                    datetime_to_string(utc_time, decimals=3), approx_str)

    @classmethod
    def _get_measurement_time(cls, data, time_source: SystemTimeSource) -> np.ndarray:
        if time_source == SystemTimeSource.P1_TIME:
            return data.p1_time
        else:
            return data.measurement_time

    @classmethod
    def _time_source_to_display_name(cls, time_source: SystemTimeSource) -> str:
        if time_source == SystemTimeSource.P1_TIME:
            return 'P1'
        elif time_source == SystemTimeSource.GPS_TIME:
            return 'GPS'
        elif time_source == SystemTimeSource.SENDER_SYSTEM_TIME:
            return 'External'
        elif time_source == SystemTimeSource.TIMESTAMPED_ON_RECEPTION:
            return 'System'

    @classmethod
    def _get_colors(cls, num_colors=None):
        colors = Tableau_20.hex_colors
        if num_colors is None:
            return colors
        elif num_colors <= len(colors):
            return colors[:num_colors]
        else:
            num_repeats = int(num_colors / len(colors))
            num_extra = num_colors % len(colors)
            return colors * num_repeats + colors[:num_extra]

    @classmethod
    def _assign_colors(cls, elements, num_colors=None):
        colors = cls._get_colors(num_colors)
        return {e: colors[i % len(colors)] for i, e in enumerate(elements)}


def main(args=None):
    parser = ArgumentParser(description="""\
Load and display information stored in a FusionEngine binary file.
""")

    plot_group = parser.add_argument_group('Plot Control')
    plot_group.add_argument(
        '--displacement-type', '--displacement', choices=_OWN_LOG_STATISTICS, default='median_fixed',
        help="Specify the position statistic to use as a reference for plotting position displacement:"
             "\n- first - Use the first-available pose solution"
             "\n- first_fixed - Use the first RTK-fixed pose solution"
             "\n- median - Use the median pose solution across the entire log"
             "\n- median_fixed - Use the median pose solution only when RTK-fixed")
    plot_group.add_argument('--mapbox-token', metavar='TOKEN',
        help="A Mapbox token to use for satellite imagery when generating a map. If unspecified, the token will be "
             "read from the MAPBOX_ACCESS_TOKEN or MapboxAccessToken environment variables if set. If no token is "
             "available, a default map will be displayed using Open Street Maps data.")
    plot_group.add_argument(
        '-m', '--measurements', action=ExtendedBooleanAction,
        help="Plot incoming measurement data (slow). Ignored if --plot is specified.")
    plot_group.add_argument(
        '--time-type', choices=('utc', 'gps', 'p1', 'relative'), default='utc',
        help="Specify the way in which time will be plotted:"
             "\n- utc - UTC date/time, if available (falls back to P1 time otherwise)"
             "\n- gps - GPS time (week and time of week), if available (falls back to P1 time otherwise)"
             "\n- p1 - Absolute P1 (or system) time"
             "\n- relative - Elapsed time since the start of the log")
    plot_group.add_argument(
        '--time-axis', choices=('absolute', 'abs', 'relative', 'rel'), default=None,
        help="Deprecated. Use --time-type instead. If specified, overrides --time-type:"
             "\n- absolute, abs - Equivalent to --time-type=utc"
             "\n- relative, rel - Equivalent to --time-type=relative")
    plot_group.add_argument(
        '--truncate', '--trunc', action=ExtendedBooleanAction, default=True,
        help="When processing a very long log (>%.1f hours), reduce or skip some plots that may be very slow to "
             "generate or display. This includes:"
             "\n- GNSS signal status display"
             "\n- High-rate (>%d Hz) measurement data"
             "\n"
             "\nTruncation is disabled if --plot is specified." %
             (Analyzer.LONG_LOG_DURATION_SEC / 3600.0, Analyzer.HIGH_MEASUREMENT_RATE_HZ))
    plot_group.add_argument(
        '--reference', '--truth',
        help="Specify reference data to use as a truth source, or as an alternate reference, for position "
             "displacement/error plots. Supported formats:"
             "\n- The path to a separate log file, or a log hash/pattern to be located under --log-base-dir, whose "
             "pose data will be used as a time-varying truth reference"
             "\n- A stationary LLA (degrees, degrees, meters) or ECEF (meters) position, as 3 comma-separated values. "
             "All spaces will be ignored."
             "\n  - 37.1234, -122.526335, 102.34"
             "\n  - lla: 37.1234, -122.526335, 102.34"
             "\n  - -2707071.0, -4321671.7, 3817403.2"
             "\n  - ecef: -2707071.0, -4321671.7, 3817403.2")
    plot_group.add_argument(
        '--reference-log-type', metavar='TYPE', default='auto',
        help="If --reference specifies a separate log file/hash, the type of log data to load from it. See "
             "--log-type for supported values.")

    plot_function_names = [n for n in dir(Analyzer) if n.startswith('plot_')]
    plot_group.add_argument(
        '--plot', action=CSVAction, nargs='*',
        help="The names of names of plots to be displayed. May be specified multiple times (--plot map --plot events)"
             "or as a comma-separated list (--plot map,events). If not specified, plots will be generated based on the "
             "data present in the log.\n"
             "\n"
             "If a partial name is specified, the best matching plot will be generated (e.g., 'sky' will match"
             "'gnss_skyplot'). Use the wildcard '*' to match multiple plots.\n"
             "\n"
             "Options include:%s" %
             ''.join(['\n- %s' % f[5:] for f in plot_function_names]))

    plot_group.add_argument(
        '--source-identifier', '--source-id', action=CSVAction, nargs='*',
        help="Plot the FusionEngine Pose messages with the listed source identifier(s). Must be integers. May be "
             "specified multiple times (--source-id 0 --source-id 1), as a space-separated list (--source-id 0 1), or "
             "as a comma-separated list (--source-id 0,1). If not specified, all available source identifiers present "
             "in the log will be used.")

    time_group = parser.add_argument_group('Time Control')
    time_group.add_argument(
        '--absolute-time', '--abs', action=ExtendedBooleanAction,
        help="Interpret the timestamps in --time as absolute P1 times. Otherwise, treat them as relative to the first "
             "message in the file. Ignored if --time contains a type specifier.")
    time_group.add_argument(
        '-t', '--time', type=str, metavar='[START][:END][:{rel,abs}]',
        help="The desired time range to be analyzed. Both start and end may be omitted to read from beginning or to "
             "the end of the file. By default, timestamps are treated as relative to the first message in the file, "
             "unless an 'abs' type is specified or --absolute-time is set.")

    log_group = parser.add_argument_group('Input File/Log Control')
    define_log_search_arguments(log_group)

    output_group = parser.add_argument_group('Output Control')
    output_group.add_argument(
        '--no-index', action=ExtendedBooleanAction,
        help="Do not automatically open the plots in a web browser.")
    output_group.add_argument(
        '-o', '--output', type=str, metavar='DIR',
        help="The directory where output will be stored. Defaults to the current directory, or to "
              "'<log_dir>/plot_fusion_engine/' if reading from a log.")
    output_group.add_argument(
        '-p', '--prefix', metavar='PREFIX',
        help="If specified, prepend each filename with PREFIX.")
    output_group.add_argument(
        '-v', '--verbose', action='count', default=0,
        help="Print verbose/trace debugging messages.")

    options = parser.parse_args(args=args)

    # Configure logging.
    if options.verbose >= 1:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s:%(lineno)d - %(message)s',
                            stream=sys.stdout)
        if options.verbose == 1:
            logging.getLogger('point_one.fusion_engine').setLevel(logging.DEBUG)
        else:
            logging.getLogger('point_one.fusion_engine').setLevel(logging.getTraceLevel(depth=options.verbose - 1))
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s', stream=sys.stdout)

    HighlightFormatter.install(color=True, standoff_level=logging.WARNING)

    # Parse the time range.
    if options.time is not None:
        time_range = TimeRange.parse(options.time, absolute=options.absolute_time)
    else:
        time_range = None

    # Locate the input file and set the output directory.
    input_path, log_dir, log_id = locate_log(input_path=options.log, log_base_dir=options.log_base_dir,
                                             return_output_dir=True, return_log_id=True)
    if input_path is None:
        # locate_log() will log an error.
        sys.exit(1)

    if log_id is None:
        _logger.info('Loading %s.' % input_path)
    else:
        _logger.info('Loading %s (log ID: %s).' % (input_path, log_id))

    if options.output is None:
        output_dir = os.path.join(log_dir, 'plot_fusion_engine')
    else:
        output_dir = options.output

    if options.source_identifier is None:
        source_id = None
    else:
        try:
            source_id = [int(s) for s in options.source_identifier]
        except ValueError:
            _logger.error('Source identifiers must be integers. Exiting.')
            sys.exit(1)

    # --time-axis is deprecated in favor of --time-type, but still accepted for backwards compatibility.
    time_type = options.time_type
    if options.time_axis is not None:
        if options.time_axis in ('relative', 'rel'):
            time_type = 'relative'
        elif options.time_axis in ('absolute', 'abs'):
            time_type = 'utc'

    # Read pose data from the file.
    analyzer = Analyzer(file=input_path, output_dir=output_dir, ignore_index=options.ignore_index,
                        prefix=options.prefix + '.' if options.prefix is not None else '',
                        time_range=time_range, time_type=time_type,
                        truncate_long_logs=options.truncate and options.plot is None, source_id=source_id)

    # Resolve reference data, if specified. This must happen after the analyzer (and its DataLoader) for the primary
    # log is constructed since some reference types (e.g., 'median') are derived from the primary log's own data.
    if options.reference is None:
        ref_path = os.path.join(log_dir, 'reference.p1log')
        if os.path.exists(ref_path):
            options.reference = ref_path

    reference_data = None
    if options.reference is not None:
        reference_data = ReferenceData.resolve_cli_argument(
            options.reference, loader=analyzer.reader, log_base_dir=options.log_base_dir,
            log_type=options.reference_log_type, source_id=analyzer.default_source_id)
        if reference_data is None:
            _logger.error('Unable to resolve reference data.')
            sys.exit(1)

    if options.plot is None:
        analyzer.plot_events()
        analyzer.plot_time_scale()
        analyzer.plot_latency()

        analyzer.plot_solution_type()
        analyzer.plot_stationary_status()
        analyzer.plot_reset_timing()
        analyzer.plot_pose()
        analyzer.plot_position_displacement(reference_type=options.displacement_type)
        analyzer.plot_relative_position()
        analyzer.plot_map(mapbox_token=options.mapbox_token)
        analyzer.plot_calibration()

        if reference_data is not None:
            analyzer.plot_pose_error(reference=reference_data)

        analyzer.plot_gnss_cn0()
        analyzer.plot_gnss_signal_status()
        analyzer.plot_gnss_skyplot()
        analyzer.plot_gnss_azimuth_elevation()
        analyzer.clear_gnss_signal_data_cache()

        analyzer.plot_gnss_corrections_status()
        analyzer.plot_dop()

        # By default, we always plot attitude measurements (i.e., output from a secondary GNSS attitude sensor like an
        # LG69T-AH), separate from other sensor measurements controlled by --measurements.
        analyzer.plot_gnss_attitude_measurements()

        if options.measurements:
            analyzer.plot_imu()
            analyzer.plot_wheel_data()

        analyzer.plot_system_status_profiling()
    else:
        if len(options.plot) == 0:
            _logger.error('No plot names specified.')
            sys.exit(1)

        # Convert the user patterns into regex. The user is allowed to specify wildcards to match multiple figures.
        functions = set()
        for name in options.plot:
            pattern = r'plot_.*%s.*' % name.replace('*', '.*')
            allow_multiple = '*' in name

            funcs = [f for f in plot_function_names if re.match(pattern, f)]
            if len(funcs) == 0:
                _logger.error("Unrecognized plot pattern '%s'." % name)
                sys.exit(1)
            elif len(funcs) > 1 and not allow_multiple:
                _logger.error("Pattern '%s' matches multiple plots:%s\n\nAdd a wildcard (%s*) to display all matching "
                              "plots." %
                              (name, ''.join(['\n  %s' % f[5:] for f in funcs]), name))
                sys.exit(1)
            else:
                functions.update(funcs)

        for func in functions:
            if func == 'plot_map':
                analyzer.plot_map(mapbox_token=options.mapbox_token)
            elif func == 'plot_skyplot':
                analyzer.plot_gnss_skyplot(decimate=False)
            elif func == 'plot_pose_error':
                if reference_data is not None:
                    analyzer.plot_pose_error(reference_data)
                else:
                    _logger.warning('No reference data available. Cannot plot position error.')
            elif func == 'plot_position_displacement':
                analyzer.plot_position_displacement(reference_type=options.displacement_type)
            else:
                getattr(analyzer, func)()

    analyzer.generate_index(reference=reference_data, auto_open=not options.no_index)

    _logger.info("Output stored in '%s'." % os.path.abspath(output_dir))
    return analyzer

if __name__ == "__main__":
    main()
