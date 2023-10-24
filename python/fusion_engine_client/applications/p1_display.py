#!/usr/bin/env python3

import os
import sys

# If this application is being run directly as a script (e.g., python p1_*.py), rather than as a script installed by pip
# (e.g., p1_*), manually set the package name and add the Python root directory (fusion-engine-client/python/) to the
# import search path to enable relative imports.
if __name__ == "__main__":
    root_dir = os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(__file__)), '../..'))
    sys.path.insert(0, root_dir)
    __package__ = os.path.dirname(__file__).replace('/', '.')


from ..analysis.analyzer import main as analyzer_main


def main():
    analyzer_main()


if __name__ == "__main__":
    main()
