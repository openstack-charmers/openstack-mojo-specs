#!/usr/bin/env python
import sys
from utils.mojo_utils import juju_wait_finished

if __name__ == '__main__':
    sys.exit(juju_wait_finished())
