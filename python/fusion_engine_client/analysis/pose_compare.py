#!/usr/bin/env python3

from typing import Tuple, Union, List, Any

from collections import namedtuple, defaultdict
import copy
import inspect
import os
import re
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


_logger = logging.getLogger('point_one.fusion_engine.analysis.pose_compare')

SolutionTypeInfo = namedtuple('SolutionTypeInfo', ['name', 'style'])

_SOLUTION_TYPE_MAP = [{
    SolutionType.Invalid: SolutionTypeInfo(name='Invalid', style={'color': 'black'}),
    SolutionType.Integrate: SolutionTypeInfo(name='Integrated', style={'color': 'cyan'}),
    SolutionType.AutonomousGPS: SolutionTypeInfo(name='Standalone', style={'color': 'red'}),
    SolutionType.DGPS: SolutionTypeInfo(name='DGPS', style={'color': 'blue'}),
    SolutionType.RTKFloat: SolutionTypeInfo(name='RTK Float', style={'color': 'green'}),
    SolutionType.RTKFixed: SolutionTypeInfo(name='RTK Fixed', style={'color': 'orange'}),
    SolutionType.PPP: SolutionTypeInfo(name='PPP', style={'color': 'pink'}),
    SolutionType.Visual: SolutionTypeInfo(name='Vision', style={'color': 'purple'}),
}, {
    SolutionType.Invalid: SolutionTypeInfo(name='Invalid', style={'color': 'black'}),
    SolutionType.Integrate: SolutionTypeInfo(name='Integrated', style={'color': 'gray'}),
    SolutionType.AutonomousGPS: SolutionTypeInfo(name='Standalone', style={'color': 'brown'}),
    SolutionType.DGPS: SolutionTypeInfo(name='DGPS', style={'color': 'yellow'}),
    SolutionType.RTKFloat: SolutionTypeInfo(name='RTK Float', style={'color': 'pink'}),
    SolutionType.RTKFixed: SolutionTypeInfo(name='RTK Fixed', style={'color': 'purple'}),
    SolutionType.PPP: SolutionTypeInfo(name='PPP', style={'color': 'green'}),
    SolutionType.Visual: SolutionTypeInfo(name='Vision', style={'color': 'orange'}),
}]


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


class PoseCompare(object):
    logger = _logger

    def __init__(self,
                 file_a: Union[DataLoader, str], file_b: Union[DataLoader, str], ignore_index: bool = False,
                 output_dir: str = None, prefix: str = '',
                 time_range: TimeRange = None, max_messages: int = None,
                 time_axis: str = 'relative'):
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
        if isinstance(file_a, str):
            self.readers = [DataLoader(file_a, ignore_index=ignore_index)]
        else:
            self.readers = [file_a]

        if isinstance(file_b, str):
            self.readers.append(DataLoader(file_b, ignore_index=ignore_index))
        else:
            self.readers.append(file_b)

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

            result = self.readers[0].read(message_types=[PoseMessage], **self.params)
            gps_time_a = result[PoseMessage.MESSAGE_TYPE].gps_time
            valid_gps_time = gps_time_a[np.isfinite(gps_time_a)]

            if len(valid_gps_time) > 0:
                self.t0 = valid_gps_time[0]
            else:
                self.t0 = Timestamp()

            self.gps_time_label = 'Relative Time (sec)'
        elif time_axis in ('absolute', 'abs'):
            self.time_axis = 'absolute'
            self.t0 = Timestamp(0.0)
            self.gps_time_label = 'GPS Time (sec)'
        else:
            raise ValueError(f"Unsupported time axis specifier '{time_axis}'.")

        self.plots = {}
        self.summary = ''
        self.profiling_present = False

        self._mapbox_token_missing = False

        if self.output_dir is not None:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)


    def plot_solution_type(self):
        """!
        @brief Plot the solution type over time.
        """
        if self.output_dir is None:
            return

        # Read the pose data.
        pose_datas = []
        for reader in self.readers:
            result = reader.read(message_types=[PoseMessage], **self.params)
            pose_datas.append(result[PoseMessage.MESSAGE_TYPE])

        if len(pose_datas[0].p1_time) == 0 or len(pose_datas[1].p1_time) == 0:
            self.logger.info('No pose data available. Skipping solution type plot.')
            return

        # Setup the figure.
        figure = make_subplots(rows=1, cols=1, print_grid=False, shared_xaxes=True, subplot_titles=['Solution Type'])

        figure['layout']['xaxis'].update(title=self.gps_time_label)
        figure['layout']['yaxis1'].update(title="Solution Type",
                                          ticktext=['%s (%d)' % (e.name, e.value) for e in SolutionType],
                                          tickvals=[e.value for e in SolutionType])

        for pose_data in pose_datas:
            time = pose_data.gps_time - float(self.t0)

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
        pose_datas = []
        for reader in self.readers:
            result = reader.read(message_types=[PoseMessage], **self.params)
            pose_datas.append(result[PoseMessage.MESSAGE_TYPE])

        if len(pose_datas[0].p1_time) == 0 or len(pose_datas[0].p1_time) == 0:
            self.logger.info('No pose data available. Skipping map display.')
            return

        # Add data to the map.
        map_data = []

        for i, pose_data in enumerate(pose_datas):
            log_name = ['Log A', 'Log B'][i]

            # Remove invalid solutions.
            valid_idx = np.logical_and(~np.isnan(pose_data.p1_time), pose_data.solution_type != SolutionType.Invalid)
            if not np.any(valid_idx):
                self.logger.info(f'No valid position solutions detected in {log_name}.')
                return

            time = pose_data.p1_time[valid_idx] - float(self.t0)
            solution_type = pose_data.solution_type[valid_idx]
            lla_deg = pose_data.lla_deg[:, valid_idx]
            std_enu_m = pose_data.position_std_enu_m[:, valid_idx]

            def _plot_data(solution_name, idx, marker_style=None):
                name = f'{log_name} {solution_name}'
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

            for type, info in _SOLUTION_TYPE_MAP[i].items():
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

    def _parse_crash_log(self, storage_messages: List[PlatformStorageDataMessage]):
        class CrashType(IntEnum):
            CRASH_TYPE_NONE = 0,
            CRASH_TYPE_HARD_FAULT = 1,
            CRASH_TYPE_MALLOC_FAIL = 2,
            CRASH_TYPE_STACK_OVERFLOW = 3,
            CRASH_TYPE_ABORT = 4

        crash_info_format = '<BI'
        format_len = struct.calcsize(crash_info_format)

        for msg in storage_messages:
            if msg.data_type == DataType.CRASH_LOG and msg.response == Response.OK:
                if len(msg.data) < format_len:
                    self.logger.warning('Crash log with unexpectedly short %d bytes of data.' % len(msg.data))
                else:
                    crash_type, crash_count = struct.unpack(crash_info_format, msg.data[:format_len])
                    return CrashType(crash_type), crash_count

        return (CrashType.CRASH_TYPE_NONE, 0)

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

        # Check the last CrashLog
        result = self.reader.read(message_types=[PlatformStorageDataMessage], remove_nan_times=False, **self.params)
        crash_type, crash_count = self._parse_crash_log(result[PlatformStorageDataMessage.MESSAGE_TYPE].messages)
        crash_table = _data_to_table(['Last Crash Type', 'Crash Count'], [[crash_type.name], [crash_count]])

        # Now populate the summary.
        if self.summary != '':
            self.summary += '\n\n'

        args = {
            'message_table': message_table,
            'version_table': version_table,
            'solution_type_table': solution_type_table,
            'time_table': time_table,
            'crash_table': crash_table,
        }

        self.summary += """
%(version_table)s

%(crash_table)s

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
        '--time-axis', choices=('absolute', 'abs', 'relative', 'rel'), default='absolute',
        help="Specify the way in which time will be plotted:"
             "\n- absolute, abs - Absolute P1 or system timestamps"
             "\n- relative, rel - Elapsed time since the start of the log")

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
        '--original', action=ExtendedBooleanAction,
        help='When loading from a log, load the recorded FusionEngine output file instead of playback results.')
    log_group.add_argument(
        'log_a',
        help="The first log to be read. May be one of:\n"
             "- The path to a .p1log file or a file containing FusionEngine messages and other content\n"
             "- The path to a FusionEngine log directory\n"
             "- A pattern matching a FusionEngine log directory under the specified base directory "
             "(see find_fusion_engine_log() and --log-base-dir)")
    log_group.add_argument(
        'log_b',
        help="The second log to be read. May be one of:\n"
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
              "'<log_dir>/plot_pose_compare/' if reading from a log.")
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
    input_path_a, output_dir, log_id = locate_log(input_path=options.log_a, log_base_dir=options.log_base_dir,
                                                  return_output_dir=True, return_log_id=True,
                                                  load_original=options.original)

    input_path_b = locate_log(input_path=options.log_b, log_base_dir=options.log_base_dir,
                                                  load_original=options.original)

    if input_path_a is None or input_path_b is None:
        # locate_log() will log an error.
        sys.exit(1)

    if log_id is None:
        _logger.info('Loading A: %s , B: %s.' % (input_path_a, input_path_b))

    if options.output is None:
        if log_id is not None:
            output_dir = os.path.join(output_dir, 'plot_pose_compare')
    else:
        output_dir = options.output

    # Read pose data from the file.
    analyzer = PoseCompare(file_a=input_path_a, file_b=input_path_b, output_dir=output_dir, ignore_index=options.ignore_index,
                        prefix=options.prefix + '.' if options.prefix is not None else '',
                        time_range=time_range, time_axis=options.time_axis)


    analyzer.plot_solution_type()
    # Need 2D + 3D difference plot

    # Want to plot difference, not displacement
    #analyzer.plot_pose_displacement()

    analyzer.plot_map(mapbox_token=options.mapbox_token)

    #analyzer.generate_index(auto_open=not options.no_index)

    _logger.info("Output stored in '%s'." % os.path.abspath(output_dir))


if __name__ == "__main__":
    main()
