from typing import Tuple, Union

from argparse import ArgumentParser
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
    root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.append(root_dir)
    __package__ = "fusion_engine_client.analysis"

from ..messages.core import *
from .attitude import get_enu_rotation_matrix
from .file_reader import FileReader


class Analyzer(object):
    logger = logging.getLogger('point_one.fusion_engine.analysis.analyzer')

    def __init__(self, reader: FileReader, output_dir=None,
                 time_range: Tuple[Union[float, Timestamp], Union[float, Timestamp]] = None,
                 absolute_time: bool = False,
                 max_messages: int = None):
        self.reader = reader
        self.output_dir = output_dir

        self.params = {
            'time_range': time_range,
            'absolute_time': absolute_time,
            'max_messages': max_messages,
            'show_progress': True,
            'return_numpy': True
        }

        self.t0 = self.reader.t0

        self.plots = {}
        self.summary = ''

        if self.output_dir is not None:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)

    def plot_pose(self):
        if self.output_dir is None:
            return

        # Read the pose data.
        result = self.reader.read(message_types=[PoseMessage], **self.params)
        pose_data = result[PoseMessage.MESSAGE_TYPE]

        if len(pose_data.p1_time) == 0:
            self.logger.info('No pose data available.')
            return

        time = pose_data.p1_time - float(self.t0)
        c_enu_ecef = get_enu_rotation_matrix(*pose_data.lla_deg[0:2, 0], deg=True)

        # Setup the figure.
        figure = make_subplots(rows=2, cols=3, print_grid=False, shared_xaxes=True,
                               subplot_titles=['Attitude (YPR)', 'ENU Displacement', 'Body Velocity',
                                               'Attitude Std', 'ENU Position Std', 'Velocity Std'])

        figure['layout'].update(showlegend=True)
        figure['layout']['xaxis'].update(title="Time (sec)")
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
                                      mode='lines', line={'color': 'blue'}),
                         1, 1)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.ypr_deg[2, :], name='Roll', legendgroup='roll',
                                      mode='lines', line={'color': 'green'}),
                         1, 1)

        figure.add_trace(go.Scattergl(x=time, y=pose_data.ypr_std_deg[0, :], name='Yaw', legendgroup='yaw',
                                      showlegend=False, mode='lines', line={'color': 'red'}),
                         2, 1)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.ypr_std_deg[1, :], name='Pitch', legendgroup='pitch',
                                      showlegend=False, mode='lines', line={'color': 'blue'}),
                         2, 1)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.ypr_std_deg[2, :], name='Roll', legendgroup='roll',
                                      showlegend=False, mode='lines', line={'color': 'green'}),
                         2, 1)

        # Plot position/displacement.
        position_ecef_m = np.array(geodetic2ecef(lat=pose_data.lla_deg[0, :], lon=pose_data.lla_deg[1, :],
                                                 alt=pose_data.lla_deg[0, :], deg=True))
        displacement_ecef_m = position_ecef_m - position_ecef_m[:, 0].reshape(3, 1)
        displacement_enu_m = c_enu_ecef.dot(displacement_ecef_m)
        figure.add_trace(go.Scattergl(x=time, y=displacement_enu_m[0, :], name='East', legendgroup='e',
                                      mode='lines', line={'color': 'red'}),
                         1, 2)
        figure.add_trace(go.Scattergl(x=time, y=displacement_enu_m[1, :], name='North', legendgroup='n',
                                      mode='lines', line={'color': 'blue'}),
                         1, 2)
        figure.add_trace(go.Scattergl(x=time, y=displacement_enu_m[2, :], name='Up', legendgroup='u',
                                      mode='lines', line={'color': 'green'}),
                         1, 2)

        figure.add_trace(go.Scattergl(x=time, y=pose_data.position_std_enu_m[0, :], name='East', legendgroup='e',
                                      showlegend=False, mode='lines', line={'color': 'red'}),
                         2, 2)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.position_std_enu_m[1, :], name='North', legendgroup='n',
                                      showlegend=False, mode='lines', line={'color': 'blue'}),
                         2, 2)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.position_std_enu_m[2, :], name='Up', legendgroup='u',
                                      showlegend=False, mode='lines', line={'color': 'green'}),
                         2, 2)

        # Plot velocity.
        figure.add_trace(go.Scattergl(x=time, y=pose_data.velocity_body_mps[0, :], name='X', legendgroup='x',
                                      mode='lines', line={'color': 'red'}),
                         1, 3)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.velocity_body_mps[1, :], name='Y', legendgroup='y',
                                      mode='lines', line={'color': 'blue'}),
                         1, 3)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.velocity_body_mps[2, :], name='Z', legendgroup='z',
                                      mode='lines', line={'color': 'green'}),
                         1, 3)

        figure.add_trace(go.Scattergl(x=time, y=pose_data.velocity_body_mps[0, :], name='X', legendgroup='x',
                                      showlegend=False, mode='lines', line={'color': 'red'}),
                         2, 3)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.velocity_body_mps[1, :], name='Y', legendgroup='y',
                                      showlegend=False, mode='lines', line={'color': 'blue'}),
                         2, 3)
        figure.add_trace(go.Scattergl(x=time, y=pose_data.velocity_body_mps[2, :], name='Z', legendgroup='z',
                                      showlegend=False, mode='lines', line={'color': 'green'}),
                         2, 3)

        self._add_figure(name="pose", figure=figure, title="Vehicle Pose")

    def generate_index(self, auto_open=True):
        if len(self.plots) == 0:
            self.logger.warning('No plots generated. Skipping index generation.')
            return

        index_template = '''\
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
  <meta content="text/html; charset=ISO-8859-1" http-equiv="content-type">
  <title>%(title)s</title>
</head>
<body>
  %(links)s
  <br>
  <br>
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

        index_path = os.path.join(self.output_dir, 'index.html')
        with open(index_path, 'w') as f:
            self.logger.info('Creating %s...' % index_path)
            f.write(index_html)

        if auto_open:
            self._open_browser(index_path)

    def _add_figure(self, name, figure, title=None):
        if title is None:
            title = name

        if name in self.plots:
            raise ValueError('Plot "%s" already exists.' % name)
        elif name == 'index':
            raise ValueError('Plot name cannot be index.')

        path = os.path.join(self.output_dir, name + '.html')
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


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--absolute-time', '--abs', action='store_true',
                        help="Interpret the timestamps in --time as absolute P1 times. Otherwise, treat them as "
                             "relative to the first message in the file.")
    parser.add_argument('--no-index', action='store_true',
                        help="Do not automatically open the plots in a web browser.")
    parser.add_argument('-o', '--output', type=str, metavar='DIR', default='.',
                        help="The directory where output will be stored.")
    parser.add_argument('-t', '--time', type=str, metavar='[START][:END]',
                        help="The desired time range to be analyzed. Both start and end may be omitted to read from "
                             "beginning or to the end of the file. By default, timestamps are treated as relative to "
                             "the first message in the file. See --absolute-time.")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Print verbose/trace debugging messages.")

    parser.add_argument('file', type=str, help="The path to a binary file to be read.")
    options = parser.parse_args()

    # Configure logging.
    if options.verbose >= 1:
        logging.basicConfig(format='%(levelname)s - %(name)s:%(lineno)d - %(message)s')
        logger = logging.getLogger('point_one.fusion_engine')
        logger.setLevel(logging.DEBUG)
    else:
        logging.basicConfig(format='%(message)s')

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

    # Read pose data from the file.
    reader = FileReader(options.file)
    analyzer = Analyzer(reader=reader, output_dir=options.output,
                        time_range=time_range, absolute_time=options.absolute_time)
    analyzer.plot_pose()
    analyzer.generate_index(auto_open=not options.no_index)