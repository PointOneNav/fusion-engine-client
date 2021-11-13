import logging
import os

from ..utils.dump_p1bin import dump_p1bin
from ..utils.log import find_log_file, find_p1log_file
from .dump_p1bin import dump_p1bin
from ..analysis.file_reader import FileReader

_logger = logging.getLogger('point_one.utils.mixed_log')

# Note that we prioritize the input.66.bin file over the others. For logs containing a single mixed serial
# data stream as a single message type within the .p1bin file (e.g., Quectel platforms), individual
# FusionEngine messages may be interrupted by .p1bin message headers since the .p1bin entires are just
# arbitrary byte blocks. In that case, we must first strip the .p1bin headers using dump_p1bin.py. ID 66 is
# the value assigned to Quectel/Teseo data within .p1bin files.
CANDIDATE_MIXED_FILES = ['input.66.bin', 'input.p1bin', 'input.rtcm3']


def locate_log(input_path, log_base_dir='/logs', return_output_dir=False, return_log_id=False):
    """!
    @brief Locate a FusionEngine `*.p1log` file, or a binary file containing a mixed stream of FusionEngine messages and
           other content.

    If a mixed binary file is found, extract the FusionEngine content into a `*.p1log` file in the same directory.

    If `input_path` is a file, the returned output directory will be the parent directory of that file. If it is a
    FusionEngine log, the returned output directory will be the log directory.

    @param input_path One of:
           - The path to a `.p1log` file or mixed content binary file
           - A FusionEngine log directory or a directory containing one of the recognized mixed content files (see @ref
             CANDIDATE_MIXED_FILES)
           - A log pattern to be matched (see @ref find_fusion_engine_log()).
    @param log_base_dir The base directory to be searched when performing a pattern match for a log directory.
    @param return_output_dir If `True`, return the output directory associated with the located input file.
    @param return_log_id If `True`, return the ID of the log if the requested path is a FusionEngine log.

    @return A tuple of:
            - The path to the located (or extracted) `*.p1log` file
            - The path to the located output directory. Only provided if `return_output_dir` is `True`.
            - The log ID string, or `None` if the requested file is not part of a FusionEngine log. Only provided if
              `return_log_id` is `True`.
    """
    # Try to find the log normally (look for a directory containing a .p1log file).
    try:
        result = find_p1log_file(input_path, log_base_dir=log_base_dir,
                                 return_output_dir=return_output_dir, return_log_id=return_log_id)
        return result
    except (FileNotFoundError, RuntimeError) as e:
        _logger.error(str(e))

    # If that fails, see if we can find a directory containing a mixed content binary file: *.p1bin or *.rtcm3 (e.g.,
    # Quectel platform logs). If found, try to extract FusionEngine messages from it.
    _logger.info('Could not find a FusionEngine log directory containing a .p1log file. Searching for a P1 log with '
                 'mixed binary data.')
    try:
        result = find_log_file(input_path, candidate_files=CANDIDATE_MIXED_FILES, log_base_dir=log_base_dir,
                               return_output_dir=return_output_dir, return_log_id=return_log_id)
        mixed_file_path = result[0]
    except (FileNotFoundError, RuntimeError) as e:
        _logger.error(str(e))
        return [None for _ in result]

    # If this is a .p1bin file, dump its contents. p1bin files typically contain unaligned blocks of binary data.
    # dump_p1bin() will extract the blocks and concatenate them.
    if mixed_file_path.endswith('.p1bin'):
        _logger.info("Found p1bin file '%s'. Extracting binary stream." % mixed_file_path)
        _, bin_files = dump_p1bin(input_path=mixed_file_path)
        # Data type 66 contains mixed Quectel binary data, including FusionEngine data.
        if 66 in bin_files:
            mixed_file_path = bin_files[66]
        else:
            _logger.warning('No mixed data extracted from .p1bin file.')
            return [None for _ in result]

    # Now, search for FusionEngine messages within the mixed binary data.
    _logger.info("Found mixed log file '%s'. Extracting FusionEngine content." % mixed_file_path)
    log_dir = os.path.dirname(mixed_file_path)
    fe_path = os.path.join(log_dir, "fusion_engine.p1log")
    num_messages = FileReader.extract_fusion_engine_log(input_path=mixed_file_path, output_path=fe_path)
    if num_messages > 0:
        result = list(result)
        result[0] = fe_path
        return result
    else:
        _logger.warning('No FusionEngine data extracted from .p1bin file.')
        return [None for _ in result]
