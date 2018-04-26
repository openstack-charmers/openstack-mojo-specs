#!/usr/bin/env python
import sys
import utils.mojo_utils as mojo_utils
import argparse

from zaza import model
from zaza.charm_lifecycle import utils as lifecycle_utils
from zaza.utilities import _local_utils


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--service")
    parser.add_argument("--kv")
    parser.add_argument("--wait")
    options = parser.parse_args()
    application = _local_utils.parse_arg(options, 'service')
    key, value = _local_utils.parse_arg(options, 'kv').split("=")
    wait = _local_utils.parse_arg(options, 'wait')
    print("Wait: {}".format(wait))
    if wait is not None:
        wait = wait == 'True'
    print("Applicatoin: {}".format(application))
    print("Option: {}={}".format(key, value))
    print("Wait: {}".format(wait))
    model.set_application_config(
        lifecycle_utils.get_juju_model(), application, {key: value})
    if wait:
        mojo_utils.juju_wait_finished()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
