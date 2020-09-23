#!/usr/bin/env python3

import os
import subprocess
import sys

if __name__ == "__main__":
    entry_template = """\
        <tr>
          <td>%(version)s%(current)s</td>
          <td><a href="%(version)s/index.html">Documentation</a></td>
          <td><a href="https://github.com/PointOneNav/fusion-engine-client/releases/tag/%(version)s">Release Notes</a></td>
        </tr>
"""

    # List available versions.
    versions = subprocess.check_output(['git', 'tag']).decode('utf-8').strip().split()
    versions.sort(key=lambda s: list(map(int, s.lstrip('v').split('.'))), reverse=True)
    latest_version = versions[0]

    # Find the docs/ directory.
    docs_dir = os.path.dirname(os.path.abspath(__file__))

    # Set version number in Doxyfile.
    if len(sys.argv) > 1:
        current_version = sys.argv[1]

        with open('%s/../Doxyfile' % docs_dir, 'r') as f:
            file_contents = f.read()
            file_contents = file_contents.format(current_version=current_version)
        with open('%s/../Doxyfile.version' % docs_dir, 'w') as f:
            f.write(file_contents)

    # Generate include_header.js.
    with open('%s/include_header.js.template' % docs_dir, 'r') as f:
        file_contents = f.read()
        with open('%s/include_header.js' % docs_dir, 'w') as f:
            f.write(file_contents % {'latest_version': latest_version})

    # Generate versions.html.
    with open('%s/versions.html.template' % docs_dir, 'r') as f:
        file_contents = f.read()

        table_contents = ""
        for version in versions:
            table_contents += entry_template % {'version': version,
                                                'current': ' (Current)' if version == latest_version else ''}

        with open('%s/versions.html' % docs_dir, 'w') as f:
            f.write(file_contents % {'content': table_contents})
