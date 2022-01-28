import fnmatch
import os

import logging

from ..messages import MessageHeader, MessageType

_logger = logging.getLogger('point_one.utils.log')

# Note: The spelling here is intentional.
MANIFEST_FILE_NAME = 'maniphest.json'

CANDIDATE_MIXED_FILES = ['input.raw', 'input.bin', 'input.rtcm3']


def find_log_by_pattern(pattern, log_base_dir='/logs', allow_multiple=False,
                        log_test_filenames=(MANIFEST_FILE_NAME,), return_test_file=False):
    """!
    @brief Perform a pattern match to locate a log directory containing the specified files.

    FusionEngine data logs are typically a directory, named with a unique hash, containing a JSON log manifest file and
    binary input/output data files. This function can locate a requested log directory under a base directory based on
    a user-specified pattern as follows:
    - Path to the directory matches the full search pattern
    - AND the deepest subdirectory name matches the last element in the search pattern
    - AND the subdirectory contain a specified test file (or at least one of a list of candidate files; defaults to a
      FusionEngine log manifest file)

    For example:
    | Path                                | `1234`   | `foo*/1234` | `foo_*/1234` |
    | `path/to/foo_bar/12345678`          | match    | match       | match        |
    | `path/to/foo_/1234abcd`             | match    | match       | match        |
    | `path/to/foo_bar/12345678/more/info`| no match | no match    | no match     |
    | `path/to/foo/12345678`              | match    | match       | no match     |
    | `path/to/foo_/abcd1234`             | no match | no match    | no match     |

    Most commonly, users specify the first N characters of a log's hash (e.g., `1234` to locate `/path/to/12345678`.

    @param pattern The pattern to be matched.
    @param log_base_dir The base directory to be searched.
    @param allow_multiple If `True`, return multiple matching logs if present, and return an empty list if no logs match
           the pattern. Otherwise, raise an exception if either multiple or zero logs are found.
    @param log_test_filenames A list of input files to locate within the log directory. If _one_ of the listed files is
           found, the directory is considered a valid log. If `None` or an empty list, skip the test file requirement.
    @param return_test_file If `True`, return the path to the located test file.

    @return A list containing entries for each matching log. Each entry is a tuple containing the path and the log ID.
            If `return_test_file == True`, each tuple will also contain the located test file (or `None` if the test
            file requirement is disabled). If `allow_multiple == False`, the list will always contain exactly one entry.
    """
    if log_test_filenames is None:
        log_test_filenames = []
    elif not isinstance(log_test_filenames, (list, tuple, set)):
        log_test_filenames = [log_test_filenames]
    else:
        log_test_filenames = [f for f in log_test_filenames if f is not None]

    # Match logs in any directory starting with the specified pattern.
    match_pattern = '*/' + pattern + '*'
    last_element = match_pattern.split('/')[-1]

    matches = []
    for root, dirnames, _ in os.walk(log_base_dir):
        for dirname in dirnames:
            path = os.path.join(root, dirname)
            # Match directories that meet the criteria defined above.
            #
            # For example, pattern `foo_*/1234*` match as follows:
            # - `path/to/foo_bar/12345678`           <-- match
            # - `path/to/foo_/1234abcd`              <-- match
            # - `path/to/foo_bar/12345678/more/info` <-- NO MATCH
            # - `path/to/foo/12345678`               <-- NO MATCH
            # - `path/to/foo_/abcd1234`              <-- NO MATCH
            if fnmatch.fnmatch(path, match_pattern) and fnmatch.fnmatch(dirname, last_element):
                test_file = None
                for f in log_test_filenames:
                    test_file_path = os.path.join(path, f)
                    if os.path.exists(test_file_path):
                        test_file = test_file_path
                        break

                if len(log_test_filenames) == 0 or test_file is not None:
                    if return_test_file:
                        matches.append((path, dirname, test_file))
                    else:
                        matches.append((path, dirname))

    if len(matches) > 1 and not allow_multiple:
        # If there are multiple matches, see if any match exactly.
        exact_matches = []
        for m in matches:
            if os.path.basename(m[0]) == pattern:
                exact_matches.append(m)

        if len(exact_matches) == 1:
            matches = exact_matches
        else:
            e = RuntimeError("Found multiple logs that match pattern '%s'. Please be more specific." % pattern)
            _logger.error(str(e))
            _logger.error('Matches:\n  %s' % ('\n  '.join([m[0] for m in matches])))
            raise e
    elif len(matches) == 0:
        message = "Found no logs that match pattern '%s'." % pattern
        if not allow_multiple:
            raise FileNotFoundError(message)
        else:
            _logger.warning(message)

    return matches


def find_log_file(input_path, candidate_files=None, return_output_dir=False, return_log_id=False, log_base_dir='/logs'):
    """!
    @brief Locate a log directory containing the specified file(s).

    `input_path` may be a file, a directory, or a pattern to be matched to a parent directory within `log_base_dir`.

    If `input_path` is a directory or pattern, this function will attempt to locate a log directory containing a data
    file from a list of candidate filenames (`candidate_files`).

    If `input_path` is a file, `candidate_files` will be ignored and the returned output directory will be the parent
    directory of that file.

    ```
    /logs/2021-10-01/
      abcdef/
        fusion_engine.p1log
        maniphest.json

    > find_log_file(input_path='abc', candidate_files=['fusion_engine.p1log'])
    /logs/2021-10-01/abcdef/fusion_engine.p1log
    ```

    @note
    For normal use, it is recommended that you call @ref locate_log() or @ref find_p1log_file() instead.

    @param input_path The path to a data file, a FusionEngine log directory, or a pattern to be matched (see @ref
           find_fusion_engine_log()).
    @param candidate_files A list of one or more data files to be located within the log directory, in order of
           priority. If `None`, defaults to `fusion_engine.p1log`.
    @param return_output_dir If `True`, return the output directory associated with the located input file.
    @param return_log_id If `True`, return the ID of the log if the requested path is a FusionEngine log.
    @param log_base_dir The base directory to be searched when performing a pattern match for a log directory.

    @return A tuple containing:
            - The path to the located file.
            - The path to the located output directory. Only provided if `return_output_dir` is `True`.
            - The log ID string, or `None` if the requested file is not part of a FusionEngine log. Only provided if
              `return_log_id` is `True`.
    """
    # Check if the input path is a file. If so, return it and set the output directory to its parent directory.
    if os.path.isfile(input_path):
        output_dir = os.path.dirname(input_path)
        if output_dir == "":
            output_dir = "."
        log_id = None
    # If the input path is a directory, see if it's a P1 log. If it is not a directory, see if it pattern matches to a
    # log directory within `log_base_dir`. If so for either case, set the output directory to the log directory (note
    # that the .p1log may be contained within a subdirectory).
    else:
        if candidate_files is None:
            # No candidate files specified. Default to 'fusion_engine.p1log'.
            candidate_files = ['fusion_engine.p1log']
        elif not isinstance(candidate_files, (tuple, list)):
            # User specified a string, not a list. Convert to a list.
            candidate_files = [candidate_files]

        # First, see if the user's path is an existing log directory containing a data file. If so, use that.
        log_dir = None
        log_id = None
        dir_exists = os.path.isdir(input_path)
        if dir_exists:
            for f in candidate_files:
                if f is None:
                    continue

                test_path = os.path.join(input_path, f)
                if os.path.exists(test_path):
                    log_dir = input_path
                    log_id = os.path.basename(log_dir)
                    input_path = test_path
                    break

        # If the user didn't specify a directory, or the directory wasn't considered a valid log (i.e., didn't have any
        # of the candidate files in it), check if they provided a pattern match to a log (i.e., a partial log ID or a
        # search pattern (foo*/partial_id*)).
        if log_dir is None:
            if dir_exists:
                _logger.info("Directory '%s' does not contain a data file. Attempting a pattern match." % input_path)
            else:
                _logger.info("File '%s' not found. Searching for a matching log." % input_path)

            try:
                matches = find_log_by_pattern(input_path, log_base_dir=log_base_dir,
                                              log_test_filenames=candidate_files, return_test_file=True)
                log_dir = matches[0][0]
                log_id = matches[0][1]
                input_path = matches[0][2]
            except RuntimeError as e:
                # Multiple matching directories found.
                raise e
            except FileNotFoundError as e:
                if dir_exists:
                    # User path is an existing directory but no candidate files found in it _and_ it wasn't a pattern
                    # match to a different directory with files.
                    raise FileNotFoundError("Directory '%s' is not a valid FusionEngine log." % input_path)
                else:
                    # No log directories found matching user pattern.
                    raise e

        output_dir = log_dir

    result = [input_path]
    if return_output_dir:
        result.append(output_dir)
    if return_log_id:
        result.append(log_id)

    return result


def find_p1log_file(input_path, return_output_dir=False, return_log_id=False, log_base_dir='/logs'):
    """!
    @brief Locate a FusionEngine log directory containing a `*.p1log` file from a list of expected candidate paths.

    If `input_path` is a file, the returned output directory will be the parent directory of that file. If it is a
    FusionEngine log, the returned output directory will be the log directory.

    @note
    `*.p1log` files must contain _only_ FusionEngine messages. See also @ref locate_log(), which supports both `*.p1log`
    files and mixed binary files.

    @param input_path The path to a `.p1log` file, a FusionEngine log directory, or a pattern to be matched (see @ref
           find_fusion_engine_log()).
    @param return_output_dir If `True`, return the output directory associated with the located input file.
    @param return_log_id If `True`, return the ID of the log if the requested path is a FusionEngine log.
    @param log_base_dir The base directory to be searched when performing a pattern match for a log directory.

    @return A tuple containing:
            - The path to the located file.
            - The path to the located output directory. Only provided if `return_output_dir` is `True`.
            - The log ID string, or `None` if the requested file is not part of a FusionEngine log. Only provided if
              `return_log_id` is `True`.
    """
    candidate_files = ['fusion_engine.p1log',
                       # Legacy path, maintained for backwards compatibility.
                       'filter/output/fe_service/output.p1bin']
    result = find_log_file(input_path, candidate_files=candidate_files, return_output_dir=return_output_dir,
                           return_log_id=return_log_id, log_base_dir=log_base_dir)
    p1log_path = result[0]
    if p1log_path.endswith('.p1log') or p1log_path.endswith('filter/output/fe_service/output.p1bin'):
        return result
    else:
        # If we got here and find_log_file() didn't raise an exception, the user specified a file (not a directory) and
        # it does not end in .p1log. We'll assume it is not a .p1log file -- it may contained mixed contents, including
        # FusionEngine messages, but it is not a .p1log file with _exclusively_ FusionEngine messages.
        raise FileExistsError('Specified file is not a .p1log file.')


def extract_fusion_engine_log(input_path, output_path=None, warn_on_gaps=True, return_counts=False):
    """!
    @brief Extract FusionEngine data from a file containing mixed binary data.

    @param input_path The path to the binary file to be read.
    @param output_path The path to an output file to be generated. If `None`, set to `<prefix>.p1log`, where
           `input_path` is `<prefix>.<ext>`.
    @param warn_on_gaps If `True`, print a warning if gaps are detected in the data sequence numbers.
    @param return_counts If `True`, return the number of messages extracted for each message type.

    @return A tuple containing:
            - The number of decoded messages.
            - A `dict` containing the number of messages extracted for each message type. Only provided if
              `return_counts` is `True`.
    """
    def _advance_to_next_sync(in_fd):
        try:
            while True:
                byte0 = in_fd.read(1)[0]
                while True:
                    if byte0 == MessageHeader._SYNC0:
                        byte1 = in_fd.read(1)[0]
                        if byte1 == MessageHeader._SYNC1:
                            in_fd.seek(-2, os.SEEK_CUR)
                            return True
                        byte0 = byte1
                    else:
                        break
        except IndexError:
            return False

    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + '.p1log'

    if input_path == output_path:
        raise ValueError("Input and output paths match. Cannot overwrite existing file '%s'." % input_path)

    header = MessageHeader()
    valid_count = 0
    message_counts = {}
    with open(input_path, 'rb') as in_fd:
        with open(output_path, 'wb') as out_path:
            prev_sequence_number = None
            while True:
                if not _advance_to_next_sync(in_fd):
                    break

                offset = in_fd.tell()
                _logger.trace('Reading candidate message @ %d (0x%x).' % (offset, offset))

                data = in_fd.read(MessageHeader.calcsize())
                read_len = len(data)
                try:
                    header.unpack(data, warn_on_unrecognized=False)
                    if header.payload_size_bytes > MessageHeader._MAX_EXPECTED_SIZE_BYTES:
                        raise ValueError('Payload size (%d) too large.' % header.payload_size_bytes)

                    payload = in_fd.read(header.payload_size_bytes)
                    read_len += len(payload)
                    if len(payload) != header.payload_size_bytes:
                        raise ValueError('Not enough data - likely not a valid FusionEngine header.')

                    data += payload
                    header.validate_crc(data)

                    if prev_sequence_number is not None and \
                       (header.sequence_number - prev_sequence_number) != 1 and \
                       not (header.sequence_number == 0 and prev_sequence_number == 0xFFFFFFFF):
                        func = _logger.warning if warn_on_gaps else _logger.debug
                        func('Data gap detected @ %d (0x%x). [sequence=%d, prev_sequence=%d, # messages=%d]' %
                             (offset, offset, header.sequence_number, prev_sequence_number, valid_count + 1))
                    prev_sequence_number = header.sequence_number

                    _logger.debug('Read %s message @ %d (0x%x). [length=%d B, sequence=%d, # messages=%d]' %
                                  (header.get_type_string(), offset, offset,
                                   MessageHeader.calcsize() + header.payload_size_bytes, header.sequence_number,
                                   valid_count + 1))

                    out_path.write(data)
                    valid_count += 1
                    message_counts.setdefault(header.message_type, 0)
                    message_counts[header.message_type] += 1
                except ValueError as e:
                    offset += 1
                    _logger.trace('%s Rewinding to offset %d (0x%x).' % (str(e), offset, offset))
                    in_fd.seek(offset, os.SEEK_SET)

        if valid_count > 0:
            _logger.debug('Found %d valid FusionEngine messages.' % valid_count)
            for type, count in message_counts.items():
                _logger.debug('  %s: %d' % (MessageType.get_type_string(type), count))
        else:
            _logger.debug('No FusionEngine messages found.')
            os.remove(output_path)

    if return_counts:
        return valid_count, message_counts
    else:
        return valid_count


def locate_log(input_path, log_base_dir='/logs', return_output_dir=False, return_log_id=False):
    """!
    @brief Locate a FusionEngine `*.p1log` file, or a binary file containing a mixed stream of FusionEngine messages and
           other content.

    If a mixed binary file is found, extract the FusionEngine content into a `*.p1log` file in the same directory.

    If `input_path` is a file, the returned output directory will be the parent directory of that file. If it is a
    FusionEngine log, the returned output directory will be the log directory.

    See also @ref find_p1log_file().

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
        is_mixed_file = False
        _logger.error(str(e))
    except FileExistsError as e:
        is_mixed_file = True

    # If that fails, see if we can find a directory containing a mixed content binary file. If found, try to extract
    # FusionEngine messages from it.
    if is_mixed_file:
        # We already know where the file is, but we call find_log_file() anyway just to populate a result tuple for us.
        result = find_log_file(input_path, return_output_dir=return_output_dir, return_log_id=return_log_id)
        mixed_file_path = input_path
    else:
        _logger.info('Could not find a FusionEngine log directory containing a .p1log file. Searching for a P1 log '
                     'with mixed binary data.')
        try:
            result = find_log_file(input_path, candidate_files=CANDIDATE_MIXED_FILES, log_base_dir=log_base_dir,
                                   return_output_dir=return_output_dir, return_log_id=return_log_id)
            mixed_file_path = result[0]
        except (FileNotFoundError, RuntimeError) as e:
            _logger.error(str(e))
            result = [None]
            if return_output_dir:
                result.append(None)
            if return_log_id:
                result.append(None)
            return result

    # Now, search for FusionEngine messages within the mixed binary data.
    _logger.info("Found mixed-content log file '%s'." % mixed_file_path)
    log_dir = os.path.dirname(mixed_file_path)
    if is_mixed_file:
        fe_path = os.path.splitext(mixed_file_path)[0] + '.p1log'
    else:
        fe_path = os.path.join(log_dir, "fusion_engine.p1log")

    _logger.info("Extracting FusionEngine content to '%s'." % fe_path)
    num_messages = extract_fusion_engine_log(input_path=mixed_file_path, output_path=fe_path)
    if num_messages > 0:
        result = list(result)
        result[0] = fe_path
        return result
    else:
        _logger.warning('No FusionEngine data extracted from mixed data file.')
        return [None for _ in result]
