import fnmatch
import os

import logging

_logger = logging.getLogger('point_one.utils.log')

# Note: The spelling here is intentional.
MANIFEST_FILE_NAME = 'maniphest.json'


def find_fusion_engine_log(pattern, log_base_dir='/logs', allow_multiple=False,
                           log_test_filenames=(MANIFEST_FILE_NAME,), return_test_file=False):
    """!
    @brief Locate a FusionEngine log directory.

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
        # Omit /logs/reports.
        if root == log_base_dir:
            try:
                dirnames.remove('reports')
            except ValueError:
                pass

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
    @brief Locate a FusionEngine log data file.

    This function locates a data file within a FusionEngine log directory, searching for the first match to a list of
    candidate files within the log directory.

    ```
    /logs/2021-10-01/
      abcdef/
        fusion_engine.p1log
        maniphest.json

    > find_log_file(input_path='abc', candidate_files=['fusion_engine.p1log'])
    /logs/2021-10-01/abcdef/fusion_engine.p1log
    ```

    If `input_path` is a file, the returned output directory will be the parent directory of that file. If it is a
    FusionEngine log directory, the returned output directory will be the log directory itself.

    @param input_path The path to a data file, a FusionEngine log directory, or a pattern to be matched (see @ref
           find_fusion_engine_log()).
    @param candidate_files A list of one or more data files to be located within the log directory, in order of
           priority. If `None`, defaults to `fusion_engine.p1log`.
    @param return_output_dir If `True`, return the output directory associated with the located input file.
    @param return_log_id If `True`, return the ID of the log if the requested path is a FusionEngine log.
    @param log_base_dir The base directory to be searched when performing a pattern match for a log directory.

    @return - The path to the located file.
            - The path to the located output directory. Only provided if `return_output_dir` is `True`.
            - The log ID string, or `None` if the requested file is not part of a FusionEngine log.
    """
    # Check if the input path is a file. If so, return it and set the output directory to its parent directory.
    if os.path.isfile(input_path):
        output_dir = os.path.dirname(input_path)
        log_id = None
    # If the input path is a directory, see if it's a P1 log. If it is not a directory, see if it pattern matches to a
    # log directory within `log_base_dir`. If so for either case, set the output directory to the log directory (note
    # that the .p1log may be contained within a subdirectory).
    else:
        if candidate_files is None:
            candidate_files = ['fusion_engine.p1log']
        elif not isinstance(candidate_files, (tuple, list)):
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
                matches = find_fusion_engine_log(input_path, log_base_dir=log_base_dir,
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


def find_p1log_file(input_path, return_output_dir=False, return_log_id=False, log_base_dir='/logs',
                    load_original=False):
    """!
    @brief Locate a FusionEngine `*.p1log` file.

    If `input_path` is a file, the returned output directory will be the parent directory of that file. If it is a
    FusionEngine log, the returned output directory will be the log directory.

    @param input_path The path to a `.p1log` file, a FusionEngine log directory, or a pattern to be matched (see @ref
           find_fusion_engine_log()).
    @param return_output_dir If `True`, return the output directory associated with the located input file.
    @param return_log_id If `True`, return the ID of the log if the requested path is a FusionEngine log.
    @param log_base_dir The base directory to be searched when performing a pattern match for a log directory.
    @param load_original If `True`, load the `.p1log` file originally recorded with the log. Otherwise, load the log
           playback output if it exists (default).

    @return - The path to the located file.
            - The path to the located output directory. Only provided if `return_output_dir` is `True`.
            - The log ID string, or `None` if the requested file is not part of a FusionEngine log.
    """
    # If a playback file exists, load that first over the original file unless the user specifically says to load the
    # originally recorded file. In that case, the playback file paths will be set to None and ignored in the loop below.
    # Note that the playback file is currently stored in a different directory.
    candidate_files = ['output/fusion_engine.playback.p1log' if not load_original else None,
                       'fusion_engine.p1log',
                       # Legacy path, maintained for backwards compatibility.
                       'filter/output/fe_service/output.playback.p1bin' if not load_original else None,
                       'filter/output/fe_service/output.p1bin']
    return find_log_file(input_path, candidate_files=candidate_files, return_output_dir=return_output_dir,
                         return_log_id=return_log_id, log_base_dir=log_base_dir)
