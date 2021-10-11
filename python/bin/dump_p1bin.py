#!/usr/bin/env python3

import os
import sys

root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.utils.dump_p1bin import main


if __name__ == "__main__":
    main()
