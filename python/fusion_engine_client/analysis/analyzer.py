#!/usr/bin/env python3

from typing import Tuple, Union

from argparse import ArgumentParser
import copy
import logging
import os
import sys
import webbrowser

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

from ..messages.core import *
from ..messages.internal import *
from .attitude import get_enu_rotation_matrix
from .file_reader import FileReader
from ..utils.log import find_p1log_file

_logger = logging.getLogger('point_one.fusion_engine.analysis.analyzer')


class Analyzer(object):
    logger = _logger

    def __init__(self, file: Union[FileReader, str], output_dir: str = None, ignore_index: bool = False,
                 prefix: str = '',
                 time_range: Tuple[Union[float, Timestamp], Union[float, Timestamp]] = None,
                 absolute_time: bool = False,
                 max_messages: int = None):
        """!
        @brief Create an analyzer for the specified log.

        @param file A @ref FileReader instance, or the path to a file to be loaded.
        @param output_dir The directory where output will be stored.
        @param ignore_index If `True`, do not use the `.p1i` index file if present, and instead regenerate it from the
               `.p1log` data file.
        @param prefix An optional prefix to be appended to the generated filenames.
        @param time_range An optional length-2 tuple specifying desired start and end bounds on the data timestamps.
               Both the start and end values may be set to `None` to read all data.
        @param absolute_time If `True`, interpret the timestamps in `time_range` as absolute P1 times. Otherwise, treat
               them as relative to the first message in the file.
        @param max_messages If set, read up to the specified maximum number of messages. Applies across all message
               types.
        """
        if isinstance(file, str):
            self.reader = FileReader(file, regenerate_index=ignore_index)
        else:
            self.reader = file

        self.output_dir = output_dir
        self.prefix = prefix

        self.params = {
            'time_range': time_range,
            'absolute_time': absolute_time,
            'max_messages': max_messages,
            'show_progress': True,
            'return_numpy': True
        }

        self.t0 = self.reader.t0
        self.system_t0 = None

        self.plots = {}
        self.summary = ''

        if self.output_dir is not None:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)

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
            self.logger.info('No pose data available.')
            return

        time = pose_data.p1_time - float(self.t0)

        valid_idx = np.logical_and(~np.isnan(pose_data.p1_time), pose_data.solution_type != SolutionType.Invalid)
        if not np.any(valid_idx):
            self.logger.info('No valid position solutions detected.')
            return

        first_idx = np.argmax(valid_idx)
        c_enu_ecef = get_enu_rotation_matrix(*pose_data.lla_deg[0:2, first_idx], deg=True)

        # Setup the figure.
        figure = make_subplots(rows=2, cols=3, print_grid=False, shared_xaxes=True,
                               subplot_titles=['Attitude (YPR)', 'ENU Displacement', 'Body Velocity',
                                               'Attitude Std', 'ENU Position Std', 'Velocity Std'])

        figure['layout'].update(showlegend=True)
        figure['layout']['xaxis'].update(title="Time (sec)")
        for i in range(6):
            figure['layout']['xaxis%d' % (i + 1)].update(showticklabels=True)
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

        figure.add_trace(go.Scattergl(x=time, y=pose_data.velocity_body_mps[0, :], name='X', legendgroup='x',
                                      showlegend=False, mode='lines', line={'color': 'red'}),
                         2, 3)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.velocity_body_mps[1, :], name='Y', legendgroup='y',
                                      showlegend=False, mode='lines', line={'color': 'green'}),
                         2, 3)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.velocity_body_mps[2, :], name='Z', legendgroup='z',
                                      showlegend=False, mode='lines', line={'color': 'blue'}),
                         2, 3)

        self._add_figure(name="pose", figure=figure, title="Vehicle Pose")

    def plot_map(self, mapbox_token):
        """!
        @brief Plot a map of the position data.
        """
        if self.output_dir is None:
            return

        mapbox_token = self.get_mapbox_token(mapbox_token)
        if mapbox_token is None:
            self.logger.info('Mapbox token not specified. Skipping map display.')
            return

        # Read the pose data.
        result = self.reader.read(message_types=[PoseMessage], **self.params)
        pose_data = result[PoseMessage.MESSAGE_TYPE]

        if len(pose_data.p1_time) == 0:
            self.logger.info('No pose data available.')
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
                map_data.append(go.Scattermapbox(lat=[np.nan], lon=[np.nan], name=name, **style))

        _plot_data('RTK Fixed', solution_type == SolutionType.RTKFixed, {'color': 'orange'})
        _plot_data('Non-Fixed', solution_type != SolutionType.RTKFixed, {'color': 'red'})

        # Create the map.
        layout = go.Layout(
            autosize=True,
            hovermode='closest',
            title='Vehicle Trajectory',
            mapbox=dict(
                accesstoken=mapbox_token,
                bearing=0,
                center=dict(
                    lat=lla_deg[0, 0],
                    lon=lla_deg[1, 0],
                ),
                pitch=0,
                zoom=18,
                style='satellite-streets'
            )
        )

        figure = go.Figure(data=map_data, layout=layout)
        figure['layout'].update(showlegend=True)

        self._add_figure(name="map", figure=figure, title="Vehicle Trajectory (Map)")

    def plot_imu(self):
        """!
        @brief Plot the IMU data.
        """
        if self.output_dir is None:
            return

        # Read the data.
        result = self.reader.read(message_types=[IMUMeasurement], **self.params)
        data = result[IMUMeasurement.MESSAGE_TYPE]

        if len(data.p1_time) == 0:
            self.logger.info('No IMU data available.')
            return

        time = data.p1_time - float(self.t0)

        figure = make_subplots(rows=2, cols=1, print_grid=False, shared_xaxes=True,
                               subplot_titles=['Acceleration', 'Gyro'])

        figure['layout'].update(showlegend=True)
        figure['layout']['xaxis'].update(title="Time (sec)")
        figure['layout']['xaxis1'].update(showticklabels=True)
        figure['layout']['xaxis2'].update(showticklabels=True)
        figure['layout']['yaxis1'].update(title="Acceleration (m/s^2)")
        figure['layout']['yaxis1'].update(title="Rotation Rate (rad/s)")

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

        self._add_figure(name="imu", figure=figure, title="IMU Measurements")

    def plot_system_status_profiling(self):
        """!
        @brief Plot system status profiling data.
        """
        if self.output_dir is None:
            return

        # Read the data.
        result = self.reader.read(message_types=[ProfileSystemStatusMessage], remove_nan_times=False, **self.params)
        data = result[ProfileSystemStatusMessage.MESSAGE_TYPE]

        if len(data.system_time) == 0:
            self.logger.info('No system profiling data available.')
            return

        time = data.system_time - self.reader.get_system_t0()

        figure = make_subplots(rows=3, cols=1, print_grid=False, shared_xaxes=True,
                               subplot_titles=['CPU Usage', 'Memory Usage', 'Queue Depth'])

        figure['layout'].update(showlegend=True)
        figure['layout']['xaxis'].update(title="System Time (sec)")
        for i in range(3):
            figure['layout']['xaxis%d' % (i + 1)].update(showticklabels=True)
        figure['layout']['yaxis1'].update(title="CPU (%)", range=[0, 100])
        figure['layout']['yaxis2'].update(title="Memory (MB)")
        figure['layout']['yaxis3'].update(title="# Entries")

        figure.add_trace(go.Scattergl(x=time, y=data.total_cpu_usage, name='Total CPU Usage',
                                      mode='lines', line={'color': 'black', 'width': 4}),
                         1, 1)
        for i in range(data.cpu_usage_per_core.shape[0]):
            color = plotly.colors.DEFAULT_PLOTLY_COLORS[i % len(plotly.colors.DEFAULT_PLOTLY_COLORS)]
            figure.add_trace(go.Scattergl(x=time, y=data.cpu_usage_per_core[i, :], name='CPU %d Usage' % i,
                                          mode='lines', line={'color': color, 'dash': 'dash'}),
                             1, 1)

        figure.add_trace(go.Scattergl(x=time, y=data.used_memory_bytes / float(1024 * 1024), name='Used Memory',
                                      mode='lines', line={'color': 'blue'}),
                         2, 1)

        figure.add_trace(go.Scattergl(x=time, y=data.propagator_depth, name='Propagator',
                                      mode='lines', line={'color': 'red'}),
                         3, 1)

        figure.add_trace(go.Scattergl(x=time, y=data.dq_depth, name='Delay Queue',
                                      mode='lines', line={'color': 'green'}),
                         3, 1)

        figure.add_trace(go.Scattergl(x=time, y=data.log_queue_depth, name='Log Queue',
                                      mode='lines', line={'color': 'blue'}),
                         3, 1)

        self._add_figure(name="profile_system_status", figure=figure, title="Profiling: System Status")

    def plot_execution_stats_profiling(self):
        """!
        @brief Plot execution profiling stats.
        """
        if self.output_dir is None:
            return

        # Read the data.
        result = self.reader.read(message_types=[ProfileExecutionStatsMessage], remove_nan_times=False, **self.params)
        data = result[ProfileExecutionStatsMessage.MESSAGE_TYPE]

        if len(data.system_time_sec) == 0:
            self.logger.info('No execution profiling stats data available.')
            return

        # Read the last task name message to map IDs to names.
        params = copy.deepcopy(self.params)
        params['max_messages'] = -1
        result = self.reader.read(message_types=[ProfileExecutionStatsMessage.DEFINITION_TYPE], remove_nan_times=False,
                                  **params)
        if len(result[ProfileExecutionStatsMessage.DEFINITION_TYPE].messages) != 0:
            definition = result[ProfileExecutionStatsMessage.DEFINITION_TYPE].messages[0]
            id_to_name = definition.to_dict()
        else:
            self.logger.warning('No execution profiling stats names received.')
            id_to_name = {}

        time = data.system_time_sec - self.reader.get_system_t0()

        figure = make_subplots(rows=3, cols=1, print_grid=False, shared_xaxes=True,
                               subplot_titles=['Average Processing Time', 'Max Processing Time',
                                               'Number of Executions Per Update'])

        figure['layout'].update(showlegend=True)
        figure['layout']['xaxis'].update(title="System Time (sec)")
        for i in range(3):
            figure['layout']['xaxis%d' % (i + 1)].update(showticklabels=True)
        figure['layout']['yaxis1'].update(title="Processing Time (ms)")
        figure['layout']['yaxis2'].update(title="Processing Time (ms)")
        figure['layout']['yaxis3'].update(title="Number of Executions")

        for i in range(len(data.running_time_ns)):
            color = plotly.colors.DEFAULT_PLOTLY_COLORS[i % len(plotly.colors.DEFAULT_PLOTLY_COLORS)]
            trace_name = id_to_name.get(i, f'unknown_{i}')
            figure.add_trace(go.Scattergl(x=time, y=data.running_time_ns[i] / data.run_count[i] / 1e6,
                                          name=trace_name, legendgroup=f'{i}',
                                          mode='lines', line={'color': color}),
                             1, 1)
            figure.add_trace(go.Scattergl(x=time, y=data.max_run_time_ns[i] / 1e6,
                                          name=trace_name, legendgroup=f'{i}', showlegend=False,
                                          mode='lines', line={'color': color}),
                             2, 1)
            figure.add_trace(go.Scattergl(x=time, y=data.run_count[i],
                                          name=trace_name, legendgroup=f'{i}', showlegend=False,
                                          mode='lines', line={'color': color}),
                             3, 1)

        self._add_figure(name="profile_execution_stats", figure=figure, title="Profiling: Execution Stats")

    def plot_counter_profiling(self):
        """!
        @brief Plot execution profiling stats.
        """
        if self.output_dir is None:
            return

        # Read the data.
        result = self.reader.read(message_types=[ProfileCounterMessage], remove_nan_times=False, **self.params)
        data = result[ProfileCounterMessage.MESSAGE_TYPE]

        if len(data.system_time_sec) == 0:
            self.logger.info('No execution profiling stats data available.')
            return

        # Read the last task name message to map IDs to names.
        params = copy.deepcopy(self.params)
        params['max_messages'] = -1
        result = self.reader.read(message_types=[ProfileCounterMessage.DEFINITION_TYPE], remove_nan_times=False,
                                  **params)
        if len(result[ProfileCounterMessage.DEFINITION_TYPE].messages) != 0:
            definition = result[ProfileCounterMessage.DEFINITION_TYPE].messages[0]
            id_to_name = definition.to_dict()
        else:
            self.logger.warning('No execution profiling stats names received.')
            id_to_name = {}

        delay_queue_count_idx = None
        delay_queue_ns_idx = None
        msg_buff_map = []
        measurement_map = []
        for k, v in id_to_name.items():
            if v == 'delay_queue_count':
                delay_queue_count_idx = k
            elif v == 'delay_queue_ns':
                delay_queue_ns_idx = k
            elif v.startswith('msg_buff_'):
                 msg_buff_map.append((k, v))
            elif v.startswith('meas_'):
                measurement_map.append((k, v))

        if (delay_queue_count_idx is None or delay_queue_ns_idx is None):
            self.logger.info('Delay queue depth data missing.')
            return

        time = data.system_time_sec - self.reader.get_system_t0()

        figure = make_subplots(rows=4, cols=1, print_grid=False, shared_xaxes=True,
                               subplot_titles=['Delay Queue Depth Measurements', 'Delay Queue Depth Age',
                                               'Message Buffer Free Space', 'Measurement Rates'])

        figure['layout'].update(showlegend=True)
        figure['layout']['xaxis'].update(title="System Time (sec)")
        for i in range(2):
            figure['layout']['xaxis%d' % (i + 1)].update(showticklabels=True)
        figure['layout']['yaxis1'].update(title="Queue Depth (measurements)")
        figure['layout']['yaxis2'].update(title="Queue Age (ms)")
        figure['layout']['yaxis3'].update(title="Buffer Free (bytes)")
        figure['layout']['yaxis4'].update(title="Message Rate (Hz)")

        figure.add_trace(go.Scattergl(x=time, y=data.counters[delay_queue_count_idx], showlegend=False,
                                      mode='lines', line={'color': 'red'}),
                         1, 1)
        figure.add_trace(go.Scattergl(x=time, y=data.counters[delay_queue_ns_idx] / 1e6, showlegend=False,
                                      mode='lines', line={'color': 'blue'}),
                         2, 1)

        for i in range(len(msg_buff_map)):
            color = plotly.colors.DEFAULT_PLOTLY_COLORS[i % len(plotly.colors.DEFAULT_PLOTLY_COLORS)]
            idx, buffer_name = msg_buff_map[i]
            figure.add_trace(go.Scattergl(x=time, y=data.counters[idx], name=f'{buffer_name}',
                                            mode='lines', line={'color': color}),
                             3, 1)

        for i in range(len(measurement_map)):
            color = plotly.colors.DEFAULT_PLOTLY_COLORS[i % len(plotly.colors.DEFAULT_PLOTLY_COLORS)]
            idx, measurement_name = measurement_map[i]
            figure.add_trace(go.Scattergl(x=time, y=np.diff(data.counters[idx]) / np.diff(time),
                                          name=f'{measurement_name}', mode='lines', line={'color': color}),
                             4, 1)

        self._add_figure(name="profile_queue_depths", figure=figure, title="Profiling: Queue Depths")

    def plot_free_rtos_system_status_profiling(self):
        """!
        @brief Plot system status profiling data.
        """
        if self.output_dir is None:
            return

        # Read the data.
        result = self.reader.read(message_types=[ProfileFreeRtosSystemStatusMessage], remove_nan_times=False,
                                  **self.params)
        data = result[ProfileFreeRtosSystemStatusMessage.MESSAGE_TYPE]

        if len(data.system_time_sec) == 0:
            self.logger.info('No FreeRTOS system profiling data available.')
            return

        # Read the last task name message to map IDs to names.
        params = copy.deepcopy(self.params)
        params['max_messages'] = -1
        result = self.reader.read(message_types=[ProfileFreeRtosSystemStatusMessage.DEFINITION_TYPE],
                                  remove_nan_times=False, **params)
        if len(result[ProfileFreeRtosSystemStatusMessage.DEFINITION_TYPE].messages) != 0:
            definition = result[ProfileFreeRtosSystemStatusMessage.DEFINITION_TYPE].messages[0]
            id_to_name = definition.to_dict()
        else:
            self.logger.warning('No FreeRTOS task names received.')
            id_to_name = {}

        time = data.system_time_sec - self.reader.get_system_t0()

        figure = make_subplots(rows=3, cols=1, print_grid=False, shared_xaxes=True,
                               subplot_titles=['CPU Usage', 'Stack High Water Marks', 'Dynamic Memory Free'])

        figure['layout'].update(showlegend=True)
        figure['layout']['xaxis'].update(title="System Time (sec)")
        for i in range(3):
            figure['layout']['xaxis%d' % (i + 1)].update(showticklabels=True)
        figure['layout']['yaxis1'].update(title="CPU (%)", range=[0, 100])
        figure['layout']['yaxis2'].update(title="Memory Free (B)")
        figure['layout']['yaxis3'].update(title="Memory Free (KB)")

        for i in range(len(data.task_cpu_usage_percent)):
            color = plotly.colors.DEFAULT_PLOTLY_COLORS[i % len(plotly.colors.DEFAULT_PLOTLY_COLORS)]
            task_name = id_to_name.get(i, f'unknown_{i}')
            figure.add_trace(go.Scattergl(x=time, y=data.task_cpu_usage_percent[i],
                                          name='Task %s CPU Usage' % task_name, legendgroup=task_name,
                                          mode='lines', line={'color': color}),
                             1, 1)
            figure.add_trace(go.Scattergl(x=time, y=data.task_min_stack_free_bytes[i],
                                          name='Task %s Stack Free' % task_name, legendgroup=task_name,
                                          mode='lines', line={'color': color, 'dash': 'dash'}),
                             2, 1)

        figure.add_trace(go.Scattergl(x=time, y=data.heap_free_bytes / 1024.0, name='Heap',
                                      mode='lines', line={'color': 'red'}),
                         3, 1)
        figure.add_trace(go.Scattergl(x=time, y=data.sbrk_free_bytes / 1024.0, name='SBRK',
                                      mode='lines', line={'color': 'blue'}),
                         3, 1)

        self._add_figure(name="profile_freertos_system_status", figure=figure,
                         title="Profiling: FreeRTOS System Status")

    def plot_measurement_pipeline_profiling(self):
        """!
        @brief Plot measurement pipeline profiling data.
        """
        if self.output_dir is None:
            return

        # Read the pipeline data.
        result = self.reader.read(message_types=[ProfilePipelineMessage], **self.params)
        data = result[ProfilePipelineMessage.MESSAGE_TYPE]

        if len(data.system_time) == 0:
            self.logger.info('No measurement profiling data available.')
            return

        # Read the last pipeline definition message to map IDs to names.
        params = copy.deepcopy(self.params)
        params['max_messages'] = -1
        result = self.reader.read(message_types=[ProfilePipelineMessage.DEFINITION_TYPE], remove_nan_times=False,
                                  **params)
        if len(result[ProfilePipelineMessage.DEFINITION_TYPE].messages) != 0:
            definition = result[ProfilePipelineMessage.DEFINITION_TYPE].messages[0]
            id_to_name = definition.to_dict()
        else:
            id_to_name = {}

        figure = make_subplots(rows=1, cols=1, print_grid=False, shared_xaxes=True,
                               subplot_titles=['Pipeline Delay'])

        figure['layout'].update(showlegend=True)
        figure['layout']['xaxis'].update(title="System Time (sec)")
        figure['layout']['yaxis1'].update(title="Delay (sec)")

        for id, point_data in data.points.items():
            name = id_to_name.get(id, 'unknown_%s' % str(id))
            time_sec = point_data[0, :] - self.reader.get_system_t0()
            delay_sec = point_data[1, :]
            figure.add_trace(go.Scattergl(x=time_sec, y=delay_sec, name=name, mode='markers'), 1, 1)

        self._add_figure(name="profile_pipeline", figure=figure, title="Profiling: Measurement Pipeline")

    def plot_execution_profiling(self):
        """!
        @brief Plot code execution profiling data.
        """
        if self.output_dir is None:
            return

        # Read the pipeline data.
        result = self.reader.read(message_types=[ProfileExecutionMessage], remove_nan_times=False, **self.params)
        data = result[ProfileExecutionMessage.MESSAGE_TYPE]

        if len(data.points) == 0:
            self.logger.info('No execution profiling data available.')
            return

        # Read the last pipeline definition message to map IDs to names.
        params = copy.deepcopy(self.params)
        params['max_messages'] = -1
        result = self.reader.read(message_types=[ProfileExecutionMessage.DEFINITION_TYPE], remove_nan_times=False,
                                  **params)
        if len(result[ProfileExecutionMessage.DEFINITION_TYPE].messages) != 0:
            definition = result[ProfileExecutionMessage.DEFINITION_TYPE].messages[0]
            id_to_name = definition.to_dict()
        else:
            id_to_name = {}

        figure = make_subplots(rows=1, cols=1, print_grid=False, shared_xaxes=True,
                               subplot_titles=['Code Execution'])

        figure['layout'].update(showlegend=True)
        figure['layout']['xaxis'].update(title="System Time (sec)")
        figure['layout']['yaxis1'].update(title="Event")

        if len(id_to_name) != 0:
            figure.update_yaxes(
                ticktext=['%s (%d)' % (name, id) for id, name in id_to_name.items()],
                tickvals=list(id_to_name.keys()))

        for i, (id, point_data) in enumerate(data.points.items()):
            name = id_to_name.get(id, 'unknown_%s' % str(id))
            time_sec = (point_data[0, :] - self.reader.get_system_t0_ns()) * 1e-9
            action = point_data[1, :].astype(int)
            color = plotly.colors.DEFAULT_PLOTLY_COLORS[i % len(plotly.colors.DEFAULT_PLOTLY_COLORS)]

            idx = action == ProfileExecutionEntry.START
            if np.any(idx):
                figure.add_trace(go.Scattergl(x=time_sec[idx], y=[id] * np.sum(idx),
                                              name=name + ' (start)', legendgroup=id,
                                              mode='markers',
                                              marker={'color': color, 'size': 12, 'symbol': 'triangle-right'}),
                                 1, 1)

            idx = action == ProfileExecutionEntry.STOP
            if np.any(idx):
                figure.add_trace(go.Scattergl(x=time_sec[idx], y=[id] * np.sum(idx),
                                              name=name + ' (stop)', legendgroup=id,
                                              mode='markers',
                                              marker={'color': color, 'size': 12, 'symbol': 'triangle-left-open'}),
                                 1, 1)

        self._add_figure(name="profile_execution", figure=figure, title="Profiling: Code Execution")

    def generate_index(self, auto_open=True):
        """!
        @brief Generate an `index.html` page with links to all generated figures.

        @param auto_open If `True`, open the page automatically in a web browser.
        """
        if len(self.plots) == 0:
            self.logger.warning('No plots generated. Skipping index generation.')
            return

        self._set_data_summary()

        index_template = '''\
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
  <meta content="text/html; charset=ISO-8859-1" http-equiv="content-type">
  <title>%(title)s</title>
</head>
<body>
  %(links)s
  %(summary)s
</body>
</html>
'''
        links = ''
        title_to_name = {e['title']: n for n, e in self.plots.items()}
        titles = list(title_to_name.keys())
        titles.sort()
        for title in titles:
            name = title_to_name[title]
            entry = self.plots[name]
            link = '<br><a href="%s" target="_blank">%s</a>' % (entry['path'], title)
            links += link

        index_html = index_template % {
            'title': 'FusionEngine Output',
            'links': links,
            'summary': '<pre>' + self.summary.replace('\n', '<br>') + '</pre>'
        }

        index_path = os.path.join(self.output_dir, self.prefix + 'index.html')
        with open(index_path, 'w') as f:
            self.logger.info('Creating %s...' % index_path)
            f.write(index_html)

        if auto_open:
            self._open_browser(index_path)

    def _set_data_summary(self):
        # Generate an index file, which we need to calculate the log duration, in case it wasn't created earlier (i.e.,
        # we didn't read anything to plot.
        self.reader.generate_index()

        idx = ~np.isnan(self.reader.index['time'])
        time = self.reader.index['time'][idx]
        if len(time) >= 2:
            duration_sec = time[-1] - time[0]
        else:
            duration_sec = np.nan

        if self.summary != '':
            self.summary += '\n\n'

        message_table = """
<table>
  <tr>
    <td>Message Type</td>
    <td>Count</td>
  </tr>
"""
        message_types, message_counts = np.unique(self.reader.index['type'], return_counts=True)
        for t, c in zip(message_types, message_counts):
            message_table += """
  <tr>
    <td>%s</td>
    <td>%d</td>
  </tr>
""" % (MessageType.get_type_string(t), c)
        message_table += """
  <tr>
    <td><hr></td>
    <td><hr></td>
  </tr>
  <tr>
    <td>Total</td>
    <td>%d</td>
  </tr>
</table>
""" % len(self.reader.index)
        message_table = message_table.replace('\n', '')

        args = {
            'duration_sec': duration_sec,
            'message_table': message_table,
        }

        self.summary += """
Duration: %(duration_sec).1f seconds

%(message_table)s
""" % args

    def _add_figure(self, name, figure, title=None):
        if title is None:
            title = name

        if name in self.plots:
            raise ValueError('Plot "%s" already exists.' % name)
        elif name == 'index':
            raise ValueError('Plot name cannot be index.')

        path = os.path.join(self.output_dir, self.prefix + name + '.html')
        self.logger.info('Creating %s...' % path)

        plotly.offline.plot(
            figure,
            output_type='file',
            filename=path,
            include_plotlyjs=True,
            auto_open=False,
            show_link=False)

        self.plots[name] = {'title': title, 'path': path}

    def _open_browser(self, filename):
        try:
            webbrowser.open("file:///" + os.path.abspath(filename))
        except:
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


def main():
    parser = ArgumentParser(description="""\
Load and display information stored in a FusionEngine binary file.
""")
    parser.add_argument('--absolute-time', '--abs', action='store_true',
                        help="Interpret the timestamps in --time as absolute P1 times. Otherwise, treat them as "
                             "relative to the first message in the file.")
    parser.add_argument('--ignore-index', action='store_true',
                        help="If set, ignore the regenerate .p1i index file from the .p1log data file.")
    parser.add_argument('--imu', action='store_true',
                        help="Plot IMU data (slow).")
    parser.add_argument('--mapbox-token', metavar='TOKEN',
                        help="A Mapbox token to use when generating a map. If unspecified, the token will be read from "
                             "the MAPBOX_ACCESS_TOKEN or MapboxAccessToken environment variables if set. If no token "
                             "is available, a map will not be displayed.")
    parser.add_argument('--no-index', action='store_true',
                        help="Do not automatically open the plots in a web browser.")
    parser.add_argument('-o', '--output', type=str, metavar='DIR',
                        help="The directory where output will be stored. Defaults to the current directory, or to "
                             "'<log_dir>/plot_fusion_engine/' if reading from a log.")
    parser.add_argument('-p', '--prefix', metavar='PREFIX',
                        help="If specified, prepend each filename with PREFIX.")
    parser.add_argument('-t', '--time', type=str, metavar='[START][:END]',
                        help="The desired time range to be analyzed. Both start and end may be omitted to read from "
                             "beginning or to the end of the file. By default, timestamps are treated as relative to "
                             "the first message in the file. See --absolute-time.")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Print verbose/trace debugging messages.")

    parser.add_argument('--log-base-dir', metavar='DIR', default='/logs',
                        help="The base directory containing FusionEngine logs to be searched if a log pattern is"
                             "specified.")
    parser.add_argument('--original', action='store_true',
                        help='When loading from a log, load the recorded FusionEngine output file instead of playback '
                             'results.')
    parser.add_argument('log',
                        help="The log to be read. May be one of:\n"
                             "- The path to a .p1log file\n"
                             "- The path to a FusionEngine log directory\n"
                             "- A pattern matching a FusionEngine log directory under the specified base directory "
                             "(see find_fusion_engine_log() and --log-base-dir)")
    options = parser.parse_args()

    # Configure logging.
    if options.verbose >= 1:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s:%(lineno)d - %(message)s')
        logger = logging.getLogger('point_one.fusion_engine')
        logger.setLevel(logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')

    # Parse the time range.
    if options.time is not None:
        time_range = options.time.split(':')
        if len(time_range) == 0:
            time_range = [None, None]
        elif len(time_range) == 1:
            time_range.append(None)
        elif len(time_range) == 2:
            pass
        else:
            raise ValueError('Invalid time range specification.')

        for i in range(2):
            if time_range[i] is not None:
                if time_range[i] == '':
                    time_range[i] = None
                else:
                    time_range[i] = float(time_range[i])
                    if time_range[i] < 0.0:
                        time_range[i] = None
    else:
        time_range = None

    # Locate the input file and set the output directory.
    try:
        input_path, output_dir, log_id = find_p1log_file(options.log, return_output_dir=True, return_log_id=True,
                                                         log_base_dir=options.log_base_dir,
                                                         load_original=options.original)

        if log_id is None:
            _logger.info('Loading %s.' % os.path.basename(input_path))
        else:
            _logger.info('Loading %s from log %s.' % (os.path.basename(input_path), log_id))

        if input_path.endswith('.playback.p1log') or input_path.endswith('.playback.p1bin'):
            _logger.warning('Using .p1log file from log playback. If you want the originally recorded data, set '
                            '--original.')

        if options.output is None:
            if log_id is not None:
                output_dir = os.path.join(output_dir, 'plot_fusion_engine')
        else:
            output_dir = options.output
    except FileNotFoundError as e:
        _logger.error(str(e))
        sys.exit(1)

    # Read pose data from the file.
    analyzer = Analyzer(file=input_path, output_dir=output_dir, ignore_index=options.ignore_index,
                        prefix=options.prefix + '.' if options.prefix is not None else '',
                        time_range=time_range, absolute_time=options.absolute_time)

    analyzer.plot_pose()
    analyzer.plot_map(mapbox_token=options.mapbox_token)

    if options.imu:
        analyzer.plot_imu()

    analyzer.plot_system_status_profiling()
    analyzer.plot_free_rtos_system_status_profiling()
    analyzer.plot_measurement_pipeline_profiling()
    analyzer.plot_execution_profiling()
    analyzer.plot_execution_stats_profiling()
    analyzer.plot_counter_profiling()

    analyzer.generate_index(auto_open=not options.no_index)

    _logger.info("Output stored in '%s'." % os.path.abspath(output_dir))


if __name__ == "__main__":
    main()
