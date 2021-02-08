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
