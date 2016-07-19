#!/usr/bin/python

import sys

import utils.mojo_utils as mojo_utils


def main(argv):
    # Check
    mojo_utils.remote_run('ceph-mon/0', 'echo 123456789 > /tmp/input.txt')
    mojo_utils.remote_run(
        'ceph-mon/0', 'rados put -p rbd test_input /tmp/input.txt')

    # Check
    mojo_utils.remote_run(
        'ceph-mon/1', 'rados get -p rbd test_input /tmp/input.txt')
    output = mojo_utils.remote_run('ceph-mon/1', 'cat /tmp/input.txt')

    # Cleanup
    mojo_utils.remote_run('ceph-mon/2', 'rados rm -p rbd test_input')
    if output[0].strip() != "123456789":
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
