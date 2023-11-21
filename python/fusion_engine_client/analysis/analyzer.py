#!/usr/bin/env python3

from typing import Tuple, Union, List, Any

from collections import namedtuple, defaultdict
import copy
import inspect
import os
import sys
import webbrowser

from gpstime import gpstime
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
from .attitude import get_enu_rotation_matrix
from .data_loader import DataLoader, TimeRange
from ..utils import trace as logging
from ..utils.argument_parser import ArgumentParser, ExtendedBooleanAction, TriStateBooleanAction, CSVAction
from ..utils.log import locate_log, DEFAULT_LOG_BASE_DIR
from ..utils.numpy_utils import find_first
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
    SolutionType.Visual: SolutionTypeInfo(name='Vision', style={'color': 'purple'}),
}


def _data_to_table(col_titles: List[str], values: List[List[Any]], row_major: bool = False):
    if row_major:
        # If values is row major (outer index is the table rows), transpose it.
        col_values = list(map(list, zip(*values)))
    else:
        col_values = values

    table_html = '''\
<table>
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

    def __init__(self,
                 file: Union[DataLoader, str], ignore_index: bool = False,
                 output_dir: str = None, prefix: str = '',
                 time_range: TimeRange = None, max_messages: int = None,
                 time_axis: str = 'relative',
                 truncate_long_logs: bool = True):
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
        @param time_axis Specify the way in which time will be plotted:
               - `absolute`, `abs` - Absolute P1 or system timestamps
               - `relative`, `rel` - Elapsed time since the start of the log
        @param truncate_long_logs If `True`, reduce or skip certain plots if the log extremely long (as defined by
               @ref LONG_LOG_DURATION_SEC).
        """
        if isinstance(file, str):
            self.reader = DataLoader(file, ignore_index=ignore_index)
        else:
            self.reader = file

        self.output_dir = output_dir
        self.prefix = prefix

        self.params = {
            'time_range': time_range,
            'max_messages': max_messages,
            'show_progress': True,
            'return_numpy': True
        }

        if time_axis in ('relative', 'rel'):
            self.time_axis = 'relative'
            self.t0 = self.reader.t0
            if self.t0 is None:
                self.t0 = Timestamp()

            self.system_t0 = self.reader.get_system_t0()
            if self.system_t0 is None:
                self.system_t0 = np.nan

            self.p1_time_label = 'Relative Time (sec)'
            self.system_time_label = 'Relative Time (sec)'
        elif time_axis in ('absolute', 'abs'):
            self.time_axis = 'absolute'
            self.t0 = Timestamp(0.0)
            self.system_t0 = 0.0
            self.p1_time_label = 'P1 Time (sec)'
            self.system_time_label = 'System Time (sec)'
        else:
            raise ValueError(f"Unsupported time axis specifier '{time_axis}'.")

        self.plots = {}
        self.summary = ''

        self._mapbox_token_missing = False

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

        # Setup the figure.
        time_axis_str = 'Relative Time' if self.time_axis == 'relative' else 'P1/System Time'
        p1_time_axis_str = 'Relative Time' if self.time_axis == 'relative' else 'P1 Time'
        figure = make_subplots(rows=2, cols=1, print_grid=False, shared_xaxes=True,
                               subplot_titles=[f'Device Time vs. {time_axis_str}',
                                               f'Pose Message Interval vs. {p1_time_axis_str}'])

        figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'])
        figure['layout']['xaxis1'].update(title=f"{time_axis_str} (sec)", showticklabels=True)
        figure['layout']['xaxis2'].update(title=f"{p1_time_axis_str} (sec)", showticklabels=True)
        figure['layout']['yaxis1'].update(title="Absolute Time",
                                          ticktext=['P1/GPS Time', 'System Time'],
                                          tickvals=[1, 2])
        figure['layout']['yaxis2'].update(title="Interval (sec)", rangemode="tozero")

        # Read the pose data to get P1 and GPS timestamps.
        result = self.reader.read(message_types=[PoseMessage], **self.params)
        pose_data = result[PoseMessage.MESSAGE_TYPE]

        if len(pose_data.p1_time) > 0:
            time = pose_data.p1_time - float(self.t0)

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

            text = ['P1: %.3f sec<br>%s' % (p, self._gps_sec_to_string(g)) for p, g in zip(p1_time, gps_time)]
            figure.add_trace(go.Scattergl(x=time, y=np.full_like(time, 1), name='P1/GPS Time', text=text,
                                          hoverlabel={'namelength': -1},
                                          mode='markers', marker={'color': 'blue'}),
                             1, 1)

            figure.add_trace(go.Scattergl(x=time, y=dp1_time, name='P1 Time Interval', text=text,
                                          hoverlabel={'namelength': -1},
                                          mode='markers', marker={'color': 'red'}),
                             2, 1)
            if dp1_stats is not None:
                figure.add_trace(go.Scattergl(x=time, y=dp1_stats['max'], name='P1 Time Interval (Max)',
                                              hoverlabel={'namelength': -1},
                                              mode='markers', marker={'symbol': 'triangle-up-open'}),
                                 2, 1)
                figure.add_trace(go.Scattergl(x=time, y=dp1_stats['min'], name='P1 Time Interval (Min)',
                                              hoverlabel={'namelength': -1},
                                              mode='markers', marker={'symbol': 'triangle-down-open'}),
                                 2, 1)

            figure.add_trace(go.Scattergl(x=time, y=dgps_time, name='GPS Time Interval', text=text,
                                          hoverlabel={'namelength': -1},
                                          mode='markers', marker={'color': 'green'}),
                             2, 1)
            if dgps_stats is not None:
                figure.add_trace(go.Scattergl(x=time, y=dgps_stats['max'], name='GPS Time Interval (Max)',
                                              hoverlabel={'namelength': -1},
                                              mode='markers', marker={'symbol': 'triangle-up-open'}),
                                 2, 1)
                figure.add_trace(go.Scattergl(x=time, y=dgps_stats['min'], name='GPS Time Interval (Min)',
                                              hoverlabel={'namelength': -1},
                                              mode='markers', marker={'symbol': 'triangle-down-open'}),
                                 2, 1)

        # Read system timestamps from event notifications, if present.
        result = self.reader.read(message_types=[EventNotificationMessage], **self.params)
        event_data = result[EventNotificationMessage.MESSAGE_TYPE]

        system_time_sec = None
        if len(event_data.messages) > 0:
            system_time_sec = np.array([(m.system_time_ns * 1e-9) for m in event_data.messages])

        if system_time_sec is not None:
            time = system_time_sec - self.system_t0

            # plotly starts to struggle with > 2 hours of data and won't display mouseover text, so decimate if
            # necessary.
            dt_sec = time[-1] - time[0]
            if dt_sec > 7200.0:
                step = math.ceil(dt_sec / 7200.0)
                idx = np.full_like(time, False, dtype=bool)
                idx[0::step] = True

                time = time[idx]
                system_time_sec = system_time_sec[idx]

            text = ['System: %.3f sec' % t for t in system_time_sec]
            figure.add_trace(go.Scattergl(x=time, y=np.full_like(time, 2), name='System Time', text=text,
                                          hoverlabel={'namelength': -1},
                                          mode='markers', marker={'color': 'purple'}),
                             1, 1)

        self._add_figure(name="time_scale", figure=figure, title="Time Scale")

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

        figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'])
        figure['layout']['xaxis1'].update(title=self.system_time_label, showticklabels=True)
        figure['layout']['yaxis1'].update(title="Elapsed Time (sec)", rangemode="tozero")

        time = reset_system_time_sec - self.system_t0

        text = ["System Time: %.3f sec" % (t + self.system_t0) for t in time]
        figure.add_trace(go.Scattergl(x=time, y=dt_reset_to_valid, text=text,
                                      name='Command -> Valid', hoverlabel={'namelength': -1},
                                      mode='markers'),
                         1, 1)
        figure.add_trace(go.Scattergl(x=time, y=dt_reset_to_invalid, text=text,
                                      name='Command -> Invalid', hoverlabel={'namelength': -1},
                                      mode='markers'),
                         1, 1)
        figure.add_trace(go.Scattergl(x=time, y=dt_invalid_to_valid, text=text,
                                      name='Invalid -> Valid', hoverlabel={'namelength': -1},
                                      mode='markers'),
                         1, 1)

        if len(unstarted_resets) > 0:
            idx = np.array(unstarted_resets)
            time = time[idx]
            text = ["System Time: %.3f sec" % (t + self.system_t0) for t in time]
            figure.add_trace(go.Scattergl(x=time, y=np.zeros_like(time), text=text,
                                          name='Unstarted Resets', hoverlabel={'namelength': -1},
                                          mode='markers'),
                             1, 1)

        self._add_figure(name="reset_timing", figure=figure, title="Reset Recovery Timing")

    def plot_pose(self):
        """!
        @brief Plot position/attitude solution data.
        """
        if self.output_dir is None:
            return

        # Read the pose data.
        result = self.reader.read(message_types=[PoseMessage], **self.params)
        pose_data = result[PoseMessage.MESSAGE_TYPE]

        if len(pose_data.p1_time) == 0:
            self.logger.info('No pose data available. Skipping pose vs. time plot.')
            return

        time = pose_data.p1_time - float(self.t0)

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
            figure['layout']['xaxis%d' % (i + 1)].update(title=self.p1_time_label, showticklabels=True, matches='x')
        figure['layout']['yaxis1'].update(title="Degrees")
        figure['layout']['yaxis2'].update(title="Meters")
        figure['layout']['yaxis3'].update(title="Meters/Second")
        figure['layout']['yaxis4'].update(title="Degrees")
        figure['layout']['yaxis5'].update(title="Meters")
        figure['layout']['yaxis6'].update(title="Meters/Second")

        # Plot YPR.
        figure.add_trace(go.Scattergl(x=time, y=pose_data.ypr_deg[0, :], name='Yaw', legendgroup='yaw',
                                      mode='lines', line={'color': 'red'}),
                         1, 1)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.ypr_deg[1, :], name='Pitch', legendgroup='pitch',
                                      mode='lines', line={'color': 'green'}),
                         1, 1)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.ypr_deg[2, :], name='Roll', legendgroup='roll',
                                      mode='lines', line={'color': 'blue'}),
                         1, 1)

        figure.add_trace(go.Scattergl(x=time, y=pose_data.ypr_std_deg[0, :], name='Yaw', legendgroup='yaw',
                                      showlegend=False, mode='lines', line={'color': 'red'}),
                         2, 1)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.ypr_std_deg[1, :], name='Pitch', legendgroup='pitch',
                                      showlegend=False, mode='lines', line={'color': 'green'}),
                         2, 1)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.ypr_std_deg[2, :], name='Roll', legendgroup='roll',
                                      showlegend=False, mode='lines', line={'color': 'blue'}),
                         2, 1)

        # Plot position/displacement.
        position_ecef_m = np.array(geodetic2ecef(lat=pose_data.lla_deg[0, :], lon=pose_data.lla_deg[1, :],
                                                 alt=pose_data.lla_deg[0, :], deg=True))
        displacement_ecef_m = position_ecef_m - position_ecef_m[:, first_idx].reshape(3, 1)
        displacement_enu_m = c_enu_ecef.dot(displacement_ecef_m)
        figure.add_trace(go.Scattergl(x=time, y=displacement_enu_m[0, :], name='East', legendgroup='e',
                                      mode='lines', line={'color': 'red'}),
                         1, 2)
        figure.add_trace(go.Scattergl(x=time, y=displacement_enu_m[1, :], name='North', legendgroup='n',
                                      mode='lines', line={'color': 'green'}),
                         1, 2)
        figure.add_trace(go.Scattergl(x=time, y=displacement_enu_m[2, :], name='Up', legendgroup='u',
                                      mode='lines', line={'color': 'blue'}),
                         1, 2)

        figure.add_trace(go.Scattergl(x=time, y=pose_data.position_std_enu_m[0, :], name='East', legendgroup='e',
                                      showlegend=False, mode='lines', line={'color': 'red'}),
                         2, 2)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.position_std_enu_m[1, :], name='North', legendgroup='n',
                                      showlegend=False, mode='lines', line={'color': 'green'}),
                         2, 2)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.position_std_enu_m[2, :], name='Up', legendgroup='u',
                                      showlegend=False, mode='lines', line={'color': 'blue'}),
                         2, 2)

        # Plot velocity.
        figure.add_trace(go.Scattergl(x=time, y=pose_data.velocity_body_mps[0, :], name='X', legendgroup='x',
                                      mode='lines', line={'color': 'red'}),
                         1, 3)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.velocity_body_mps[1, :], name='Y', legendgroup='y',
                                      mode='lines', line={'color': 'green'}),
                         1, 3)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.velocity_body_mps[2, :], name='Z', legendgroup='z',
                                      mode='lines', line={'color': 'blue'}),
                         1, 3)

        figure.add_trace(go.Scattergl(x=time, y=pose_data.velocity_std_body_mps[0, :], name='X', legendgroup='x',
                                      showlegend=False, mode='lines', line={'color': 'red'}),
                         2, 3)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.velocity_std_body_mps[1, :], name='Y', legendgroup='y',
                                      showlegend=False, mode='lines', line={'color': 'green'}),
                         2, 3)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.velocity_std_body_mps[2, :], name='Z', legendgroup='z',
                                      showlegend=False, mode='lines', line={'color': 'blue'}),
                         2, 3)

        self._add_figure(name="pose", figure=figure, title="Vehicle Pose vs. Time")

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

        time = cal_data.p1_time - float(self.t0)
        text = ["Time: %.3f sec (%.3f sec)" % (t, t + float(self.t0)) for t in time]

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
            figure['layout']['xaxis%d' % (i + 1)].update(title=self.p1_time_label, showticklabels=True)
        figure['layout']['yaxis1'].update(title="Percent Complete", range=[0, 100])
        figure['layout']['yaxis2'].update(ticktext=['%s' % e.name for e in CalibrationStage],
                                          tickvals=list(range(len(stage_map))))
        figure['layout']['yaxis3'].update(title="Degrees")
        figure['layout']['yaxis4'].update(title="Degrees")
        figure['layout']['yaxis5'].update(title="Meters")

        # Plot calibration stage and completion percentages.
        figure.add_trace(go.Scattergl(x=time, y=cal_data.gyro_bias_percent_complete, text=text,
                                      name='Gyro Bias Completion', hoverlabel={'namelength': -1},
                                      mode='lines', line={'color': 'red'}),
                         1, 1)
        figure.add_trace(go.Scattergl(x=time, y=cal_data.accel_bias_percent_complete, text=text,
                                      name='Accel Bias Completion', hoverlabel={'namelength': -1},
                                      mode='lines', line={'color': 'green'}),
                         1, 1)
        figure.add_trace(go.Scattergl(x=time, y=cal_data.mounting_angle_percent_complete, text=text,
                                      name='Mounting Angle Completion', hoverlabel={'namelength': -1},
                                      mode='lines', line={'color': 'blue'}),
                         1, 1)

        figure.add_trace(go.Scattergl(x=time, y=calibration_stage, name='Stage', text=text,
                                      mode='lines', line={'color': 'black', 'dash': 'dash'}),
                         1, 1, secondary_y=True)

        # Plot mounting angles.
        figure.add_trace(go.Scattergl(x=time, y=cal_data.ypr_deg[0, :], name='Yaw', legendgroup='y', text=text,
                                      mode='lines', line={'color': 'red'}),
                         2, 1)
        figure.add_trace(go.Scattergl(x=time, y=cal_data.ypr_deg[1, :], name='Pitch', legendgroup='p', text=text,
                                      mode='lines', line={'color': 'green'}),
                         2, 1)
        figure.add_trace(go.Scattergl(x=time, y=cal_data.ypr_deg[2, :], name='Roll', legendgroup='r', text=text,
                                      mode='lines', line={'color': 'blue'}),
                         2, 1)

        figure.add_trace(go.Scattergl(x=time, y=cal_data.ypr_std_dev_deg[0, :], name='Yaw Std Dev', legendgroup='y',
                                      text=text, mode='lines', line={'color': 'red'}, hoverlabel={'namelength': -1}),
                         3, 1)
        figure.add_trace(go.Scattergl(x=time, y=cal_data.ypr_std_dev_deg[1, :], name='Pitch Std Dev', legendgroup='p',
                                      text=text, mode='lines', line={'color': 'green'}, hoverlabel={'namelength': -1}),
                         3, 1)
        figure.add_trace(go.Scattergl(x=time, y=cal_data.ypr_std_dev_deg[2, :], name='Roll Std Dev', legendgroup='r',
                                      text=text, mode='lines', line={'color': 'blue'}, hoverlabel={'namelength': -1}),
                         3, 1)

        thresh_time = time[np.array((0, -1))]
        figure.add_trace(go.Scattergl(x=thresh_time, y=[cal_data.mounting_angle_max_std_dev_deg[0]] * 2,
                                      name='Max Yaw Std Dev', legendgroup='y', hoverlabel={'namelength': -1},
                                      mode='lines', line={'color': 'red', 'dash': 'dash'}),
                         3, 1)
        figure.add_trace(go.Scattergl(x=thresh_time, y=[cal_data.mounting_angle_max_std_dev_deg[1]] * 2,
                                      name='Max Pitch Std Dev', legendgroup='p', hoverlabel={'namelength': -1},
                                      text=text, mode='lines', line={'color': 'green', 'dash': 'dash'}),
                         3, 1)
        figure.add_trace(go.Scattergl(x=thresh_time, y=[cal_data.mounting_angle_max_std_dev_deg[2]] * 2,
                                      name='Max Roll Std Dev', legendgroup='r', hoverlabel={'namelength': -1},
                                      text=text, mode='lines', line={'color': 'blue', 'dash': 'dash'}),
                         3, 1)

        # Plot travel distance.
        figure.add_trace(go.Scattergl(x=time, y=cal_data.travel_distance_m, name='Travel Distance', text=text,
                                      mode='lines', line={'color': 'blue'}, hoverlabel={'namelength': -1}),
                         4, 1)
        figure.add_trace(go.Scattergl(x=thresh_time, y=[cal_data.min_travel_distance_m] * 2,
                                      name='Min Travel Distance', text=text, hoverlabel={'namelength': -1},
                                      mode='lines', line={'color': 'black', 'dash': 'dash'}),
                         4, 1)

        self._add_figure(name="calibration", figure=figure, title="Calibration Status")

    def plot_solution_type(self):
        """!
        @brief Plot the solution type over time.
        """
        if self.output_dir is None:
            return

        # Read the pose data.
        result = self.reader.read(message_types=[PoseMessage], **self.params)
        pose_data = result[PoseMessage.MESSAGE_TYPE]

        if len(pose_data.p1_time) == 0:
            self.logger.info('No pose data available. Skipping solution type plot.')
            return

        # Setup the figure.
        figure = make_subplots(rows=1, cols=1, print_grid=False, shared_xaxes=True, subplot_titles=['Solution Type'])

        figure['layout']['xaxis'].update(title=self.p1_time_label)
        figure['layout']['yaxis1'].update(title="Solution Type",
                                          ticktext=['%s (%d)' % (e.name, e.value) for e in SolutionType],
                                          tickvals=[e.value for e in SolutionType])

        time = pose_data.p1_time - float(self.t0)

        text = ["Time: %.3f sec (%.3f sec)" % (t, t + float(self.t0)) for t in time]
        figure.add_trace(go.Scattergl(x=time, y=pose_data.solution_type, text=text, mode='markers'), 1, 1)

        self._add_figure(name="solution_type", figure=figure, title="Solution Type")

    def _plot_displacement(self, source, time, solution_type, displacement_enu_m, std_enu_m):
        """!
        @brief Generate a topocentric (top-down) plot of position displacement, as well as plot of displacement over
               time.
        """
        if self.output_dir is None:
            return

        # Setup the figure.
        topo_figure = make_subplots(rows=1, cols=1, print_grid=False, shared_xaxes=False,
                                    subplot_titles=['Displacement'])
        topo_figure['layout']['xaxis1'].update(title="East (m)")
        topo_figure['layout']['yaxis1'].update(title="North (m)")

        time_figure = make_subplots(rows=4, cols=1, print_grid=False, shared_xaxes=True,
                                    subplot_titles=['3D', 'East', 'North', 'Up'])
        time_figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'])
        for i in range(4):
            time_figure['layout']['xaxis%d' % (i + 1)].update(title=self.p1_time_label, showticklabels=True)
        time_figure['layout']['yaxis1'].update(title="Displacement (m)")
        time_figure['layout']['yaxis2'].update(title="Displacement (m)")
        time_figure['layout']['yaxis3'].update(title="Displacement (m)")
        time_figure['layout']['yaxis4'].update(title="Displacement (m)")

        # Remove invalid solutions.
        valid_idx = np.logical_and(~np.isnan(time), solution_type != SolutionType.Invalid)
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
        def _plot_data(name, idx, marker_style=None):
            style = {'mode': 'markers', 'marker': {'size': 8}, 'showlegend': True, 'legendgroup': name,
                     'hoverlabel': {'namelength': -1}}
            if marker_style is not None:
                style['marker'].update(marker_style)

            if np.any(idx):
                text = ["Time: %.3f sec (%.3f sec)<br>Delta (ENU): (%.2f, %.2f, %.2f) m" \
                        "<br>Std (ENU): (%.2f, %.2f, %.2f) m" %
                        (t, t + float(self.t0), *delta, *std)
                        for t, delta, std in zip(time[idx], displacement_enu_m[:, idx].T, std_enu_m[:, idx].T)]
                topo_figure.add_trace(go.Scattergl(x=displacement_enu_m[0, idx], y=displacement_enu_m[1, idx],
                                                   name=name, text=text, **style), 1, 1)

                time_figure.add_trace(go.Scattergl(x=time[idx], y=np.linalg.norm(displacement_enu_m[:, idx], axis=0),
                                                   name=name, text=text, **style), 1, 1)
                style['showlegend'] = False
                time_figure.add_trace(go.Scattergl(x=time[idx], y=displacement_enu_m[0, idx], name=name,
                                                   text=text, **style), 2, 1)
                time_figure.add_trace(go.Scattergl(x=time[idx], y=displacement_enu_m[1, idx], name=name,
                                                   text=text, **style), 3, 1)
                time_figure.add_trace(go.Scattergl(x=time[idx], y=displacement_enu_m[2, idx], name=name,
                                                   text=text, **style), 4, 1)
            else:
                # If there's no data, draw a dummy trace so it shows up in the legend anyway.
                topo_figure.add_trace(go.Scattergl(x=[np.nan], y=[np.nan], name=name, visible='legendonly', **style),
                                      1, 1)
                time_figure.add_trace(go.Scattergl(x=[np.nan], y=[np.nan], name=name, visible='legendonly', **style),
                                      1, 1)

        for type, info in _SOLUTION_TYPE_MAP.items():
            _plot_data(info.name, solution_type == type, marker_style=info.style)

        name = source.replace(' ', '_').lower()
        self._add_figure(name=f"{name}_top_down", figure=topo_figure, title=f"{source}: Top-Down (Topocentric)")
        self._add_figure(name=f"{name}_displacement", figure=time_figure, title=f"{source}: vs. Time")

    def plot_pose_displacement(self):
        """!
        @brief Generate a topocentric (top-down) plot of position displacement, as well as plot of displacement over
               time.
        """
        if self.output_dir is None:
            return

        # Read the pose data.
        result = self.reader.read(message_types=[PoseMessage], **self.params)
        pose_data = result[PoseMessage.MESSAGE_TYPE]

        if len(pose_data.p1_time) == 0:
            self.logger.info('No pose data available. Skipping displacement plots.')
            return

        # Remove invalid solutions.
        valid_idx = np.logical_and(~np.isnan(pose_data.p1_time), pose_data.solution_type != SolutionType.Invalid)
        if not np.any(valid_idx):
            self.logger.info('No valid position solutions detected. Skipping displacement plots.')
            return

        time = pose_data.p1_time[valid_idx] - float(self.t0)
        solution_type = pose_data.solution_type[valid_idx]
        lla_deg = pose_data.lla_deg[:, valid_idx]
        std_enu_m = pose_data.position_std_enu_m[:, valid_idx]

        # Convert to ENU displacement with respect to the median position (we use median instead of centroid just in
        # case there are one or two huge outliers).
        position_ecef_m = np.array(geodetic2ecef(lat=lla_deg[0, :], lon=lla_deg[1, :], alt=lla_deg[2, :], deg=True))
        center_ecef_m = np.median(position_ecef_m, axis=1)
        displacement_ecef_m = position_ecef_m - center_ecef_m.reshape(3, 1)
        c_enu_ecef = get_enu_rotation_matrix(*lla_deg[0:2, 0], deg=True)
        displacement_enu_m = c_enu_ecef.dot(displacement_ecef_m)

        self._plot_displacement('Pose Displacement', time, solution_type, displacement_enu_m, std_enu_m)

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

        time = relative_position_data.p1_time[valid_idx] - float(self.t0)
        solution_type = relative_position_data.solution_type[valid_idx]
        displacement_enu_m = relative_position_data.relative_position_enu_m[:, valid_idx]
        std_enu_m = relative_position_data.position_std_enu_m[:, valid_idx]

        self._plot_displacement('Relative Position vs.Base Station', time, solution_type, displacement_enu_m, std_enu_m)

    def plot_map(self, mapbox_token):
        """!
        @brief Plot a map of the position data.
        """
        if self.output_dir is None:
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

        # Read the pose data.
        result = self.reader.read(message_types=[PoseMessage], **self.params)
        pose_data = result[PoseMessage.MESSAGE_TYPE]

        if len(pose_data.p1_time) == 0:
            self.logger.info('No pose data available. Skipping map display.')
            return

        # Remove invalid solutions.
        valid_idx = np.logical_and(~np.isnan(pose_data.p1_time), pose_data.solution_type != SolutionType.Invalid)
        if not np.any(valid_idx):
            self.logger.info('No valid position solutions detected.')
            return

        time = pose_data.p1_time[valid_idx] - float(self.t0)
        solution_type = pose_data.solution_type[valid_idx]
        lla_deg = pose_data.lla_deg[:, valid_idx]
        std_enu_m = pose_data.position_std_enu_m[:, valid_idx]

        # Add data to the map.
        map_data = []

        def _plot_data(name, idx, marker_style=None):
            style = {'mode': 'markers', 'marker': {'size': 8}, 'showlegend': True}
            if marker_style is not None:
                style['marker'].update(marker_style)

            if np.any(idx):
                text = ["Time: %.3f sec (%.3f sec)<br>Std (ENU): (%.2f, %.2f, %.2f) m" %
                        (t, t + float(self.t0), std[0], std[1], std[2])
                        for t, std in zip(time[idx], std_enu_m[:, idx].T)]
                map_data.append(go.Scattermapbox(lat=lla_deg[0, idx], lon=lla_deg[1, idx], name=name, text=text,
                                                 **style))
            else:
                # If there's no data, draw a dummy trace so it shows up in the legend anyway.
                map_data.append(go.Scattermapbox(lat=[np.nan], lon=[np.nan], name=name, visible='legendonly', **style))

        for type, info in _SOLUTION_TYPE_MAP.items():
            _plot_data(info.name, solution_type == type, marker_style=info.style)

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

        self._add_figure(name="map", figure=figure, title="Vehicle Trajectory (Map)")

    def plot_gnss_skyplot(self, decimate=True):
        # Read the satellite data.
        result = self.reader.read(message_types=[GNSSSatelliteMessage], **self.params)
        data = result[GNSSSatelliteMessage.MESSAGE_TYPE]

        if len(data.p1_time) == 0:
            self.logger.info('No satellite data available. Skipping sky plot.')
            return

        # Setup the figure.
        figure = go.Figure()
        figure['layout'].update(title='GNSS Sky Plot')
        figure['layout']['polar']['radialaxis'].update(range=[90, 0])
        figure['layout']['polar']['angularaxis'].update(visible=False)

        # Assign colors to each satellite.
        data_by_sv = GNSSSatelliteMessage.group_by_sv(data)
        svs = sorted(list(data_by_sv.keys()))
        color_by_sv = self._assign_colors(svs)

        # Plot each satellite.
        indices_by_system = defaultdict(list)
        color_by_sv_format = []
        color_by_cn0_format = []
        for sv in svs:
            name = satellite_to_string(sv, short=False)
            system = get_system(sv)
            sv_data = data_by_sv[sv]

            p1_time = sv_data['p1_time']
            az_deg = sv_data['azimuth_deg']
            el_deg = sv_data['elevation_deg']
            cn0_dbhz = sv_data['cn0_dbhz']

            # Decimate the data to 30 second intervals.
            if decimate and len(p1_time) > 1:
                interval_sec = 30.0
                dt_sec = np.round(np.min(np.diff(p1_time)) / 0.1) * 0.1
                if dt_sec < interval_sec:
                    rounded_time = np.round(p1_time / interval_sec) * interval_sec
                    idx = np.where(np.diff(rounded_time, prepend=rounded_time[0]) > 0.01)[0]
                    p1_time = p1_time[idx]
                    az_deg = az_deg[idx]
                    el_deg = el_deg[idx]
                    cn0_dbhz = cn0_dbhz[idx]

            # Plot the data. We set styles for both coloring by SV and by C/N0. We'll add buttons below to switch
            # between styles.
            color_by_sv_format.append({'color': color_by_sv[sv]})
            color_by_cn0_format.append({'cmin': 20, 'cmax': 55, 'colorscale': 'RdBu', 'showscale': True,
                                        'colorbar': {'x': 0}, 'color': cn0_dbhz})

            text = ['P1: %.1f sec<br>(Az, El): (%.2f, %.2f) deg<br>C/N0: %.1f dB-Hz' %
                    (t, a, e, c) for t, a, e, c in zip(p1_time, az_deg, el_deg, cn0_dbhz)]
            figure.add_trace(go.Scatterpolargl(r=el_deg, theta=(90 - az_deg), text=text,
                                               name=name, hoverinfo='name+text', hoverlabel={'namelength': -1},
                                               mode='markers', marker=color_by_sv_format[-1]))
            indices_by_system[system].append(len(figure.data) - 1)

        # Add selection buttons for each system and for choosing between coloring by SV and C/N0.
        num_traces = len(figure.data)
        buttons = [dict(label='All', method='restyle', args=['visible', [True] * num_traces])]
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

        self._add_figure(name='gnss_skyplot', figure=figure, title='GNSS Sky Plot')

    def plot_gnss_cn0(self):
        # The legacy GNSSSatelliteMessage contains data per satellite, not per signal. The plotted C/N0 values will
        # reflect the L1 signal, unless L1 is not being tracked.
        result = self.reader.read(message_types=[GNSSSatelliteMessage], **self.params)
        data = result[GNSSSatelliteMessage.MESSAGE_TYPE]

        if len(data.p1_time) == 0:
            self.logger.info('No satellite data available. Skipping C/N0 plot.')
            return

        # Setup the figure.
        figure = make_subplots(
            rows=1, cols=1,  print_grid=False, shared_xaxes=True,
            subplot_titles=['C/N0 (L1 Only)'])

        figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'])
        figure['layout']['xaxis1'].update(title=self.p1_time_label, showticklabels=True)
        figure['layout']['yaxis1'].update(title="C/N0 (dB-Hz)")

        # Assign colors to each satellite.
        data_by_sv = GNSSSatelliteMessage.group_by_sv(data)
        svs = sorted(list(data_by_sv.keys()))
        color_by_sv = self._assign_colors(svs)

        # Plot each satellite.
        indices_by_system = defaultdict(list)
        for sv in svs:
            name = satellite_to_string(sv, short=False)
            system = get_system(sv)
            sv_data = data_by_sv[sv]

            text = ['P1: %.1f sec' % t for t in sv_data['p1_time']]
            time = sv_data['p1_time'] - float(self.t0)
            figure.add_trace(go.Scattergl(x=time, y=sv_data['cn0_dbhz'], text=text,
                                          name=name, hoverlabel={'namelength': -1},
                                          mode='markers', marker={'color': color_by_sv[sv]}),
                             1, 1)
            indices_by_system[system].append(len(figure.data) - 1)

        # Add signal type selection buttons.
        num_traces = len(figure.data)
        buttons = [dict(label='All', method='restyle', args=['visible', [True] * num_traces])]
        for system, indices in sorted(indices_by_system.items()):
            if len(indices) == 0:
                continue
            visible = np.full((num_traces,), False)
            visible[indices] = True
            buttons.append(dict(label=f'{str(system)} ({len(indices)})', method='restyle', args=['visible', visible]))
        figure['layout']['updatemenus'] = [{
            'type': 'buttons',
            'direction': 'left',
            'buttons': buttons,
            'x': 0.0,
            'xanchor': 'left',
            'y': 1.1,
            'yanchor': 'top'
        }]

        self._add_figure(name='gnss_cn0', figure=figure, title='GNSS C/N0 vs. Time')

    def plot_gnss_signal_status(self):
        filename = 'gnss_signal_status'
        figure_title = "GNSS Signal Status"

        # Read the satellite data.
        result = self.reader.read(message_types=[GNSSSatelliteMessage], **self.params)
        data = result[GNSSSatelliteMessage.MESSAGE_TYPE]
        is_legacy_message = True

        if len(data.p1_time) == 0:
            self.logger.info('No satellite data available. Skipping signal usage plot.')
            return

        # Setup the figure.
        colors = {'unused': 'black', 'pr': 'red', 'is_pivot': 'purple',
                  'float': 'darkgoldenrod', 'not_fixed': 'green', 'fixed_skipped': 'blue', 'fixed': 'orange'}

        # The legacy GNSSSatelliteMessage contains data per satellite, not per signal, and only includes in-use status.
        # It does not elaborate on how the signal was used.
        if is_legacy_message:
            title = '''\
Satellite Status<br>
Black=Unused, Red=Used'''
            entry_type = 'Satellite'
        else:
            # In practice, the signal status plot can be _VERY_ slow to generate for really long logs (multiple hours)
            # because plotly doesn't handle figures with lots of traces very efficiently. The legacy satellite status
            # plot doesn't seem to suffer nearly as much since A) it has fewer elements (# SVs vs # signals), and B) it
            # only supports at most 2 traces per element since it doesn't convey usage type.
            if self.truncate_data:
                _logger.warning('Skipping signal status plot for very long log. Rerun with --truncate=false to '
                                'generate this plot.')
                self._add_figure(name=filename, title=f'{figure_title} (Skipped - Long Log Detected)')
                return

            title = '''\
Signal Status<br>
Black=Unused, Red=Pseudorange, Pink=Pseudorange (Differential), Purple=Pivot (Differential)<br>
Gold=Float, Green=Integer (Not Fixed), Blue=Integer (Fixed, Float Solution Type), Orange=Integer (Fixed)'''
            entry_type = 'Signal'

        figure = make_subplots(
            rows=5, cols=1,  print_grid=False, shared_xaxes=True,
            subplot_titles=[title,
                            None, None, None,
                            'Satellite Count'],
            specs=[[{'rowspan': 4}],
                   [None],
                   [None],
                   [None],
                   [{}]])
        figure['layout'].update(showlegend=False, modebar_add=['v1hovermode'])
        figure['layout']['xaxis1'].update(title=self.p1_time_label)
        figure['layout']['yaxis1'].update(title=entry_type)
        figure['layout']['yaxis2'].update(title=f"# {entry_type}s", rangemode='tozero')

        # Plot the signal counts.
        time = data.p1_time - float(self.t0)
        text = ["P1: %.3f sec" % (t + float(self.t0)) for t in time]
        figure.add_trace(go.Scattergl(x=time, y=data.num_svs, text=text,
                                      name=f'# {entry_type}s', hoverlabel={'namelength': -1},
                                      mode='lines', line={'color': 'black', 'dash': 'dash'}),
                         5, 1)
        figure.add_trace(go.Scattergl(x=time, y=data.num_used_svs, text=text,
                                      name=f'# Used {entry_type}s', hoverlabel={'namelength': -1},
                                      mode='lines', line={'color': 'green'}),
                         5, 1)

        num_count_traces = len(figure.data)

        # Plot each satellite. Plot in reverse order so G01 is at the top of the Y axis.
        data_by_sv = GNSSSatelliteMessage.group_by_sv(data)
        svs = list(data_by_sv.keys())
        svs_by_system = defaultdict(set)
        indices_by_system = defaultdict(list)
        for i, sv in enumerate(svs[::-1]):
            sv = int(sv)
            system = get_system(sv)
            name = satellite_to_string(sv, short=True)
            svs_by_system[system].add(sv)

            sv_data = data_by_sv[sv]
            time = sv_data['p1_time'] - float(self.t0)
            is_used = np.bitwise_and(sv_data['flags'], SatelliteInfo.SATELLITE_USED).astype(bool)

            idx = is_used
            if np.any(idx):
                text = ["P1: %.3f sec" % (t + float(self.t0)) for t in time[idx]]
                figure.add_trace(go.Scattergl(x=time[idx], y=[i] * np.sum(idx), text=text,
                                              name=name, hoverlabel={'namelength': -1},
                                              mode='markers',
                                              marker={'color': colors['pr'], 'symbol': 'circle', 'size': 8}),
                                 1, 1)
                indices_by_system[system].append(len(figure.data) - 1)

            idx = ~is_used
            if np.any(idx):
                text = ["P1: %.3f sec" % (t + float(self.t0)) for t in time[idx]]
                figure.add_trace(go.Scattergl(x=time[idx], y=[i] * np.sum(idx), text=text,
                                              name=name + ' (Unused)', hoverlabel={'namelength': -1},
                                              mode='markers',
                                              marker={'color': colors['unused'], 'symbol': 'x', 'size': 8}),
                                 1, 1)
                indices_by_system[system].append(len(figure.data) - 1)

        tick_text = [satellite_to_string(s, short=True) for s in svs[::-1]]
        figure['layout']['yaxis1'].update(tickmode='array', tickvals=np.arange(0, len(svs)),
                                          ticktext=tick_text, automargin=True)

        # Add signal type selection buttons.
        num_traces = len(figure.data)
        buttons = [dict(label='All', method='restyle', args=['visible', [True] * num_traces])]
        for system, indices in sorted(indices_by_system.items()):
            if len(indices) == 0:
                continue
            visible = np.full((num_traces,), False)
            visible[:num_count_traces] = True
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

        self._add_figure(name=filename, figure=figure, title=figure_title)

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

        # # Setup the figure.
        figure = make_subplots(
            rows=1, cols=1,  print_grid=False, shared_xaxes=True,
            subplot_titles=['Dilution of Precision (DOP)'])

        figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'])
        figure['layout']['xaxis'].update(title=self.p1_time_label)

        dops = [('GDOP', data.gdop), ('PDOP', data.pdop), ('HDOP', data.hdop), ('VDOP', data.vdop)]

        # Assign colors to each DOP type.
        color_by_dop = self._assign_colors([entry[0] for entry in dops])

        # Plot each DOP type.
        for entry in dops:
            name, dop = entry

            text = ['P1: %.1f sec' % t for t in data.p1_time]
            time = data.p1_time - float(self.t0)
            figure.add_trace(go.Scattergl(x=time, y=dop, text=text,
                                          name=name, hoverlabel={'namelength': -1},
                                          mode='markers', marker={'color': color_by_dop[name]}),
                             1, 1)

        self._add_figure(name='gnss_dop', figure=figure, title='GNSS Dilution of Precision (DOP) vs. Time')

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
        for i in range(2):
            figure['layout']['xaxis%d' % (i + 1)].update(title=self.p1_time_label, showticklabels=True, matches='x')
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
            time = data.p1_time[idx] - float(self.t0)
            name = f'Station {station_id}'
            color = colors[station_id]
            text = ["P1 Time: %.3f sec" % (t + float(self.t0)) for t in time]
            figure.add_trace(go.Scattergl(x=time, y=data.baseline_distance_m[idx] * 1e-3, text=text,
                                          name=name, legendgroup=int(station_id), showlegend=True,
                                          mode='markers', marker={'color': color}),
                             1, 1)
            figure.add_trace(go.Scattergl(x=time, y=data.corrections_age_sec[idx], text=text,
                                          name=name, legendgroup=int(station_id), showlegend=False,
                                          mode='markers', marker={'color': color}),
                             4, 1)

        self._add_figure(name="gnss_corrections_status", figure=figure, title="GNSS Corrections Status")

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
            raw_time_source = _get_time_source(raw_measurement_type, data)
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

        if same_time_source:
            time_name = self._time_source_to_display_name(common_time_source)
            figure['layout']['annotations'][0]['text'] += '<br>Time Source: %s' % time_name

            time_label = f'{time_name} Time (sec)'
            for i in range(len(titles)):
                figure['layout']['xaxis%d' % (i + 1)].update(title=time_label, showticklabels=True)
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
            result = self.reader.read(message_types=[PoseMessage], **self.params)
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
                result = self.reader.read(message_types=[PoseAuxMessage], **self.params)
                pose_aux_data = result[PoseAuxMessage.MESSAGE_TYPE]
                if len(pose_aux_data.p1_time) != 0:
                    self.logger.warning('Body forward velocity not available. Estimating |speed| from ENU velocity. '
                                        'May not match wheel speeds when going backward.')
                    nav_engine_p1_time = pose_aux_data.p1_time
                    nav_engine_speed_mps = np.linalg.norm(pose_aux_data.velocity_enu_mps, axis=0)
                    nav_engine_speed_name = '|3D Speed Estimate| (Nav Engine)'

            if nav_engine_speed_mps is not None:
                time = nav_engine_p1_time - float(self.t0)
                text = ["P1: %.3f sec" % t for t in nav_engine_p1_time]
                figure.add_trace(go.Scattergl(x=time, y=nav_engine_speed_mps, text=text,
                                              name=nav_engine_speed_name, hoverlabel={'namelength': -1},
                                              mode='lines', line={'color': 'black', 'dash': 'dash'}),
                                 1, 1)

        # Plot the data.
        def _plot_trace(time, data, name, color, text, style=None):
            if style is None:
                style = {}
            style.setdefault('mode', 'lines')
            style.setdefault('line', {}).setdefault('color', color)

            if type == 'tick':
                figure.add_trace(go.Scattergl(x=time, y=data, text=text,
                                              name=name, hoverlabel={'namelength': -1},
                                              legendgroup=name,
                                              **style),
                                 1, 1)

                dt_sec = np.diff(time)
                ticks_per_sec = np.diff(data) / dt_sec
                figure.add_trace(go.Scattergl(x=time[1:], y=ticks_per_sec, text=text,
                                              name=name, hoverlabel={'namelength': -1},
                                              legendgroup=name, showlegend=False,
                                              **style),
                                 2, 1)
            else:
                figure.add_trace(go.Scattergl(x=time, y=data, text=text,
                                              name=name, hoverlabel={'namelength': -1},
                                              legendgroup=name,
                                              **style),
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

            abs_time_sec = self._get_measurement_time(data, time_source)
            idx = ~np.isnan(abs_time_sec)
            abs_time_sec = abs_time_sec[idx]

            t0 = self._get_t0_for_time_source(time_source)
            time = abs_time_sec - t0
            time_name = self._time_source_to_display_name(time_source)
            text = ["%s Time: %.3f sec" % (time_name, t) for t in abs_time_sec]

            _plot_trace(time=time, data=getattr(data, 'front_left_' + var_suffix)[idx], text=text,
                        name='Front Left Wheel' + name_suffix, color='red', style=style)
            _plot_trace(time=time, data=getattr(data, 'front_right_' + var_suffix)[idx], text=text,
                        name='Front Right Wheel' + name_suffix, color='green', style=style)
            _plot_trace(time=time, data=getattr(data, 'rear_left_' + var_suffix)[idx], text=text,
                        name='Rear Left Wheel' + name_suffix, color='blue', style=style)
            _plot_trace(time=time, data=getattr(data, 'rear_right_' + var_suffix)[idx], text=text,
                        name='Rear Right Wheel' + name_suffix, color='purple', style=style)

            if show_gear:
                figure.add_trace(go.Scattergl(x=time, y=data.gear[idx], text=text,
                                              name='Gear (Wheel Data)', hoverlabel={'namelength': -1},
                                              mode='markers', marker={'color': 'red'}),
                                 gear_y_axis, 1)

            name = "Wheel Interval" + name_suffix
            color = 'blue' if is_raw else 'red'
            figure.add_trace(go.Scattergl(x=time[1:], y=np.diff(time), name=name, hoverlabel={'namelength': -1},
                                          mode='markers', marker={'color': color}),
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

            abs_time_sec = self._get_measurement_time(data, time_source)
            idx = ~np.isnan(abs_time_sec)
            abs_time_sec = abs_time_sec[idx]

            t0 = self._get_t0_for_time_source(time_source)
            time = abs_time_sec - t0
            time_name = self._time_source_to_display_name(time_source)
            text = ["%s Time: %.3f sec" % (time_name, t) for t in abs_time_sec]

            _plot_trace(time=time, data=getattr(data, var_suffix)[idx], text=text,
                        name='Speed Measurement' + name_suffix, color='orange', style=style)

            if show_gear:
                figure.add_trace(go.Scattergl(x=time, y=data.gear[idx], text=text,
                                              name='Gear (Vehicle Data)', hoverlabel={'namelength': -1},
                                              mode='markers', marker={'color': 'orange'}),
                                 gear_y_axis, 1)

            name = "Vehicle Interval" + name_suffix
            color = 'blue' if is_raw else 'red'
            figure.add_trace(go.Scattergl(x=time[1:], y=np.diff(time), name=name, hoverlabel={'namelength': -1},
                                          mode='markers', marker={'color': color}),
                             interval_y_axis, 1)

        # Plot the data. If we have both corrected (e.g., WheelSpeedOutput) and uncorrected (e.g., RawWheelSpeedOutput)
        # messages are present in the log, plot them both for comparison.
        _plot_func = _plot_wheel_data if source == 'wheel' else _plot_vehicle_data
        _plot_func(data, corrected_time_source, is_raw=False, show_gear=True)
        _plot_func(raw_data, raw_time_source, is_raw=True, show_gear=False)

        self._add_figure(name=filename, figure=figure, title=figure_title)

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

        time = data.p1_time - float(self.t0)

        titles = ['Acceleration', 'Gyro']
        if message_cls == RawIMUOutput:
            titles = [t + ' (Uncorrected)' for t in titles]
        else:
            titles = [t + ' (Corrected)' for t in titles]
        titles.append('Measurement Interval')

        figure = make_subplots(rows=len(titles), cols=1, print_grid=False, shared_xaxes=True, subplot_titles=titles)

        figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'])
        for i in range(3):
            figure['layout']['xaxis%d' % (i + 1)].update(title=self.p1_time_label, showticklabels=True)
        figure['layout']['yaxis1'].update(title="Acceleration (m/s^2)")
        figure['layout']['yaxis2'].update(title="Rotation Rate (rad/s)")
        figure['layout']['yaxis3'].update(title="Interval (sec)")

        figure.add_trace(go.Scattergl(x=time, y=data.accel_mps2[0, :], name='X', legendgroup='x',
                                      mode='lines', line={'color': 'red'}),
                         1, 1)
        figure.add_trace(go.Scattergl(x=time, y=data.accel_mps2[1, :], name='Y', legendgroup='y',
                                      mode='lines', line={'color': 'green'}),
                         1, 1)
        figure.add_trace(go.Scattergl(x=time, y=data.accel_mps2[2, :], name='Z', legendgroup='z',
                                      mode='lines', line={'color': 'blue'}),
                         1, 1)

        figure.add_trace(go.Scattergl(x=time, y=data.gyro_rps[0, :], name='X', legendgroup='x',
                                      showlegend=False, mode='lines', line={'color': 'red'}),
                         2, 1)
        figure.add_trace(go.Scattergl(x=time, y=data.gyro_rps[1, :], name='Y', legendgroup='y',
                                      showlegend=False, mode='lines', line={'color': 'green'}),
                         2, 1)
        figure.add_trace(go.Scattergl(x=time, y=data.gyro_rps[2, :], name='Z', legendgroup='z',
                                      showlegend=False, mode='lines', line={'color': 'blue'}),
                         2, 1)

        figure.add_trace(go.Scattergl(x=time[1:], y=np.diff(time), name='Interval', hoverlabel={'namelength': -1},
                                      mode='markers', marker={'color': 'red'}),
                         3, 1)

        self._add_figure(name=filename, figure=figure, title=figure_title)

    def plot_heading_measurements(self):
        """!
        @brief Generate time series plots for heading (degrees) and baseline distance (meters) data.
        """
        if self.output_dir is None:
            return

        # Read the heading measurement data.
        result = self.reader.read(message_types=[RawHeadingOutput, HeadingOutput], **self.params)
        raw_heading_data = result[RawHeadingOutput.MESSAGE_TYPE]
        heading_data = result[HeadingOutput.MESSAGE_TYPE]

        if (len(heading_data.p1_time) == 0) and (len(raw_heading_data.p1_time) == 0):
            self.logger.info('No heading measurement data available. Skipping plot.')
            return

        # Note that we read the pose data after heading, that way we don't bother reading pose data from disk if there's
        # no heading data in the log.
        result = self.reader.read(message_types=[PoseMessage], **self.params)
        primary_pose_data = result[PoseMessage.MESSAGE_TYPE]

        # Setup the figure.
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=(
                'Heading, 2-sigma band',
                'ENU/Baseline Distance',
                'Solution Type'
            ),
            shared_xaxes=True,
        )

        fig.update_xaxes(title_text='Time (sec)', showticklabels=True)
        fig.update_yaxes(title_text='Heading (deg)', rangemode='tozero', row=1, col=1)
        fig.update_yaxes(title_text='Distance (m)', row=2, col=1)
        fig.update_yaxes(
            ticktext=['%s (%d)' % (e.name, e.value) for e in SolutionType],
            tickvals=[e.value for e in SolutionType],
            title_text='Solution Type',
            row=3, col=1
        )

        fig.update_layout(title='Heading Plots', legend_traceorder='normal')


        # Display the navigation engine's heading estimate, if available, for comparison with the heading sensor
        # measurement.
        if primary_pose_data is not None:
            invalid_idx = primary_pose_data.solution_type[primary_pose_data.solution_type != SolutionType.Invalid]
            yaw_deg = primary_pose_data.ypr_deg[0][invalid_idx]
            if len(yaw_deg) > 0:
                pose_heading_deg = 90.0 - yaw_deg
                pose_heading_deg[pose_heading_deg < 0.0] += 360.0
                fig.add_trace(
                    go.Scatter(
                        x=primary_pose_data.p1_time - float(self.t0),
                        y=pose_heading_deg,
                        customdata=primary_pose_data.p1_time,
                        mode='lines',
                        line={'color': 'yellow'},
                        name='Primary Device Heading Estimate',
                        hovertemplate='<b>Time</b>: %{x:.3f} sec (%{customdata:.3f} sec)'
                                      '<br><b>Heading</b>: %{y:.2f} deg'
                    ),
                    row=1, col=1
                )

        # Corrected heading plot
        if len(heading_data.p1_time) > 0:
            heading_time = heading_data.p1_time - float(self.t0)
            fig.add_trace(
                go.Scatter(
                    x=heading_time,
                    y=heading_data.heading_true_north_deg,
                    customdata=heading_data.p1_time,
                    mode='markers',
                    marker={'size': 2, "color": "green"},
                    name='Corrected Heading Data',
                    hovertemplate='<b>Time</b>: %{x:.3f} sec (%{customdata:.3f} sec)'
                                  '<br><b>Heading</b>: %{y:.2f} deg',
                    legendgroup='heading'
                ),
                row=1, col=1
            )

        # Uncorrected heading plot
        if len(raw_heading_data.p1_time) > 0:
            raw_heading_time = raw_heading_data.p1_time - float(self.t0)
            # Compute heading uncertainty envelop.
            denom = raw_heading_data.relative_position_enu_m[0]**2 + raw_heading_data.relative_position_enu_m[1]**2
            dh_e = raw_heading_data.relative_position_enu_m[0] / denom
            dh_n = raw_heading_data.relative_position_enu_m[2] / denom

            heading_std = np.sqrt(
                (dh_e * raw_heading_data.position_std_enu_m[0]) ** 2 +
                (dh_n * raw_heading_data.position_std_enu_m[1]) ** 2
            )

            envelope = np.arctan(
                (2 * heading_std / raw_heading_data.baseline_distance_m)
            )
            envelope *= 180. / np.pi
            fig.add_trace(
                go.Scatter(
                    x=raw_heading_time,
                    y=raw_heading_data.heading_true_north_deg,
                    customdata=raw_heading_data.p1_time,
                    mode='markers',
                    marker={'size': 2, "color": "red"},
                    name='Uncorrected Heading Data',
                    hovertemplate='<b>Time</b>: %{x:.3f} sec (%{customdata:.3f} sec)'
                                  '<br><b>Heading</b>: %{y:.2f} deg',
                    legendgroup='heading'
                ),
                row=1, col=1
            )
            idx = ~np.isnan(raw_heading_data.heading_true_north_deg)

            fig.add_trace(
                go.Scatter(
                    x=raw_heading_time[idx],
                    y=raw_heading_data.heading_true_north_deg[idx] + envelope[idx],
                    mode='lines',
                    marker={'size': 2, "color": "red"},
                    line=dict(width=0),
                    legendgroup='heading',
                    showlegend=False,
                    hoverinfo='skip'
                ),
                row=1, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=raw_heading_time[idx],
                    y=raw_heading_data.heading_true_north_deg[idx] - envelope[idx],
                    mode='lines',
                    marker={'size': 2, "color": "red"},
                    line=dict(width=0),
                    fillcolor='rgba(68, 68, 68, 0.3)',
                    fill='tonexty',
                    legendgroup='heading',
                    showlegend=False,
                    hoverinfo='skip'
                ),
                row=1, col=1
            )

            # Second plot - baseline, ENU components
            fig.add_trace(
                go.Scatter(
                    x=raw_heading_time,
                    y=raw_heading_data.relative_position_enu_m[0],
                    customdata=raw_heading_data.p1_time,
                    hovertemplate='<b>Time</b>: %{x:.3f} sec (%{customdata:.3f} sec)'
                                  '<br><b>East</b>: %{y:.2f} m',
                    name='East'
                ),
                row=2, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=raw_heading_time,
                    y=raw_heading_data.relative_position_enu_m[1],
                    customdata=raw_heading_data.p1_time,
                    hovertemplate='<b>Time</b>: %{x:.3f} sec (%{customdata:.3f} sec)'
                                  '<br><b>North</b>: %{y:.2f} m',
                    name='North'
                ),
                row=2, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=raw_heading_time,
                    y=raw_heading_data.relative_position_enu_m[2],
                    customdata=raw_heading_data.p1_time,
                    hovertemplate='<b>Time</b>: %{x:.3f} sec (%{customdata:.3f} sec)'
                                  '<br><b>Up</b>: %{y:.2f} m',
                    name='Up'
                ),
                row=2, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=raw_heading_time,
                    y=raw_heading_data.baseline_distance_m,
                    customdata=raw_heading_data.p1_time,
                    marker={'size': 2, "color": "red"},
                    hovertemplate='<b>Time</b>: %{x:.3f} sec (%{customdata:.3f} sec)'
                                  '<br><b>Baseline</b>: %{y:.2f} m',
                    name='Baseline'
                ),
                row=2, col=1
            )

        # 3rd plot - solution type
        if primary_pose_data is not None:
            fig.add_trace(
                go.Scatter(
                    x=primary_pose_data.p1_time - float(self.t0),
                    y=primary_pose_data.solution_type,
                    customdata=primary_pose_data.p1_time,
                    mode='markers',
                    marker={'color': 'yellow'},
                    hovertemplate='<b>Time</b>: %{x:.3f} sec (%{customdata:.3f} sec)'
                                  '<br><b>Solution</b>: %{text}',
                    text=[str(SolutionType(s)) for s in primary_pose_data.solution_type],
                    name='Primary Solution Type'
                ),
                row=3, col=1
            )

        if len(raw_heading_data.p1_time) > 0:
            fig.add_trace(
                go.Scatter(
                    x=raw_heading_time,
                    y=raw_heading_data.solution_type,
                    customdata=raw_heading_data.p1_time,
                    marker={'color': 'red'},
                    hovertemplate='<b>Time</b>: %{x:.3f} sec (%{customdata:.3f} sec)'
                                  '<br><b>Solution</b>: %{text}',
                    text=[str(SolutionType(s)) for s in raw_heading_data.solution_type],
                    name='Uncorrected Heading Solution Type'
                ),
                row=3, col=1
            )

        if len(heading_data.p1_time) > 0:
            fig.add_trace(
                go.Scatter(
                    x=heading_time,
                    y=heading_data.solution_type,
                    customdata=heading_data.p1_time,
                    marker={'color': 'green'},
                    hovertemplate='<b>Time</b>: %{x:.3f} sec (%{customdata:.3f} sec)'
                                  '<br><b>Solution</b>: %{text}',
                    text=[str(SolutionType(s)) for s in raw_heading_data.solution_type],
                    name='Corrected Heading Solution Type'
                ),
                row=3, col=1
            )

        self._add_figure(name='heading_measurement', figure=fig, title='Measurements: Heading')

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

        # Setup the figure.
        figure = make_subplots(rows=1, cols=1, print_grid=False, shared_xaxes=True,
                               subplot_titles=['GNSS Temperature'])

        figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'])
        for i in range(1):
            figure['layout']['xaxis%d' % (i + 1)].update(title=self.p1_time_label, showticklabels=True)
        figure['layout']['yaxis1'].update(title="Temp (deg C)")

        # Plot the data.
        time = data.p1_time - float(self.t0)
        figure.add_trace(go.Scattergl(x=time, y=data.gnss_temperature_degc, customdata=data.p1_time,
                                      name='GNSS Temperature',
                                      hovertemplate='Time: %{x:.3f} sec (%{customdata:.3f} sec)',
                                      mode='markers', line={'color': 'red'}),
                         1, 1)

        self._add_figure(name="profile_system_status", figure=figure, title="Profiling: System Status")

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
        for message, message_bytes in zip(data.messages, data.messages_bytes):
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

        table_html = _data_to_table(table_columns, rows, row_major=True)
        body_html = f"""\
<h2>Device Event Log</h2>
<pre>{table_html}</pre>
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

    def generate_index(self, auto_open=True):
        """!
        @brief Generate an `index.html` page with links to all generated figures.

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

        index_html = _page_template % {
            'title': 'FusionEngine Output',
            'body': links + '\n<pre>' + self.summary.replace('\n', '<br>') + '</pre>'
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
        result = self.reader.read(message_types=[PoseMessage], **self.params)
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
            dt_p1_sec = pose_data.p1_time[idx] - float(self.t0)
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
        else:
            processed_t0 = Timestamp()

        result = self.reader.read(message_types=None, require_system_time=True, **params)
        if len(result.messages) > 0:
            processed_system_t0 = result.messages[0].get_system_time_sec()
        else:
            processed_system_t0 = None

        # Create a table with log times and durations.
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
            str(self.reader.t0),
            system_time_to_str(self.reader.get_system_t0(), is_seconds=True).replace(' time', ':'),
            self._gps_sec_to_string(t0_gps, is_approx=t0_is_approx),
            log_duration_sec,
            '',
            # Processed data summary.
            str(processed_t0),
            system_time_to_str(processed_system_t0, is_seconds=True).replace(' time', ':'),
            self._gps_sec_to_string(t0_gps, is_approx=t0_is_approx),
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

        # Create a software version table.
        result = self.reader.read(message_types=[VersionInfoMessage.MESSAGE_TYPE], remove_nan_times=False,
                                  **self.params)
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

    def _add_figure(self, name, figure=None, title=None):
        if title is None:
            title = name

        if name in self.plots:
            raise ValueError('Plot "%s" already exists.' % name)
        elif name == 'index':
            raise ValueError('Plot name cannot be index.')

        if figure is not None:
            path = os.path.join(self.output_dir, self.prefix + name + '.html')
            self.logger.info('Creating %s...' % path)

            os.makedirs(os.path.dirname(path), exist_ok=True)
            plotly.offline.plot(
                figure,
                output_type='file',
                filename=path,
                include_plotlyjs=True,
                auto_open=False,
                show_link=False)

        self.plots[name] = {'title': title, 'path': path if figure is not None else None}

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
            return float(self.t0)
        elif time_source == SystemTimeSource.GPS_TIME:
            return 0.0
        elif time_source == SystemTimeSource.SENDER_SYSTEM_TIME:
            return 0.0
        elif time_source == SystemTimeSource.TIMESTAMPED_ON_RECEPTION:
            return float(self.system_t0)

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

        if np.isnan(gps_time_sec):
            return "GPS: N/A<br>UTC: N/A"
        else:
            SECS_PER_WEEK = 7 * 24 * 3600.0
            week = int(gps_time_sec / SECS_PER_WEEK)
            tow_sec = gps_time_sec - week * SECS_PER_WEEK
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


def main():
    parser = ArgumentParser(description="""\
Load and display information stored in a FusionEngine binary file.
""")

    plot_group = parser.add_argument_group('Plot Control')
    plot_group.add_argument('--mapbox-token', metavar='TOKEN',
        help="A Mapbox token to use for satellite imagery when generating a map. If unspecified, the token will be "
             "read from the MAPBOX_ACCESS_TOKEN or MapboxAccessToken environment variables if set. If no token is "
             "available, a default map will be displayed using Open Street Maps data.")
    plot_group.add_argument(
        '-m', '--measurements', action=ExtendedBooleanAction,
        help="Plot incoming measurement data (slow). Ignored if --plot is specified.")
    plot_group.add_argument(
        '--time-axis', choices=('absolute', 'abs', 'relative', 'rel'), default='absolute',
        help="Specify the way in which time will be plotted:"
             "\n- absolute, abs - Absolute P1 or system timestamps"
             "\n- relative, rel - Elapsed time since the start of the log")
    plot_group.add_argument(
        '--truncate', '--trunc', action=ExtendedBooleanAction, default=True,
        help="When processing a very long log (>%.1f hours), reduce or skip some plots that may be very slow to "
             "generate or display. This includes:"
             "\n- GNSS signal status display"
             "\n- High-rate (>%d Hz) measurement data"
             "\n"
             "\nTruncation is disabled if --plot is specified." %
             (Analyzer.LONG_LOG_DURATION_SEC / 3600.0, Analyzer.HIGH_MEASUREMENT_RATE_HZ))

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
    log_group.add_argument(
        '--ignore-index', action=ExtendedBooleanAction,
        help="If set, do not load the .p1i index file corresponding with the .p1log data file. If specified and a "
             ".p1i file does not exist, do not generate one. Otherwise, a .p1i file will be created automatically to "
             "improve data read speed in the future.")
    log_group.add_argument(
        '--log-base-dir', metavar='DIR', default=DEFAULT_LOG_BASE_DIR,
        help="The base directory containing FusionEngine logs to be searched if a log pattern is specified.")
    log_group.add_argument(
        'log',
        help="The log to be read. May be one of:\n"
             "- The path to a .p1log file or a file containing FusionEngine messages and other content\n"
             "- The path to a FusionEngine log directory\n"
             "- A pattern matching a FusionEngine log directory under the specified base directory "
             "(see find_fusion_engine_log() and --log-base-dir)")

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

    options = parser.parse_args()

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
    input_path, output_dir, log_id = locate_log(input_path=options.log, log_base_dir=options.log_base_dir,
                                                return_output_dir=True, return_log_id=True)
    if input_path is None:
        # locate_log() will log an error.
        sys.exit(1)

    if log_id is None:
        _logger.info('Loading %s.' % input_path)
    else:
        _logger.info('Loading %s (log ID: %s).' % (input_path, log_id))

    if options.output is None:
        if log_id is not None:
            output_dir = os.path.join(output_dir, 'plot_fusion_engine')
    else:
        output_dir = options.output

    # Read pose data from the file.
    analyzer = Analyzer(file=input_path, output_dir=output_dir, ignore_index=options.ignore_index,
                        prefix=options.prefix + '.' if options.prefix is not None else '',
                        time_range=time_range, time_axis=options.time_axis,
                        truncate_long_logs=options.truncate and options.plot is None)

    if options.plot is None:
        analyzer.plot_events()
        analyzer.plot_time_scale()

        analyzer.plot_solution_type()
        analyzer.plot_reset_timing()
        analyzer.plot_pose()
        analyzer.plot_pose_displacement()
        analyzer.plot_relative_position()
        analyzer.plot_map(mapbox_token=options.mapbox_token)
        analyzer.plot_calibration()
        analyzer.plot_gnss_cn0()
        analyzer.plot_gnss_signal_status()
        analyzer.plot_gnss_skyplot()
        analyzer.plot_gnss_corrections_status()
        analyzer.plot_dop()

        # By default, we always plot heading measurements (i.e., output from a secondary heading device like an
        # LG69T-AH), separate from other sensor measurements controlled by --measurements.
        analyzer.plot_heading_measurements()

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
            else:
                getattr(analyzer, func)()

    analyzer.generate_index(auto_open=not options.no_index)

    _logger.info("Output stored in '%s'." % os.path.abspath(output_dir))


if __name__ == "__main__":
    main()
