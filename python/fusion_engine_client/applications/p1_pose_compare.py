#!/usr/bin/env python3

if __package__ is None or __package__ == "":
    from import_utils import enable_relative_imports
    __package__ = enable_relative_imports(__name__, __file__)

from ..analysis.pose_compare import main as pose_compare_main


def main():
    pose_compare_main()


if __name__ == "__main__":
    main()
