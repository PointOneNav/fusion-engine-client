#!/usr/bin/env python3

if __package__ is None or __package__ == "":
    from import_utils import enable_relative_imports
    __package__ = enable_relative_imports(__name__, __file__)

from .p1_capture import main as p1_capture_main

def main():
    p1_capture_main(default_display_mode='quiet', default_output='-')


if __name__ == "__main__":
    main()
