from typing import Optional, Union

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
             "- Print the binary representation of each message on a single line, but no other details\n"
             "- pretty - Print the message contents in a human-readable format (default)\n"
             "- pretty-binary - Use `pretty` format, but include the binary representation of each message\n"
             "- pretty-binary-payload - Like `pretty-binary`, but exclude the message header from the binary\n"
             "- oneline - Print a summary of each message on a single line\n"
             "- oneline-detailed - Print a one-line summary, including message offset details\n"
             "- oneline-binary - Use `oneline-detailed` format, but include the binary representation of each message\n"
             "- oneline-binary-payload - Like `oneline-binary`, but exclude the message header from the binary")


def print_message(header: MessageHeader, contents: Union[MessagePayload, bytes],
                  offset_bytes: Optional[int] = None, format: str = 'pretty', bytes: Optional[int] = None,
                  logger: Optional[logging.Logger] = None):
    if logger is None:
        logger = _logger

    if format == 'binary':
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

    if format != 'oneline':
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

    if bytes is None:
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

    logger.info('\n'.join(parts))


class MessageStatsEntry:
    def __init__(self):
        self.count = 0
        self.total_bytes = 0

    def update(self, header: MessageHeader, message: MessagePayload):
        self.count += 1
        self.total_bytes = header.get_message_size()


class DeviceSummary:
    def __init__(self):
        self.device_id = None
        self.version_info = None
        self.stats = defaultdict(MessageStatsEntry)

    def update(self, header: MessageHeader, message: MessagePayload):
        self.stats[header.message_type].update(header, message)

        if header.message_type == MessageType.DEVICE_ID:
            self.device_id = message
        elif header.message_type == MessageType.VERSION_INFO:
            self.version_info = message


def print_summary_table(device_summary: DeviceSummary, logger: Optional[logging.Logger] = None):
    if logger is None:
        logger = _logger

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

    format_string = '| {:<50} | {:>5} | {:>8} |'
    logger.info(format_string.format('Message Name', 'Type', 'Count'))
    logger.info(format_string.format('-' * 50, '-' * 5, '-' * 8))
    total_messages = 0
    for type, entry in sorted(device_summary.stats.items(), key=lambda x: int(x[0])):
        if type in message_type_to_class:
            name = message_type_to_class[type].__name__
        elif type.is_unrecognized():
            name = str(type)
        else:
            name = f'Unsupported ({str(type)})'
        logger.info(format_string.format(name, int(type), entry.count))
        total_messages += entry.count
    logger.info(format_string.format('-' * 50, '-' * 5, '-' * 8))
    logger.info(format_string.format('Total', '', total_messages))
