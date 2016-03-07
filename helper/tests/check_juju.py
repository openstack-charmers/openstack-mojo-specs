#!/usr/bin/python
import sys
from utils.juju_wait import wait
from utils.mojo_utils import juju_wait_finished

if __name__ == '__main__':
    sys.exit(juju_wait_finished())
