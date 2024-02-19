#!/usr/bin/env python3
import os
import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

if __package__ is None or __package__ == "":
    from import_utils import enable_relative_imports
    __package__ = enable_relative_imports(__name__, __file__)

from ..messages import *
from ..parsers import MixedLogReader
from ..parsers.host_time_byte_mapper import HostTimeByteMapper
from ..utils import trace as logging
from ..utils.argument_parser import ArgumentParser, ExtendedBooleanAction
from ..utils.log import DEFAULT_LOG_BASE_DIR, locate_log
from ..utils.time_range import TimeRange
from ..utils.trace import BrokenPipeStreamHandler, HighlightFormatter

_logger = logging.getLogger('point_one.fusion_engine.applications.plot_host_timing')


def main():
    parser = ArgumentParser(description="""\
Generate plots of host time intervals for FE messages.
Requires a `*_host_times.bin` file was generated during the collection. For instance,
python/fusion_engine_client/applications/p1_dump_pcap.py generates the host times TCP data was received.
""")

    parser.add_argument(
        '--absolute-time', '--abs', action=ExtendedBooleanAction,
        help="Interpret the timestamps in --time as absolute P1 times. Otherwise, treat them as relative to the first "
             "message in the file. Ignored if --time contains a type specifier.")
    parser.add_argument(
        '-m', '--message-type', type=str, action='append',
        help="An optional list of class names corresponding with the message types to be displayed. May be specified "
             "multiple times (-m Pose -m PoseAux), or as a comma-separated list (-m Pose,PoseAux). All matches are"
             "case-insensitive.\n"
             "\n"
             "If a partial name is specified, the best match will be returned. Use the wildcard '*' to match multiple "
             "message types.\n"
             "\n"
             "Supported types:\n%s" % '\n'.join(['- %s' % c for c in message_type_by_name.keys()]))
    parser.add_argument(
        '-t', '--time', type=str, metavar='[START][:END][:{rel,abs}]',
        help="The desired time range to be analyzed. Both start and end may be omitted to read from beginning or to "
             "the end of the file. By default, timestamps are treated as relative to the first message in the file, "
             "unless an 'abs' type is specified or --absolute-time is set.")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Print verbose/trace debugging messages.")

    log_parser = parser.add_argument_group('Log Control')
    log_parser.add_argument(
        '--ignore-index', action='store_true',
        help="If set, do not load the .p1i index file corresponding with the .p1log data file. If specified and a .p1i "
             "file does not exist, do not generate one. Otherwise, a .p1i file will be created automatically to "
             "improve data read speed in the future.")
    log_parser.add_argument(
        '--log-base-dir', metavar='DIR', default=DEFAULT_LOG_BASE_DIR,
        help="The base directory containing FusionEngine logs to be searched if a log pattern is specified.")
    log_parser.add_argument(
        '--original', action='store_true',
        help="When loading from a log, load the recorded FusionEngine output file instead of playback results.")
    log_parser.add_argument(
        '--progress', action='store_true',
        help="Print file read progress to the console periodically.")
    log_parser.add_argument(
        'log',
        help="The log to be read. May be one of:\n"
             "- The path to a .p1log file or a file containing FusionEngine messages and other content\n"
             "- The path to a FusionEngine log directory\n"
             "- A pattern matching a FusionEngine log directory under the specified base directory "
             "(see find_fusion_engine_log() and --log-base-dir)")

    options = parser.parse_args()

    read_index = not options.ignore_index

    # Configure logging.
    if options.verbose >= 1:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s:%(lineno)d - %(message)s',
                            stream=sys.stdout)
        if options.verbose == 1:
            logging.getLogger('point_one.fusion_engine.parsers').setLevel(logging.DEBUG)
        else:
            logging.getLogger('point_one.fusion_engine.parsers').setLevel(
                logging.getTraceLevel(depth=options.verbose - 1))
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s', stream=sys.stdout)

    HighlightFormatter.install(color=True, standoff_level=logging.WARNING)
    BrokenPipeStreamHandler.install()

    # Locate the input file and set the output directory.
    input_path, log_id = locate_log(input_path=options.log, log_base_dir=options.log_base_dir, return_log_id=True,
                                    load_original=options.original,
                                    extract_fusion_engine_data=False)
    if input_path is None:
        # locate_log() will log an error.
        sys.exit(1)

    _logger.info("Processing input file '%s'." % input_path)

    # Parse the time range.
    time_range = TimeRange.parse(options.time, absolute=options.absolute_time)

    # If the user specified a set of message names, lookup their type values. Below, we will limit the printout to only
    # those message types.
    message_types = set()
    if options.message_type is not None:
        # Pattern match to any of:
        #   -m Type1
        #   -m Type1 -m Type2
        #   -m Type1,Type2
        #   -m Type1,Type2 -m Type3
        #   -m Type*
        try:
            message_types = MessagePayload.find_matching_message_types(options.message_type)
            if len(message_types) == 0:
                # find_matching_message_types() will print an error.
                sys.exit(1)
        except ValueError as e:
            _logger.error(str(e))
            sys.exit(1)
    else:
        _logger.error('Must specify at least one message type')
        sys.exit(1)

    host_mapper = HostTimeByteMapper(input_path)
    if not host_mapper.does_host_time_file_exist():
        _logger.error(f'Host time file "{host_mapper.index_path}" not found.')
        sys.exit(1)
    host_mapper.load_from_file()
    # Host times map 1-to-1 with reader.index entries.
    host_times = host_mapper.map_to_msg_offsets(reader.index.offset)

    output_dir = Path(input_path).parent
    prefix = os.path.splitext(os.path.basename(input_path))[0]

    # Process all data in the file.
    reader = MixedLogReader(input_path, return_offset=True, show_progress=options.progress,
                            ignore_index=not read_index, message_types=message_types, time_range=time_range)

    for type in message_types:
        # Filter host times to indexes that match message type.
        msg_index = reader.index[type].message_index
        type_host_times = host_times[msg_index]

        times = (type_host_times - type_host_times[0])[1:]
        host_diff = np.diff(type_host_times)[1:]

        figure = make_subplots(rows=2, cols=1, print_grid=False, shared_xaxes=False,
                               subplot_titles=[f'{type} Host Time Intervals',
                                               f'{type} Host Time Interval Histogram'])

        figure['layout']['xaxis1'].update(title=f"Relative Host Time (sec)", showticklabels=True)
        figure['layout']['xaxis2'].update(title=f"Host Time Interval (sec)", showticklabels=True)
        figure['layout']['yaxis1'].update(title="Host Time Interval (sec)")
        figure['layout']['yaxis2'].update(title="Percent")

        figure.add_trace(go.Scatter(x=times, y=host_diff, name='Host Time Intervals',
                                    mode='markers', marker={'color': 'blue'}),
                         1, 1)
        figure.add_trace(go.Histogram(x=host_diff, histnorm='percent', name='Host Time Interval Histogram'),
                         2, 1)

        file_path = os.path.join(output_dir, f'{prefix}_{type}_timing.html')
        _logger.info(f'Writing {file_path}')
        figure.write_html(file_path)


if __name__ == "__main__":
    main()
