#!/usr/bin/env python3

import sys

from zaza.charm_tests.dragent import test


if __name__ == "__main__":
    sys.exit(test.run_from_cli())
