import fnmatch
import os

import logging

_logger = logging.getLogger('point_one.utils.log')

MANIFEST_FILE_NAME = 'maniphest.json'


# Taken from Logunitas logutil.py.
def find_log(pattern, log_base_dir='/logs', allow_multiple=False):
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
            # Match directories that:
            # - Match the full search pattern
            # - AND whose name matches the last element in the search pattern
            # - AND that contain a maniphest.json file
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
            _logger.error("Found multiple logs that match pattern '%s'. Please be more specific." % pattern)
            _logger.error('Matches: ')
            _logger.error(matches)

    if len(matches) == 0:
        _logger.warning("Found no logs that match pattern '%s'." % pattern)

    return matches


def find_p1bin(input_path, load_original=False, return_output_dir=False, return_log_id=False):
    """!
    @brief Locate a FusionEngine `*.p1bin` file.

    If `input_path` is a file, the returned output directory will be the parent directory of that file. If it is an
    Atlas log, the returned output directory will be the log directory.

    @param input_path The path to a `.p1bin` file, or to an Atlas log directory containing FusionEngine output.
    @param load_original If `True`, load the `.p1bin` file originally recorded with the Atlas log. Otherwise, load the
           log playback output if it exists (default).
    @param return_output_dir If `True`, return the output directory associated with the located input file.
    @param return_log_id If `True`, return the ID of the log if the requested path is an Atlas log.

    @return - The path to the located file.
            - The path to the located output directory. Only provided if `return_output_dir` is `True`.
            - The log ID string, or `None` if the requested file is not part of an Atlas log.
    """
    # Check if the input path is a file. If so, return it and set the output directory to its parent directory.
    if os.path.isfile(input_path):
        output_dir = os.path.dirname(input_path)
        log_id = None
    # If the input path is a directory, see if it's an Atlas log or pattern matches to a log. If so, set the output
    # directory to the log directory (not the subdirectory containing the p1bin file).
    else:
        # A valid Atlas logs will contain a manifest file.
        dir_exists = os.path.isdir(input_path)
        log_dir = None
        log_id = None
        if dir_exists and os.path.exists(os.path.join(input_path, MANIFEST_FILE_NAME)):
            log_dir = input_path
            log_id = os.path.basename(log_dir)
        # Check if this is a pattern matching to a log (i.e., a partial log ID or a search pattern (foo*/partial_id*)).
        else:
            _logger.info("File '%s' not found. Searching for a matching log." % input_path)
            matches = find_log(input_path)
            if len(matches) > 1:
                # find_log() will print an error.
                raise RuntimeError('Unable to locate requested log.')
            elif len(matches) == 1:
                log_dir = matches[0][0]
                log_id = matches[0][1]

        # If the input path wasn't a file, wasn't a log directory, and didn't pattern match to a log directory, there's
        # nothing to be found.
        if log_id is None:
            if dir_exists:
                raise FileNotFoundError("Directory '%s' is not a valid Atlas log." % input_path)
            else:
                raise FileNotFoundError("File/log '%s' not found." % input_path)
        # If we found a log directory, see if it contains an output file.
        else:
            # Check for a FusionEngine output file.
            #
            # If a playback file exists, load that first over the original file unless the user specifically says to
            # load the originally recorded file. In that case, the playback file paths will be set to None and ignored
            # in the loop below.
            candidate_files = [os.path.join(log_dir, 'output', 'fusion_engine.playback.p1bin')
                               if not load_original else None,
                               os.path.join(log_dir, 'output', 'fusion_engine.p1bin'),
                               # Legacy path, maintained for backwards compatibility.
                               os.path.join(log_dir, 'filter', 'output', 'fe_service', 'output.playback.p1bin')
                               if not load_original else None,
                               os.path.join(log_dir, 'filter', 'output', 'fe_service', 'output.p1bin')]
            input_path = None
            for path in candidate_files:
                if path is not None and os.path.exists(path):
                    input_path = path
                    output_dir = log_dir
                    break

            if input_path is None:
                raise FileNotFoundError("No .p1bin file found for log '%s' (%s)." % (log_id, log_dir))

    result = [input_path]
    if return_output_dir:
        result.append(output_dir)
    if return_log_id:
        result.append(log_id)

    return result
