#!/usr/bin/python
import utils.mojo_utils as mojo_utils

mojo_utils.juju_check_hooks_complete()
mojo_utils.juju_status_check_and_wait()
