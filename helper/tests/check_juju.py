#!/usr/bin/env python3
import sys

# Deprecated: Replace juju_wait* with zaza.model.wait_for_application_states
# This may require exporting JUJU_MODEL into the environment
from utils.mojo_utils import juju_wait_finished

if __name__ == '__main__':
    sys.exit(juju_wait_finished())
