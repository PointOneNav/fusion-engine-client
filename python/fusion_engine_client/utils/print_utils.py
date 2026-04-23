from typing import Optional, Set, Union

import argparse
from collections import defaultdict

from ..messages import *
from ..utils import trace as logging
from ..utils.bin_utils import bytes_to_hex

_logger = logging.getLogger('point_one.fusion_engine.utils.print_utils')


def add_print_format_argument(parser: argparse._ActionsContainer, *arg_names):
    parser.add_argument(
        *arg_names,
        choices=['binary', 'pretty', 'pretty-binary', 'pretty-binary-payload',
                 'oneline', 'oneline-detailed', 'oneline-binary', 'oneline-binary-payload'],
        default='pretty',
        help="Specify the format used to print the message contents:\n"
             "- binary - Print the binary representation of each message on a single line, but no other details\n"
             "- pretty - Print the message contents in a human-readable format (default)\n"
             "- pretty-binary - Use `pretty` format, but include the binary representation of each message\n"
             "- pretty-binary-payload - Like `pretty-binary`, but exclude the message header from the binary\n"
             "- oneline - Print a summary of each message on a single line\n"
             "- oneline-detailed - Print a one-line summary, including message offset details\n"
             "- oneline-binary - Use `oneline-detailed` format, but include the binary representation of each message\n"
             "- oneline-binary-payload - Like `oneline-binary`, but exclude the message header from the binary")

def add_wrapped_data_mode_argument(parser: argparse._ActionsContainer, *arg_names):
    parser.add_argument(
        *arg_names,
        choices=['auto', 'all', 'parent', 'content'],
        default='parent',
        help="Specify the way in which InputDataWrapper messages should be handled:\n"
             "- auto - Use 'all' mode unless specific message types are specified, in which case use 'content' mode "
             "and only print the wrapped contents.\n"
             "- all - Print both the @ref InputDataWrapperMessage and its contents if it contains a FusionEngine "
             "message\n"
             "- parent - Print the @ref InputDataWrapperMessage message but not its contents\n"
             "- content - Print the wrapped contents, if the wrapper contains a FusionEngine message, but do not print "
             "the InputDataWrapper message itself")


def print_message(header: MessageHeader, contents: Union[MessagePayload, bytes],
                  offset_bytes: Optional[int] = None, format: str = 'pretty', bytes: Optional[bytes] = None,
                  logger: Optional[logging.Logger] = None,
                  message_types: Optional[Set[MessageType]] = None, wrapped_data_mode: str = 'all'):
    """!
    @brief Print the specified FusionEngine message to the console or provided `Logger` instance.

    @param header The header of the message to be printed.
    @param contents The payload of the message to be printed, or a `bytes` object if the message was not recognized.
    @param offset_bytes The offset of this message (in bytes) within the input data stream.
    @param format The format used to print the message contents:
           - `binary` - Print the binary representation of each message on a single line, but no other details
           - `pretty` - Print the message contents in a human-readable format (default)
           - `pretty-binary` - Use `pretty` format, but include the binary representation of each message
           - `pretty-binary-payload` - Like `pretty-binary`, but exclude the message header from the binary
           - `oneline` - Print a summary of each message on a single line
           - `oneline-detailed` - Print a one-line summary, including message offset details
           - `oneline-binary` - Use `oneline-detailed` format, but include the binary representation of each message
           - `oneline-binary-payload` - Like `oneline-binary`, but exclude the message header from the binary
    @param bytes The binary representation of the message.
    @param logger A `logging.Logger` instance with which the output will be printed.
    @param message_types An optional set of FusionEngine @ref MessageType%s to be displayed. All other message types
           will be ignored.
    @param wrapped_data_mode The way in which @ref InputDataWrapperMessage%s should be handled:
           - all - Print both the @ref InputDataWrapperMessage and its contents if it contains a FusionEngine message
           - parent - Print the @ref InputDataWrapperMessage message but not its contents
           - content - Print the wrapped contents, if the wrapper contains a FusionEngine message, but do not print the
                       @ref InputDataWrapperMessage itself
    """
    if logger is None:
        logger = _logger

    is_requested = message_types is None or header.message_type in message_types
    if header.message_type == MessageType.INPUT_DATA_WRAPPER:
        wrapped_fe_header = contents.get_fe_content_header()
        if is_requested:
            hide_message = False
        elif wrapped_data_mode == 'content':
            hide_message = True
        # Note: is_requested==False above implies message_types is not None, no need to check again.
        elif wrapped_fe_header is None:
            hide_message = True
        else:
            hide_message = wrapped_fe_header.message_type not in message_types
    else:
        hide_message = not is_requested

    if hide_message:
        pass
    elif format == 'binary':
        if bytes is None:
            raise ValueError('No data provided for binary format.')
        parts = []
    elif isinstance(contents, MessagePayload):
        if format.startswith('oneline'):
            # The repr string should always start with the message type, then other contents:
            #   [POSE (10000), p1_time=12.029 sec, gps_time=2249:528920.500 (1360724120.500 sec), ...]
            # We want to reformat and insert the additional details as follows for consistency:
            #   POSE (10000) [sequence=10, ... p1_time=12.029 sec, gps_time=2249:528920.500 (1360724120.500 sec), ...]
            message_str = repr(contents).split('\n')[0]
            message_str = message_str.replace('[', '', 1)
            break_idx = message_str.find(',')
            if break_idx >= 0:
                message_str = f'{message_str[:break_idx]} [{message_str[(break_idx + 2):]}'
            else:
                message_str = message_str.rstrip(']')
            parts = [message_str]
        else:
            parts = str(contents).split('\n')
    else:
        parts = [f'{header.get_type_string()} (unsupported)']

    if hide_message:
        pass
    elif format != 'oneline':
        details = 'source_id=%d, sequence=%d, size=%d B' % (header.source_identifier,
                                                            header.sequence_number,
                                                            header.get_message_size())
        if offset_bytes is not None:
            details += ', offset=%d B (0x%x)' % (offset_bytes, offset_bytes)

        idx = parts[0].find('[')
        if idx < 0:
            parts[0] += f' [{details}]'
        else:
            parts[0] = f'{parts[0][:(idx + 1)]}{details}, {parts[0][(idx + 1):]}'

    if hide_message:
        pass
    elif bytes is None:
        pass
    elif format == 'binary':
        byte_string = bytes_to_hex(bytes, bytes_per_row=-1, bytes_per_col=2).replace('\n', '\n  ')
        parts.insert(1, byte_string)
    elif format == 'pretty-binary' or format == 'pretty-binary-payload':
        if format.endswith('-payload'):
            bytes = bytes[MessageHeader.calcsize():]
        byte_string = '    ' + bytes_to_hex(bytes, bytes_per_row=16, bytes_per_col=2).replace('\n', '\n    ')
        parts.insert(1, "  Binary:\n%s" % byte_string)
    elif format == 'oneline-binary' or format == 'oneline-binary-payload':
        if format.endswith('-payload'):
            bytes = bytes[MessageHeader.calcsize():]
        byte_string = '  ' + bytes_to_hex(bytes, bytes_per_row=16, bytes_per_col=2).replace('\n', '\n  ')
        parts.insert(1, byte_string)

    if not hide_message:
        if wrapped_data_mode == 'recursive':
            parts[0] += ' [wrapped]'

        logger.info('\n'.join(parts))

    # If this is an InputDataWrapper message, recursively display its contents.
    if header.message_type == MessageType.INPUT_DATA_WRAPPER and wrapped_data_mode != 'parent':
        wrapped_fe_payload = contents.get_fe_content_payload()
        if wrapped_fe_payload is not None:
            print_message(wrapped_fe_header, wrapped_fe_payload, 0, format=format, bytes=contents.data,
                          message_types=message_types, wrapped_data_mode='recursive')


class MessageStatsEntry:
    def __init__(self):
        self.count = 0
        self.total_bytes = 0

    def update(self, header: MessageHeader, message: MessagePayload):
        self.count += 1
        self.total_bytes += header.get_message_size()


class DeviceSummary:
    def __init__(self):
        self.device_id = None
        self.version_info = None
        self.stats = defaultdict(MessageStatsEntry)
        self.wrapped_non_fe_input_data_stats = defaultdict(MessageStatsEntry)
        self.wrapped_fe_input_data_stats = defaultdict(MessageStatsEntry)

    def update(self, header: MessageHeader, message: MessagePayload, message_types: Optional[Set[MessageType]] = None):
        # If the user specified specific message types, ignore non-FusionEngine messages or FusionEngine messages
        # that are not in the list.
        wrapped_fe_header = None
        include_wrapped_content = False
        if header.message_type == MessageType.INPUT_DATA_WRAPPER:
            wrapped_fe_header = message.get_fe_content_header()
            if message_types is None:
                include_wrapped_content = True
            elif wrapped_fe_header is None:
                include_wrapped_content = False
            else:
                include_wrapped_content = wrapped_fe_header.message_type in message_types

        # Record stats for this message type. Skip InputDataWrappers messages whose content is not listed in
        # message_types.
        if header.message_type != MessageType.INPUT_DATA_WRAPPER or include_wrapped_content:
            self.stats[header.message_type].update(header, message)

        # Extract additional data from the message.
        if header.message_type == MessageType.DEVICE_ID:
            self.device_id = message
        elif header.message_type == MessageType.VERSION_INFO:
            self.version_info = message
        elif header.message_type == MessageType.INPUT_DATA_WRAPPER:
            wrapped_fe_header = message.get_fe_content_header()
            if include_wrapped_content:
                # Count all wrapped content, not including FusionEngine messages.
                if wrapped_fe_header is None:
                    self.wrapped_non_fe_input_data_stats[message.data_type].count += 1
                    self.wrapped_non_fe_input_data_stats[message.data_type].total_bytes += len(message.data)
                # Count FusionEngine messages separately.
                else:
                    self.wrapped_fe_input_data_stats[wrapped_fe_header.message_type].count += 1
                    self.wrapped_fe_input_data_stats[wrapped_fe_header.message_type].total_bytes += len(message.data)


def print_summary_table(device_summary: DeviceSummary, logger: Optional[logging.Logger] = None):
    if logger is None:
        logger = _logger

    # Print high-level device/software info.
    device_type = DeviceType.UNKNOWN
    device_id = '<Unknown>'
    if device_summary.device_id is not None:
        device_type = device_summary.device_id.device_type
        if len(device_summary.device_id.user_id_data) != 0:
            device_id = DeviceIDMessage._get_str(device_summary.device_id.user_id_data)
    logger.info(f'Device ID: {device_id}  |  '
                f'Device type: {"<Unknown>" if device_type == DeviceType.UNKNOWN else str(device_type)}')

    if device_summary.version_info is not None and device_summary.version_info.engine_version_str != "":
        logger.info(f'Software version: {device_summary.version_info.engine_version_str}')
    else:
        logger.info(f'Software version: <Unknown>')

    # Print a table with stats for all FusionEngine messages in the data.
    def _print_table_header(cols: List[Dict]):
        col_width = [max(len(c['name']), c.get('min_width', 0)) for c in cols]
        formats = ['{:%s%d}' % (c.get('align', '>'), col_width[i]) for i, c in enumerate(cols)]
        format_string = '| ' + ' | '.join(formats) + ' |'

        logger.info('')
        logger.info(format_string.format(*[c['name'] for c in cols]))
        dividers = ['-' * col_width[i] for i, _ in enumerate(cols)]
        logger.info(format_string.format(*dividers))

        return format_string, dividers

    cols = [
        {'name': 'Message Name', 'align': '<', 'min_width': 50},
        {'name': 'Type', 'min_width': 5},
        {'name': 'Count', 'min_width': 8},
        {'name': 'Total Size (B)'}
    ]
    format_string, dividers = _print_table_header(cols)
    total_messages = 0
    total_bytes = 0
    for type, entry in sorted(device_summary.stats.items(), key=lambda x: int(x[0])):
        if type in message_type_to_class:
            name = message_type_to_class[type].__name__
        elif type.is_unrecognized():
            name = str(type)
        else:
            name = f'Unsupported ({str(type)})'
        logger.info(format_string.format(name, int(type), entry.count, entry.total_bytes))
        total_messages += entry.count
        total_bytes += entry.total_bytes
    logger.info(format_string.format(*dividers))
    logger.info(format_string.format('Total', '', total_messages, total_bytes))

    # Print a second table displaying types/stats for messages extracted from InputDataWrapper messages.
    wrapped_input_data_types = (set(device_summary.wrapped_non_fe_input_data_stats.keys()) |
                                set(device_summary.wrapped_fe_input_data_stats.keys()))
    if len(wrapped_input_data_types) > 0:
        cols = [
            {'name': 'Input Data Type', 'align': '<', 'min_width': 50},
            {'name': 'Count', 'min_width': 8},
            {'name': 'Total Size (B)'}
        ]
        format_string, dividers = _print_table_header(cols)
        total_messages = 0
        total_bytes = 0
        have_wrapped_fe = False
        for data_type in sorted(wrapped_input_data_types):
            if data_type in device_summary.wrapped_non_fe_input_data_stats:
                entry = device_summary.wrapped_non_fe_input_data_stats[data_type]
                logger.info(format_string.format(data_type.to_string(), entry.count, entry.total_bytes))
                total_messages += entry.count
                total_bytes += entry.total_bytes

            if data_type in device_summary.wrapped_fe_input_data_stats:
                entry = device_summary.wrapped_fe_input_data_stats[data_type]
                logger.info(format_string.format(f'{data_type.to_string()} **', entry.count, entry.total_bytes))
                have_wrapped_fe = True
        logger.info(format_string.format(*dividers))
        logger.info(format_string.format('Total', total_messages, total_bytes))
        if have_wrapped_fe:
            logger.info('** FusionEngine content extracted from InputDataWrapperMessages.')
