#!/usr/bin/env python3

from enum import Enum
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


def _data_to_table(col_titles: List[str], values: List[List[Any]], round_decimal_places: Optional[int] = None, row_major: bool = False):
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
                if round_decimal_places and isinstance(col_data[row_idx], float):
                    table_html += f'<td>{col_data[row_idx]:.{round_decimal_places}f}</td>'
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

class NovatelData:
    def __init__(self, gps_time, position_type, lla_deg, lla_std_dev_m):
        """!
        @brief Create a data object that contains data from a Novatel CSV file and replicates the functionality of a
               @ref DataLoader object.

        @param gps_time An array containing GPS times.
        @param position_type An array containing Novatel position types.
        @param lla_deg An array containing latitude, longitude, and altitude.
        @param lla_std_dev_m An array containing standard deviation of position.
        """

        self.gps_time = gps_time
        self.solution_type = np.full((len(position_type)), SolutionType.Invalid)
        self.lla_deg = lla_deg
        # TODO HACK: Figure out how to extract pos std enu from given LLA data. For now, just report lat/lon std instead.
        # Since we only care about the "magnitude" of the std dev, this should be OK since it's still in meters.
        self.position_std_enu_m = lla_std_dev_m

        # Novatel will sometime report Float or Fixed solutions with high std dev. To avoid using it as truth when it
        # has high uncertainty, downgrade these solutions.
        ref_valid_idx = ~np.any(np.isnan(lla_std_dev_m), axis=0)
        ref_combined_std_dev_m = np.full((ref_valid_idx.size), np.nan)
        ref_combined_std_dev_m[ref_valid_idx] = np.sqrt(np.sum(np.square(lla_std_dev_m[:, ref_valid_idx]), axis=0))

        # Translate solution type values.
        # From BESTPOS documentation:
        # 48: L1_INT, Single-frequency RTK solution with carrier phase ambiguities resolved to integers
        # 49: WIDE_INT, Multi-frequency RTK solution with carrier phase ambiguities resolved to wide-lane integers
        # 50: NARROW_INT, Multi-frequency RTK solution with carrier phase ambiguities resolved to narrow-lane integers
        # 56: INS_RTKFIXED, INS position, where the last applied position update used a fixed integer ambiguity RTK (L1_INT, WIDE_INT or NARROW_INT) solution
        self.solution_type[(position_type == 48) | (position_type == 49) | (position_type == 50) |
                           (position_type == 56)] = SolutionType.RTKFixed

        # Downgrade fixed solutions with high std dev.
        self.solution_type[(self.solution_type == SolutionType.RTKFixed) & (ref_combined_std_dev_m > 0.1)] = SolutionType.RTKFloat


        # From BESTPOS documentation:
        # 32: L1_FLOAT, Single-frequency RTK solution with unresolved, float carrier phase ambiguities
        # 34: NARROW_FLOAT, Multi-frequency RTK solution with unresolved, float carrier phase ambiguities
        # 55: INS_RTKFLOAT, INS position, where the last applied position update used a floating ambiguity RTK (L1_FLOAT or NARROW_FLOAT) solution
        self.solution_type[(position_type == 32) | (position_type == 34) | (position_type == 55)] = SolutionType.RTKFloat

        # Downgrade float solutions with high std dev.
        self.solution_type[(self.solution_type == SolutionType.RTKFloat) & (ref_combined_std_dev_m > 0.3)] = SolutionType.AutonomousGPS

        # From BESTPOS documentation:
        # 1: FIXEDPOS, Position has been fixed by the FIX position command or by position averaging
        # 2: FIXEDHEIGHT, Position has been fixed by the FIX height or FIX auto command or by position averaging
        # 8: DOPPLER_VELOCITY, Velocity computed using instantaneous Doppler
        # 19: PROPAGATED, Propagated by a Kalman filter without new observations
        # 51: RTK_DIRECT_INS, RTK status where the RTK filter is directly initialized from the INS filter
        self.solution_type[(position_type == 1) | (position_type == 2) | (position_type == 8) |
                           (position_type == 19) | (position_type == 51)] = SolutionType.Integrate

        # From BESTPOS documentation:
        # 16: SINGLE, Solution calculated using only data supplied by GNSS satellites.
        # 18: WAAS, Solution calculated using corrections from an SBAS satellite
        # 52: INS_SBAS, INS position, where the last applied position update used a GNSS solution computed using corrections from an SBAS (WAAS) solution
        # 53: INS_PSRSP, INS position, where the last applied position update used a single point GNSS (SINGLE) solution
        self.solution_type[(position_type == 16) | (position_type == 18) | (position_type == 52) |
                           (position_type == 53)] = SolutionType.AutonomousGPS

        # Downgrade SPP solutions with high std dev.
        self.solution_type[(self.solution_type == SolutionType.AutonomousGPS) & (ref_combined_std_dev_m > 1.5)] = SolutionType.Integrate

        # From BESTPOS documentation:
        # 17: PSRDIFF, Solution calculated using pseudorange differential (DGPS, DGNSS) corrections
        # 54: INS_PSRDIFF, INS position, where the last applied position update used a pseudorange differential GNSS (PSRDIFF) solution
        self.solution_type[(position_type == 17) | (position_type == 54)] = SolutionType.DGPS

        # Calculate synthetic P1 times assuming constant stream of messages.
        rate = np.round(np.median(np.diff(self.gps_time)), 4)
        _logger.info(f'Novatel rate: {rate}')
        self.p1_time = np.arange(0, len(gps_time)) * rate
        self.p1_time = self.p1_time


class PoseCompare(object):
    logger = _logger

    def __init__(self,
                 file_test: Union[DataLoader, str], file_reference: Union[DataLoader, str], ignore_index: bool = False,
                 output_dir: str = None, prefix: str = '',
                 time_range: TimeRange = None, max_messages: int = None,
                 time_axis: str = 'relative', test_device_name=None, reference_device_name=None):
        """!
        @brief Create an analyzer for the comparing the pose from two p1log files.

        @param file_test A @ref DataLoader instance, or the path to a file to be loaded as the device under test.
        @param file_reference A @ref DataLoader instance, or the path to a file to be loaded as the reference device.
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
        @param test_device_name If set, label test data with this device name.
        @param reference_device_name If set, label reference data with this device name.
        """
        self.params = {
            'time_range': time_range,
            'max_messages': max_messages,
            'show_progress': True,
            'return_numpy': True
        }

        if isinstance(file_test, str):
            self.test_pose = DataLoader(file_test, ignore_index=ignore_index).read(
                message_types=[PoseMessage], **self.params)[PoseMessage.MESSAGE_TYPE]
        else:
            self.test_pose = file_test.read(message_types=[PoseMessage], **self.params)[PoseMessage.MESSAGE_TYPE]

        if len(self.test_pose.p1_time) == 0:
            raise ValueError('Test log did not contain pose data.')

        if isinstance(file_reference, str):
            # Check if this is a CSV file and parse if needed.
            if re.match(r'.*novatel.*\.csv', os.path.basename(file_reference)):
                # Perform correct action
                data = np.genfromtxt(file_reference, delimiter=',', skip_header=1)
                # Extract necessary data.
                # Convert GPS time to P1 time.
                gps_time = data[:, 0]
                lla_deg = data[:, [1,2,4]].T
                height_msl_m = data[:, 3]
                pos_type = data[:, 5]
                solution_status = data[:, 6]
                time_status = data[:, 7]
                lla_std_dev_m = data[:, [8,9,10]].T

                self.reference_pose = NovatelData(gps_time,
                                                  pos_type,
                                                  lla_deg,
                                                  lla_std_dev_m)
            else:
                self.reference_pose = DataLoader(file_reference, ignore_index=ignore_index).read(
                    message_types=[PoseMessage], **self.params)[PoseMessage.MESSAGE_TYPE]
        else:
            self.reference_pose = file_reference.read(
                message_types=[PoseMessage], **self.params)[PoseMessage.MESSAGE_TYPE]

        if len(self.reference_pose.p1_time) == 0:
            raise ValueError('Reference log did not contain pose data.')

        self.test_data_name = 'Test'
        if test_device_name:
            self.test_data_name += ' ' + test_device_name

        self.reference_data_name = 'Reference'
        if reference_device_name:
            self.reference_data_name += ' ' + reference_device_name

        self.data_names = [
            self.test_data_name,
            self.reference_data_name,
        ]

        self.output_dir = output_dir
        self.prefix = prefix

        gps_time_test = self.test_pose.gps_time
        valid_gps_time = gps_time_test[np.isfinite(gps_time_test)]
        if len(valid_gps_time) == 0:
            raise ValueError('Test data had no valid GPS Times.')

        if np.all(self.test_pose.solution_type == SolutionType.Invalid):
            raise ValueError(f'Test data had no valid position solutions.')

        if time_axis in ('relative', 'rel'):
            self.time_axis = 'relative'
            self.t0 = valid_gps_time[0]
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

        self.pose_index_maps = self._get_log_pose_mapping()

        if len(self.pose_index_maps[0]) == 0:
            raise ValueError('Test and reference logs did not have overlapping GPS times.')

    def _get_log_pose_mapping(self):
        # intersect1d implicitly ignore NaNs.
        gps_matches = np.intersect1d(self.test_pose.gps_time, self.reference_pose.gps_time, return_indices=True)

        # [matched_indices_log_test, matched_indices_log_reference]
        return gps_matches[1:]

    def plot_solution_type(self):
        """!
        @brief Plot the solution type over time.
        """
        if self.output_dir is None:
            return

        # Setup the figure.
        figure = make_subplots(rows=1, cols=1, print_grid=False, shared_xaxes=True, subplot_titles=['Solution Type'])

        figure['layout']['xaxis'].update(title=self.gps_time_label)
        figure['layout']['yaxis1'].update(title="Solution Type",
                                          ticktext=['%s (%d)' % (e.name, e.value) for e in SolutionType],
                                          tickvals=[e.value for e in SolutionType])

        for name, pose_data in zip(self.data_names, (self.test_pose, self.reference_pose)):
            time = pose_data.gps_time - float(self.t0)

            text = ["Time: %.3f sec (%.3f sec)" % (t, t + float(self.t0)) for t in time]
            figure.add_trace(go.Scattergl(x=time, y=pose_data.solution_type,
                             text=text, name=name, mode='markers'), 1, 1)

        self._add_figure(name="solution_type", figure=figure, title="Solution Type")


    def plot_position_std_dev(self):
        """!
        @brief Plot the solution type over time.
        """
        if self.output_dir is None:
            return

        # Setup the figure.
        figure = make_subplots(rows=1, cols=1, print_grid=False, shared_xaxes=True, subplot_titles=['Solution Type'])

        figure['layout']['xaxis'].update(title=self.gps_time_label)
        figure['layout']['yaxis1'].update(title="Position Standard Deviation (m)")

        for name, pose_data in zip(self.data_names, (self.test_pose, self.reference_pose)):
            valid_idx = ~np.any(np.isnan(pose_data.position_std_enu_m), axis=0)
            time = pose_data.gps_time[valid_idx] - float(self.t0)

            text = ["Time: %.3f sec (%.3f sec)" % (t, t + float(self.t0)) for t in time]
            combined_std_dev_m = np.sqrt(np.sum(np.square(pose_data.position_std_enu_m[:, valid_idx]), axis=0))
            figure.add_trace(go.Scattergl(x=time, y=combined_std_dev_m,
                             text=text, name=name, mode='markers'), 1, 1)

        self._add_figure(name="position_std_dev", figure=figure, title="Position Standard Deviation")

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

        # Add data to the map.
        map_data = []

        for i, pose_data in enumerate((self.test_pose, self.reference_pose)):
            log_name = self.data_names[i]

            # Remove invalid solutions.
            valid_idx = np.logical_and(~np.isnan(pose_data.gps_time), pose_data.solution_type != SolutionType.Invalid)
            if not np.any(valid_idx):
                self.logger.info(f'No valid position solutions detected in {log_name}.')
                return

            time = pose_data.gps_time[valid_idx] - float(self.t0)
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
                    map_data.append(go.Scattermapbox(lat=[np.nan], lon=[np.nan],
                                    name=name, visible='legendonly', **style))

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

    def _plot_pose_error(self, time, solution_type, error_enu_m, std_enu_m):
        """!
        @brief Generate a plot of pose ENU error over time.
        """
        if self.output_dir is None:
            return

        time_figure = make_subplots(rows=4, cols=1, print_grid=False, shared_xaxes=True,
                                    subplot_titles=['3D', 'East', 'North', 'Up'])
        time_figure['layout'].update(showlegend=True, modebar_add=['v1hovermode'],
                                     title=f'{self.test_data_name} Vs. {self.reference_data_name}')
        for i in range(4):
            time_figure['layout']['xaxis%d' % (i + 1)].update(title=self.gps_time_label, showticklabels=True)
        time_figure['layout']['yaxis1'].update(title="Error (m)")
        time_figure['layout']['yaxis2'].update(title="Error (m)")
        time_figure['layout']['yaxis3'].update(title="Error (m)")
        time_figure['layout']['yaxis4'].update(title="Error (m)")

        # Plot the data.
        def _plot_data(name, idx, marker_style=None):
            style = {'mode': 'markers', 'marker': {'size': 8}, 'showlegend': True, 'legendgroup': name,
                     'hoverlabel': {'namelength': -1}}
            if marker_style is not None:
                style['marker'].update(marker_style)

            if np.any(idx):
                text = ["Time: %.3f sec (%.3f sec)<br>Delta (ENU): (%.2f, %.2f, %.2f) m"
                        "<br>Std (ENU): (%.2f, %.2f, %.2f) m" %
                        (t, t + float(self.t0), *delta, *std)
                        for t, delta, std in zip(time[idx], error_enu_m[:, idx].T, std_enu_m[:, idx].T)]

                time_figure.add_trace(go.Scattergl(x=time[idx], y=self.error_3d_m[idx],
                                                   name=name, text=text, **style), 1, 1)
                style['showlegend'] = False
                time_figure.add_trace(go.Scattergl(x=time[idx], y=error_enu_m[0, idx], name=name,
                                                   text=text, **style), 2, 1)
                time_figure.add_trace(go.Scattergl(x=time[idx], y=error_enu_m[1, idx], name=name,
                                                   text=text, **style), 3, 1)
                time_figure.add_trace(go.Scattergl(x=time[idx], y=error_enu_m[2, idx], name=name,
                                                   text=text, **style), 4, 1)
            else:
                # If there's no data, draw a dummy trace so it shows up in the legend anyway.
                time_figure.add_trace(go.Scattergl(x=[np.nan], y=[np.nan], name=name, visible='legendonly', **style),
                                      1, 1)

        for type, info in _SOLUTION_TYPE_MAP[0].items():
            _plot_data(info.name, solution_type == type, marker_style=info.style)

        self._add_figure(name=f"pose_error", figure=time_figure, title=f"Pose Error: vs. Time")

    def generate_pose_error(self, skip_plot: bool, no_reference_filter=False):
        """!
        @brief Generate a plot of pose error over time.
        """
        if self.output_dir is None:
            return

        # Assume tha solution types indicate comparable performance between data sets.
        reference_solution_types = self.reference_pose.solution_type[self.pose_index_maps[1]]
        if not no_reference_filter:
            reference_fixed_or_better = reference_solution_types == SolutionType.RTKFixed
            reference_float_or_better = np.logical_or(
                reference_fixed_or_better, reference_solution_types == SolutionType.RTKFloat)
            reference_standalone_or_better = np.logical_or(
                reference_float_or_better, reference_solution_types == SolutionType.AutonomousGPS)
            reference_dr_or_better = np.logical_or(reference_standalone_or_better,
                                                reference_solution_types == SolutionType.Integrate)
        else:
            reference_fixed_or_better = reference_solution_types != SolutionType.Invalid
            reference_float_or_better = reference_fixed_or_better
            reference_standalone_or_better = reference_fixed_or_better
            reference_dr_or_better = reference_fixed_or_better

        test_solution_types = self.test_pose.solution_type[self.pose_index_maps[0]]
        valid_fixed = np.logical_and(test_solution_types == SolutionType.RTKFixed, reference_fixed_or_better)
        valid_float = np.logical_and(test_solution_types == SolutionType.RTKFloat, reference_float_or_better)
        valid_standalone = np.logical_and(
            test_solution_types == SolutionType.AutonomousGPS, reference_standalone_or_better)
        valid_dr = np.logical_and(test_solution_types == SolutionType.Integrate, reference_dr_or_better)

        # Remove solutions without reliable reference.
        valid_idx = valid_fixed | valid_float | valid_standalone | valid_dr
        if not np.any(valid_idx):
            self.logger.info('No valid position solutions detected. Skipping error plots.')
            return

        test_gps_times = self.test_pose.gps_time[self.pose_index_maps[0]]
        test_std_enu_m = self.test_pose.position_std_enu_m[:, self.pose_index_maps[0]]
        test_lla_deg = self.test_pose.lla_deg[:, self.pose_index_maps[0]]
        valid_test_lla_deg = test_lla_deg[:, valid_idx]
        valid_test_ecef = np.array(geodetic2ecef(
            lat=test_lla_deg[0, valid_idx], lon=test_lla_deg[1, valid_idx], alt=test_lla_deg[2, valid_idx], deg=True))

        reference_lla_deg = self.reference_pose.lla_deg[:, self.pose_index_maps[1]]
        valid_reference_ecef = np.array(geodetic2ecef(
            lat=reference_lla_deg[0, valid_idx],
            lon=reference_lla_deg[1, valid_idx],
            alt=reference_lla_deg[2, valid_idx],
            deg=True))

        time = test_gps_times[valid_idx] - float(self.t0)
        solution_type = test_solution_types[valid_idx]
        std_enu_m = test_std_enu_m[:, valid_idx]

        error_ecef_m = valid_test_ecef - valid_reference_ecef
        c_enu_ecef = get_enu_rotation_matrix(*valid_test_lla_deg[0:2, 0], deg=True)
        error_enu_m = c_enu_ecef.dot(error_ecef_m)

        self.error_gps_times = test_gps_times[valid_idx]
        self.error_3d_m = np.linalg.norm(error_enu_m, axis=0)
        self.error_2d_m = np.linalg.norm(error_enu_m[:2], axis=0)
        self.error_solution_types = solution_type

        if not skip_plot:
            self._plot_pose_error(time, solution_type, error_enu_m, std_enu_m)

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

    def _set_data_summary(self):
        devices_solution_cdf = []
        totals = []
        for pose_index_map, pose_data in zip(self.pose_index_maps, (self.test_pose, self.reference_pose)):
            solution_types = pose_data.solution_type[pose_index_map]
            device_solution_cdf = {}
            device_solution_cdf['RTK Fixed'] = np.sum(solution_types == SolutionType.RTKFixed)
            device_solution_cdf['RTK Float'] = np.sum(
                solution_types == SolutionType.RTKFloat) + device_solution_cdf['RTK Fixed']
            # DGPS is just used by native receiver output?
            device_solution_cdf['Standalone'] = np.sum(
                solution_types == SolutionType.AutonomousGPS) + np.sum(solution_types == SolutionType.DGPS) + device_solution_cdf['RTK Float']
            device_solution_cdf['Integrate'] = np.sum(
                solution_types == SolutionType.Integrate) + device_solution_cdf['Standalone']
            total = device_solution_cdf['Integrate'] + np.sum(solution_types == SolutionType.Invalid)
            if total != len(solution_types):
                _logger.warning(
                    f'Unexpected SolutionTypes in: {[_SOLUTION_TYPE_MAP[0][k].name for k in np.unique(solution_types)]}')

            devices_solution_cdf.append(device_solution_cdf)
            totals.append(total)

        types = list(devices_solution_cdf[0].keys())
        counts = []
        percents = []
        for i in range(2):
            counts.append([devices_solution_cdf[i][t] for t in types])
            percents.append([devices_solution_cdf[i][t] / totals[i] * 100.0 for t in types])
        solution_type_table = _data_to_table(['Position Type', 'Test Count', 'Test Percent', 'Reference Count', 'Reference Percent'], [
                                             types, counts[0], percents[0], counts[1], percents[1]], round_decimal_places=2)

        self.percent_solution_type_reference_or_better = {t: devices_solution_cdf[0][t] / devices_solution_cdf[1][t] * 100.0 for t in types}

        # Debug time mapping between logs
        matched_p1_time_a = self.test_pose.p1_time[self.pose_index_maps[0]]
        matched_p1_time_b = self.reference_pose.p1_time[self.pose_index_maps[1]]
        p1_offsets = matched_p1_time_a - matched_p1_time_b
        log_b_p1_time = self.reference_pose.p1_time + \
            np.interp(np.arange(len(self.reference_pose.p1_time)), self.pose_index_maps[1], p1_offsets)
        log_a_t0 = self.test_pose.p1_time[0]
        log_b_t0 = log_b_p1_time[0]
        log_a_end = self.test_pose.p1_time[-1]
        log_b_end = log_b_p1_time[-1]

        test_pose_rate = np.round(np.median(np.diff(self.test_pose.gps_time[~np.isnan(self.test_pose.gps_time)])), 4)
        test_start_gps = self.test_pose.gps_time[self.pose_index_maps[0][0]]
        test_end_gps = self.test_pose.gps_time[self.pose_index_maps[0][-1]]
        expected_test_gps_epochs = np.round((test_end_gps - test_start_gps) / test_pose_rate)
        actual_test_gps_epochs = self.pose_index_maps[0][-1] - self.pose_index_maps[0][0]
        self.missing_test_gps_epochs = int(expected_test_gps_epochs - actual_test_gps_epochs)

        data = [[], []]
        data[0].append(self.test_data_name + ' Log Start')
        data[1].append(log_a_t0)
        data[0].append(self.reference_data_name + ' Log Start')
        data[1].append(log_b_t0)
        data[0].append(self.test_data_name + ' Log Duration')
        data[1].append(log_a_end - log_a_t0)
        data[0].append(self.reference_data_name + ' Log Duration')
        data[1].append(log_b_end - log_b_t0)
        data[0].append('Matched GPS Epochs')
        data[1].append(len(matched_p1_time_a))
        data[0].append('Missing Test GPS Epochs')
        data[1].append(self.missing_test_gps_epochs)
        data[0].append('Min P1 Time Offset')
        data[1].append(np.min(p1_offsets))
        data[0].append('Max P1 Time Offset')
        data[1].append(np.max(p1_offsets))

        time_table = _data_to_table(['Description', 'Time'], data, round_decimal_places=2)

        columns = ['Error Metric (m)', 'Mean_', 'Median', 'Min__', 'Max__', "Std"]
        data = []

        def get_stats(label, values):
            if len(values) == 0:
                return [label] + ['NA'] * 5
            else:
                return [label, np.mean(values), np.median(values), np.min(values), np.max(values), np.std(values)]
        data.append(get_stats('2D [All]', self.error_2d_m))
        data.append(get_stats('3D [All]', self.error_3d_m))
        data.append(get_stats('3D [fixed]', self.error_3d_m[self.error_solution_types == SolutionType.RTKFixed]))
        data.append(get_stats('3D [float]', self.error_3d_m[self.error_solution_types == SolutionType.RTKFloat]))
        data.append(get_stats('3D [standalone]',
                    self.error_3d_m[self.error_solution_types == SolutionType.AutonomousGPS]))
        data.append(get_stats('3D [dr]', self.error_3d_m[self.error_solution_types == SolutionType.Integrate]))
        error_table = _data_to_table(columns, data, row_major=True, round_decimal_places=2)

        self.summary += f"""
<h1>Comparison of {self.test_data_name} to {self.reference_data_name}</h1>

{time_table}

<h1>Solution Type CDF</h1>
{solution_type_table}

{error_table}
"""
        return

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
        'log_test',
        help="The first log to be read. May be one of:\n"
             "- The path to a .p1log file or a file containing FusionEngine messages and other content\n"
             "- The path to a FusionEngine log directory\n"
             "- A pattern matching a FusionEngine log directory under the specified base directory "
             "(see find_fusion_engine_log() and --log-base-dir)")
    log_group.add_argument(
        'log_reference',
        help="The second log to be read. May be one of:\n"
             "- The path to a .p1log file or a file containing FusionEngine messages and other content\n"
             "- The path to a FusionEngine log directory\n"
             "- A pattern matching a FusionEngine log directory under the specified base directory "
             "(see find_fusion_engine_log() and --log-base-dir)")
    log_group.add_argument('--reference-device-name', default=None, help='Label to apply to reference data.')
    log_group.add_argument('--test-device-name', default=None, help='Label to apply to test data.')

    output_group = parser.add_argument_group('Output Control')
    output_group.add_argument(
        '--no-index', action=ExtendedBooleanAction,
        help="Do not automatically open the plots in a web browser.")
    output_group.add_argument(
        '--skip-plots', action=ExtendedBooleanAction,
        help="Do not generate plots.")
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

    analysis_group = parser.add_argument_group('Analysis Control')
    analysis_group.add_argument(
        '--no-reference-filter', action=ExtendedBooleanAction,
        help="If set, don't filter limit the reference used for error calculation to portions where the reference "
             "solution type matches or exceeds the test device.")

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
    input_path_test, output_dir, log_id = locate_log(input_path=options.log_test, log_base_dir=options.log_base_dir,
                                                     return_output_dir=True, return_log_id=True,
                                                     load_original=options.original)

    input_path_reference = locate_log(input_path=options.log_reference, log_base_dir=options.log_base_dir,
                                      load_original=options.original)

    if input_path_test is None or input_path_reference is None:
        # locate_log() will log an error.
        sys.exit(1)

    if log_id is None:
        _logger.info('Loading A: %s , B: %s.' % (input_path_test, input_path_reference))

    if options.output is None:
        if log_id is not None:
            output_dir = os.path.join(output_dir, 'plot_pose_compare')
    else:
        output_dir = options.output

    # Read pose data from the file.
    analyzer = PoseCompare(file_test=input_path_test, file_reference=input_path_reference, output_dir=output_dir, ignore_index=options.ignore_index,
                           prefix=options.prefix + '.' if options.prefix is not None else '',
                           time_range=time_range, time_axis=options.time_axis, test_device_name=options.test_device_name, reference_device_name=options.reference_device_name)

    if not options.skip_plots:
        analyzer.plot_solution_type()
        analyzer.plot_position_std_dev()
        analyzer.plot_map(mapbox_token=options.mapbox_token)
    analyzer.generate_pose_error(options.skip_plots, no_reference_filter=options.no_reference_filter)

    analyzer.generate_index(auto_open=not options.no_index)

    _logger.info("Output stored in '%s'." % os.path.abspath(output_dir))
    return analyzer

if __name__ == "__main__":
    main()
