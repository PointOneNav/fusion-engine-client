import fnmatch
import glob
import os

from . import trace as logging
from ..messages import MessageType
from ..parsers.file_index import FileIndexBuilder, FileIndex
from ..parsers.mixed_log_reader import MixedLogReader

_logger = logging.getLogger('point_one.utils.log')

# Note: The spelling here is intentional.
MANIFEST_FILE_NAME = 'maniphest.json'

# The following files are listed order of priority. The first located file will be returned.
CANDIDATE_P1LOG_FILES = [
    # v- Typically captured at the time the log is recorded, or embedded in a mixed-binary log file and extracted
    # by extract_fusion_engine_log().
    'input.p1log',
    'fusion_engine.p1log',
    'output/fusion_engine.p1log',
]

CANDIDATE_MIXED_FILES = ['input.raw', 'input.bin', 'input.rtcm3']

# Determine the default log base directory in the following order of priority:
# - P1_LOG_BASE_DIR environment variable
# - If Windows, set to `My Documents/point_one/logs`
# - Otherwise (Linux/Mac):
#   - Use `/logs` if it exists
#   - Otherwise, use `~/point_one/logs`
#
# Note that this is the default value. It can still be overridden by setting `log_base_dir` in all functions below
# (typically controlled by a --log-base-dir argument to an application).
DEFAULT_LOG_BASE_DIR = os.getenv('P1_LOG_BASE_DIR')
if DEFAULT_LOG_BASE_DIR is None:
    if os.name == "nt":
        DEFAULT_LOG_BASE_DIR = os.path.expandvars("%USERPROFILE%/Documents/point_one/logs")
    else:
        if os.path.exists('/logs'):
            DEFAULT_LOG_BASE_DIR = '/logs'
        else:
            DEFAULT_LOG_BASE_DIR = os.path.expanduser("~/point_one/logs")


def find_log_by_pattern(pattern, log_base_dir=DEFAULT_LOG_BASE_DIR, allow_multiple=False,
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
    | Path                                | `1234`   | `1234$`  | `foo*/1234` | `foo_*/1234` |
    | `path/to/foo_bar/12345678`          | match    | no match | match       | match        |
    | `path/to/foo_/1234abcd`             | match    | no match | match       | match        |
    | `path/to/foo_bar/12345678/more/info`| no match | no match | no match    | no match     |
    | `path/to/foo/12345678`              | match    | no match | match       | no match     |
    | `path/to/foo_/abcd1234`             | no match | no match | no match    | no match     |
    | `path/to/foo/1234`                  | match    | match    | match       | no match     |

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
    #
    # If the pattern ends with '$', treat that as the end of the match and do not append a '*'.
    if len(pattern) == 0:
        raise ValueError('Search pattern not specified.')

    if pattern[0] == '/':
        match_pattern = ''
    else:
        match_pattern = '*/'

    if pattern[-1] == '$':
        match_pattern += pattern[:-1]
    else:
        match_pattern += pattern + '*'

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
            raise RuntimeError(
                "Found multiple logs that match pattern '%s'. Please be more specific.\n  %s" %
                (pattern, '\n  '.join([m[0] for m in matches])))
    elif len(matches) == 0:
        message = "Found no logs that match pattern '%s'." % pattern
        if not allow_multiple:
            raise FileNotFoundError(message)
        else:
            _logger.warning(message)

    return matches


def find_log_file(input_path, candidate_files=None, return_output_dir=False, return_log_id=False,
                  log_base_dir=DEFAULT_LOG_BASE_DIR, check_exact_match=True, check_pattern_match=True):
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
    @param check_exact_match If `True`, check if `input_path` is the path to a data file. Otherwise, skip this check and
           only perform a pattern search.
    @param check_pattern_match If `True` and `input_path` does not refer to a log file or directory, perform a pattern
           match using `input_path` as the pattern.

    @return The path to the located file or a tuple containing:
            - The path to the located file.
            - The path to the located output directory. Only provided if `return_output_dir` is `True`.
            - The log ID string, or `None` if the requested file is not part of a FusionEngine log. Only provided if
              `return_log_id` is `True`.
    """
    def _get_log_id(file_path):
        parent_dir = os.path.dirname(os.path.abspath(input_path))
        return os.path.basename(parent_dir)

    # Check if the input path is a file. If so, return it and set the output directory to its parent directory.
    if os.path.isfile(input_path) and check_exact_match:
        output_dir = os.path.dirname(input_path)
        if output_dir == "":
            output_dir = "."
        log_id = _get_log_id(input_path)
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

        def _search_directory(dir_path):
            for f in candidate_files:
                if f is None:
                    continue

                test_path = os.path.join(dir_path, f)
                if os.path.exists(test_path):
                    return test_path, dir_path, _get_log_id(test_path)
            return None, None, None

        if check_exact_match:
            dir_exists = os.path.isdir(input_path)
            if dir_exists:
                matching_input_path, log_dir, log_id = _search_directory(input_path)
                if matching_input_path is not None:
                    input_path = matching_input_path
        else:
            dir_exists = False

        # If we didn't find an exact match and the path contains a *, try a glob search in the current directory first.
        # For example, if they specified 'abc*', search for './abc*'.
        if log_dir is None and '*' in input_path:
            pattern = input_path
            matches = glob.glob(pattern)
            matching_input_path = None
            matching_log_dir = None
            matching_log_id = None
            for m in matches:
                if os.path.isdir(m):
                    matching_input_path, matching_log_dir, matching_log_id = _search_directory(m)
                    if matching_input_path is not None:
                        break
                else:
                    matching_input_path = m
                    matching_log_dir = os.path.dirname(matching_input_path)
                    if matching_log_dir == "":
                        matching_log_dir = "."
                    matching_log_id = None
                    break

            if matching_input_path is not None:
                if len(matches) == 1:
                    input_path = matching_input_path
                    log_dir = matching_log_dir
                    log_id = matching_log_id
                else:
                    raise RuntimeError(
                        "Found multiple logs that match pattern '%s'. Please be more specific.\n  %s" %
                        (pattern, '\n  '.join(matches)))

        # If the user didn't specify a directory, or the directory wasn't considered a valid log (i.e., didn't have any
        # of the candidate files in it), check if they provided a pattern match to a log (i.e., a partial log ID or a
        # search pattern (foo*/partial_id*)).
        if log_dir is None and check_pattern_match and not (input_path.startswith('./') or input_path.startswith('/')):
            if check_exact_match:
                if dir_exists:
                    _logger.info("Directory '%s' does not contain a data file. Attempting a pattern match." %
                                 input_path)
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

    if len(result) == 1:
        return result[0]
    else:
        return tuple(result)


def find_p1log_file(input_path, return_output_dir=False, return_log_id=False, log_base_dir=DEFAULT_LOG_BASE_DIR):
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

    @return The path to the located file or a tuple containing:
            - The path to the located file.
            - The path to the located output directory. Only provided if `return_output_dir` is `True`.
            - The log ID string, or `None` if the requested file is not part of a FusionEngine log. Only provided if
              `return_log_id` is `True`.
    """
    # The following files are listed order of priority. The first located file will be returned.
    candidate_files = CANDIDATE_P1LOG_FILES
    result = find_log_file(input_path, candidate_files=candidate_files, return_output_dir=return_output_dir,
                           return_log_id=return_log_id, log_base_dir=log_base_dir)
    if isinstance(result, tuple):
        p1log_path = result[0]
    else:
        p1log_path = result

    if p1log_path.endswith('.p1log') or p1log_path.endswith('filter/output/fe_service/output.p1bin'):
        return result
    else:
        # If we got here and find_log_file() didn't raise an exception, the user specified a file (not a directory) and
        # it does not end in .p1log. We'll assume it is not a .p1log file -- it may contained mixed contents, including
        # FusionEngine messages, but it is not a .p1log file with _exclusively_ FusionEngine messages.
        raise FileExistsError('Specified file is not a .p1log file.')


def extract_fusion_engine_log(input_path, output_path=None, warn_on_gaps=True, return_counts=False, save_index=True):
    """!
    @brief Extract FusionEngine data from a file containing mixed binary data.

    @param input_path The path to the binary file to be read.
    @param output_path The path to an output file to be generated. If `None`, set to `<prefix>.p1log`, where
           `input_path` is `<prefix>.<ext>`.
    @param warn_on_gaps If `True`, print a warning if gaps are detected in the data sequence numbers.
    @param return_counts If `True`, return the number of messages extracted for each message type.
    @param save_index If `True`, generate an index file to go along with the output file for faster reading in the
           future. See @ref FileIndex for details.

    @return A tuple containing:
            - The number of decoded messages.
            - A `dict` containing the number of messages extracted for each message type. Only provided if
              `return_counts` is `True`.
    """

    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + '.p1log'

    index_builder = FileIndexBuilder() if save_index else None

    with open(input_path, 'rb') as in_fd, open(output_path, 'wb') as out_path:
        reader = MixedLogReader(in_fd, warn_on_gaps=warn_on_gaps, save_index=False,
                                return_header=True, return_payload=True, return_bytes=True, return_offset=False,
                                show_progress=True)
        for header, payload, data in reader:
            if index_builder is not None:
                p1_time = payload.get_p1_time() if payload is not None else None
                index_builder.append(message_type=header.message_type, offset_bytes=out_path.tell(),
                                     p1_time=p1_time)
            out_path.write(data)

        if reader.valid_count > 0:
            _logger.debug('Found %d valid FusionEngine messages.' % reader.valid_count)
            for type, count in reader.message_counts.items():
                _logger.debug('  %s: %d' % (MessageType.get_type_string(type), count))
        else:
            _logger.debug('No FusionEngine messages found.')
            os.remove(output_path)

    if index_builder is not None:
        index_path = FileIndex.get_path(output_path)
        _logger.debug("Saving index file as '%s'." % index_path)
        index_builder.save(FileIndex.get_path(output_path), output_path)

    if return_counts:
        return reader.valid_count, reader.message_counts
    else:
        return reader.valid_count


def locate_log(input_path, log_base_dir=DEFAULT_LOG_BASE_DIR, return_output_dir=False, return_log_id=False,
               extract_fusion_engine_data=False):
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
    @param extract_fusion_engine_data If `True`, extract FusionEngine content from a file containing mixed binary data
           and generate a new `*.p1log` file. Otherwise, return the path to the located mixed binary file.

    @return The path to the located file or a tuple of:
            - The path to the located (or extracted) `*.p1log` file
            - The path to the located output directory. Only provided if `return_output_dir` is `True`.
            - The log ID string, or `None` if the requested file is not part of a FusionEngine log. Only provided if
              `return_log_id` is `True`.
    """
    input_path = os.path.expanduser(input_path)

    def _populate_result(input_file, output_dir, log_id):
        result = [input_file]
        if return_output_dir:
            result.append(output_dir)
        if return_log_id:
            result.append(log_id)

        if len(result) == 1:
            return result[0]
        else:
            return tuple(result)

    # Look for a log file/directory in the following order of priority:
    # 1. A file referred to by `input_path`.
    # 2. A directory referred to by `input_path` containing one of the possible candidate filenames (input.p1log,
    #    input.raw, etc.).
    # 3. If `input_path` contains a `*`, a file the specified pattern (e.g., `abc*` matches
    #    `abc123.p1log`, `/home/**/abc*` matches `/home/user/abc123.p1log`).
    # 4. If `input_path` contains a `*`, a directory matching the specified pattern and containing one of the candidate
    #    filenames (e.g., `abc*` matches `abc123/input.p1log`, `/home/**/abc*` matches `/home/user/abc123/input.p1log`).
    # 5. A directory under `log_base_dir` matching a pattern specified by `input_path` and containing one of the
    #    candidate filenames (e.g., `<log_base_dir>/<input_path>*/input.p1log`).
    #
    # The log file may contain exclusively FusionEngine messages, or may contain mixed binary content.
    try:
        candidate_files = CANDIDATE_P1LOG_FILES
        candidate_files += CANDIDATE_MIXED_FILES
        log_file_path, output_dir, log_id = find_log_file(
            input_path, candidate_files=candidate_files, log_base_dir=log_base_dir,
            return_output_dir=True, return_log_id=True)
    except (FileNotFoundError, RuntimeError) as e:
        _logger.error(str(e))
        return _populate_result(None, None, None)

    # Found a log file.
    _logger.info("Found log file '%s'." % log_file_path)

    # Now, search for and extract FusionEngine messages within the mixed binary data to create a *.p1log file if
    # requested, or simply return the path to the mixed content file.
    parts = os.path.splitext(log_file_path)
    if parts[1] != '.p1log' and extract_fusion_engine_data:
        # If the user specified an actual file, use its name to set the *.p1log file name.
        if os.path.isfile(input_path):
            fe_path = parts[0] + '.p1log'
        # Otherwise, if they specified a pattern and searched for a log directory, save the output as
        # fusion_engine.p1log.
        else:
            fe_path = os.path.join(output_dir, "fusion_engine.p1log")

        _logger.info("Extracting FusionEngine content to '%s'." % fe_path)
        num_messages = extract_fusion_engine_log(input_path=log_file_path, output_path=fe_path)
        if num_messages > 0:
            log_file_path = fe_path
        else:
            _logger.warning('No FusionEngine data extracted from mixed data file.')
            return _populate_result(None, None, None)

    # Search successful.
    return _populate_result(log_file_path, output_dir, log_id)
