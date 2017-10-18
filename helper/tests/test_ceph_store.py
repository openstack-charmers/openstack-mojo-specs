#!/usr/bin/env python

import sys

import utils.mojo_utils as mojo_utils
import argparse


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("application",  default="ceph-mon", nargs="*")
    parser.add_argument("units", default=[0, 1], nargs="*")
    options = parser.parse_args()
    application = mojo_utils.parse_mojo_arg(options,
                                            'application', multiargs=False)
    units = mojo_utils.parse_mojo_arg(options, 'units', multiargs=True)

    mojo_utils.remote_run(
        '{}/{}'.format(application, units[0]), 'ceph osd pool create rbd 128 || true')
    # Check
    mojo_utils.remote_run(
        '{}/{}'.format(application, units[0]),
        'echo 123456789 > /tmp/input.txt')
    mojo_utils.remote_run(
        '{}/{}'.format(application, units[0]),
        'rados put -p rbd test_input /tmp/input.txt')

    # Check
    mojo_utils.remote_run(
        '{}/{}'.format(application, units[-1]),
        'rados get -p rbd test_input /tmp/input.txt')
    output = mojo_utils.remote_run(
        '{}/{}'.format(application, units[-1]),
        'cat /tmp/input.txt')

    # Cleanup
    mojo_utils.remote_run(
        '{}/{}'.format(application, units[-1]),
        'rados rm -p rbd test_input')
    if output[0].strip() != "123456789":
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
