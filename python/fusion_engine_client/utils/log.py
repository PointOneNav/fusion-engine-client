import fnmatch
import os

import logging

_logger = logging.getLogger('point_one.utils.log')

# Note: The spelling here is intentional.
MANIFEST_FILE_NAME = 'maniphest.json'


def find_fusion_engine_log(pattern, log_base_dir='/logs', allow_multiple=False):
    """!
    @brief Locate a FusionEngine log directory.

    FusionEngine data logs are typically a directory, named with a unique hash, containing a JSON log manifest file and
    binary input/output data files. This function can locate a requested log directory under a base directory based on
    a user-specified pattern as follows:
    - Path to the directory matches the full search pattern
    - AND the deepest subdirectory name matches the last element in the search pattern
    - AND the subdirectory contain a manifest file

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

    @return A list containing entries for each matching log. Each entry is a tuple containing the path and the log ID.
            If `allow_multiple == False`, the list will always contain exactly one entry.
    """
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
            if (fnmatch.fnmatch(path, match_pattern) and fnmatch.fnmatch(dirname, last_element) and
                os.path.exists(os.path.join(path, MANIFEST_FILE_NAME))):
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


def find_p1log_file(input_path, return_output_dir=False, return_log_id=False, log_base_dir='/logs'):
    """!
    @brief Locate a FusionEngine `*.p1log` file.

    If `input_path` is a file, the returned output directory will be the parent directory of that file. If it is an
    Atlas log, the returned output directory will be the log directory.

    @param input_path The path to a `.p1log` file or FusionEngine log directory, or a pattern to be matched (see @ref
           find_fusion_engine_log()).
    @param return_output_dir If `True`, return the output directory associated with the located input file.
    @param return_log_id If `True`, return the ID of the log if the requested path is an Atlas log.
    @param log_base_dir The base directory to be searched when performing a pattern match for a log directory.

    @return - The path to the located file.
            - The path to the located output directory. Only provided if `return_output_dir` is `True`.
            - The log ID string, or `None` if the requested file is not part of an Atlas log.
    """
    # Check if the input path is a file. If so, return it and set the output directory to its parent directory.
    if os.path.isfile(input_path):
        output_dir = os.path.dirname(input_path)
        log_id = None
    # If the input path is a directory, see if it's an Atlas log or pattern matches to a log. If so, set the output
    # directory to the log directory (not the subdirectory containing the p1log file).
    else:
        # A valid Atlas logs will contain a manifest file.
        dir_exists = os.path.isdir(input_path)
        if dir_exists and os.path.exists(os.path.join(input_path, MANIFEST_FILE_NAME)):
            log_dir = input_path
            log_id = os.path.basename(log_dir)
        # Check if this is a pattern matching to a log (i.e., a partial log ID or a search pattern (foo*/partial_id*)).
        else:
            _logger.info("File '%s' not found. Searching for a matching log." % input_path)
            try:
                matches = find_fusion_engine_log(input_path, log_base_dir=log_base_dir)
                log_dir = matches[0][0]
                log_id = matches[0][1]
            except RuntimeError as e:
                raise e
            except FileNotFoundError as e:
                if dir_exists:
                    raise FileNotFoundError("Directory '%s' is not a valid Atlas log." % input_path)
                else:
                    raise e

        # If we found a log directory, see if it contains a FusionEngine output file.
        candidate_files = [os.path.join(log_dir, 'fusion_engine.p1log'),
                           # Legacy path, maintained for backwards compatibility.
                           os.path.join(log_dir, 'filter', 'output', 'fe_service', 'output.p1bin')]
        input_path = None
        for path in candidate_files:
            if os.path.exists(path):
                input_path = path
                output_dir = log_dir
                break

        if input_path is None:
            raise FileNotFoundError("No .p1log file found for log '%s' (%s)." % (log_id, log_dir))

    result = [input_path]
    if return_output_dir:
        result.append(output_dir)
    if return_log_id:
        result.append(log_id)

    return result
