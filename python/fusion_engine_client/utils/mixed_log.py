import logging
import os

from ..utils.dump_p1bin import dump_p1bin
from ..utils.log import find_log_file, find_p1log_file
from .dump_p1bin import dump_p1bin
from ..analysis.file_reader import FileReader

_logger = logging.getLogger('point_one.utils.mixed_log')


def find_mixed_log_file(options, find_p1log=True):
    try:
        if find_p1log:
            input_path, output_dir, log_id = find_p1log_file(options.log,
                                                             return_output_dir=True, return_log_id=True,
                                                             log_base_dir=options.log_base_dir,
                                                             load_original=options.original)
        else:
            candidate_files = ['input.66.bin', 'input.p1bin', 'input.rtcm3']
            input_path, output_dir, log_id = find_log_file(options.log,
                                                           candidate_files=candidate_files,
                                                           return_output_dir=True, return_log_id=True,
                                                           log_base_dir=options.log_base_dir)

        if log_id is None:
            _logger.info('Loading %s.' % os.path.basename(input_path))
        else:
            _logger.info('Loading %s from log %s.' % (os.path.basename(input_path), log_id))

        if input_path.endswith('.playback.p1log') or input_path.endswith('.playback.p1bin'):
            _logger.warning('Using .p1log file from log playback. If you want the originally recorded data, set '
                            '--original.')

        if not hasattr(options, 'output') or options.output is None:
            if log_id is not None:
                output_dir = os.path.join(output_dir, 'plot_fusion_engine')
        else:
            output_dir = options.output

        return input_path, output_dir
    except (FileNotFoundError, RuntimeError) as e:
        _logger.error(str(e))
        return None, None


def locate_log(options):
    # Try to find the log normally (look for a directory containing a .p1log file).
    input_path, output_dir = find_mixed_log_file(options, find_p1log=True)
    if input_path is not None:
        return input_path, output_dir

    # If that fails, see if we can find a directory containing a mixed content binary file: *.p1bin or *.rtcm3 (e.g.,
    # Quectel platform logs). If found, try to extract FusionEngine messages from it.
    _logger.info('Could not find a FusionEngine log directory containing a .p1log file. Searching for a P1 log with '
                 'mixed binary data.')
    input_path, output_dir = find_mixed_log_file(options, find_p1log=False)
    if input_path is not None:
        # If this is a .p1bin file, dump its contents. p1bin files typically contain unaligned blocks of binary data.
        # dump_p1bin() will extract the blocks and concatenate them.
        if input_path.endswith('.p1bin'):
            _, bin_files = dump_p1bin(input_path=input_path)
            # Data type 66 contains mixed Quectel binary data, including FusionEngine data.
            if 66 in bin_files:
                input_path = bin_files[66]
            else:
                _logger.warning('No mixed data extracted from .p1bin file.')
                return None, None

        # Now, search for FusionEngine messages within the mixed binary data.
        log_dir = os.path.dirname(input_path)
        fe_path = os.path.join(log_dir, "fusion_engine.p1log")
        num_messages = FileReader.extract_fusion_engine_log(input_path=input_path, output_path=fe_path)
        if num_messages > 0:
            return fe_path, output_dir
        else:
            _logger.warning('No FusionEngine data extracted from .p1bin file.')
            return None, None
    else:
        # _find_log_file() will log a message.
        return None, None
