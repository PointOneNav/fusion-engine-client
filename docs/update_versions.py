#!/usr/bin/env python3

import os
from packaging import version
import subprocess
import sys


if __name__ == "__main__":
    entry_template = """\
        <tr>
          <td>%(version)s%(current)s</td>
          <td><a href="/fusion-engine/%(version)s/index.html">Documentation</a></td>
          <td><a href="https://github.com/PointOneNav/fusion-engine-client/releases/tag/%(version)s">Release Notes</a></td>
        </tr>
"""

    entry_template_no_docs = """\
        <tr>
          <td>%(version)s%(current)s</td>
          <td></td>
          <td><a href="https://github.com/PointOneNav/fusion-engine-client/releases/tag/%(version)s">Release Notes</a></td>
        </tr>
"""

    # List available versions.
    versions = [version.parse(v.lstrip('v'))
                for v in subprocess.check_output(['git', 'tag']).decode('utf-8').strip().split()
                if v.startswith('v')]
    versions.sort(reverse=True)
    latest_version = versions[0]

    # Find the docs/ directory.
    docs_dir = os.path.dirname(os.path.abspath(__file__))

    # Set version number in Doxyfile.
    if len(sys.argv) > 1:
        current_version = sys.argv[1]
        if not current_version.startswith('v'):
            current_version = f'v{current_version}'

        with open('%s/../Doxyfile' % docs_dir, 'r') as f:
            file_contents = f.read()
            file_contents = file_contents.format(current_version=current_version)
        with open('%s/../Doxyfile.version' % docs_dir, 'w') as f:
            f.write(file_contents)

    # Generate include_header.js.
    with open('%s/include_header.js.template' % docs_dir, 'r') as f:
        file_contents = f.read()
        with open('%s/include_header.js' % docs_dir, 'w') as f:
            f.write(file_contents % {'latest_version': f'v{str(latest_version)}'})

    # Generate versions.html.
    FIRST_RELEASE_WITH_DOCS = version.Version('1.4.0')
    with open('%s/versions.html.template' % docs_dir, 'r') as f:
        file_contents = f.read()

        table_contents = ""
        for v in versions:
            if v >= FIRST_RELEASE_WITH_DOCS:
                template = entry_template
            else:
                template = entry_template_no_docs

            table_contents += template % {'version': f'v{str(v)}',
                                          'current': ' (Current)' if v == latest_version else ''}

        with open('%s/versions.html' % docs_dir, 'w') as f:
            f.write(file_contents % {'content': table_contents})
