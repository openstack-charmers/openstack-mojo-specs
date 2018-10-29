#!/usr/bin/env python3

import sys

from zaza.utilities import juju as juju_utils


def main(argv):
    # Mount the storage volume
    juju_utils.remote_run(
        'gluster/0',
        remote_cmd=('mkdir /mnt/gluster && mount -t glusterfs localhost:test '
                    '/mnt/gluster'))
    juju_utils.remote_run(
        'gluster/1',
        remote_cmd=('mkdir /mnt/gluster && mount -t glusterfs localhost:test '
                    '/mnt/gluster'))
    juju_utils.remote_run(
        'gluster/2',
        remote_cmd=('mkdir /mnt/gluster && mount -t glusterfs localhost:test '
                    '/mnt/gluster'))

    # Check
    juju_utils.remote_run(
        'gluster/0', remote_cmd='echo 123456789 > /mnt/gluster/test_input')

    # Check
    output = juju_utils.remote_run(
        'gluster/1', remote_cmd='cat /mnt/gluster/test_input')

    # Cleanup
    juju_utils.remote_run(
        'gluster/2', remote_cmd='rm /mnt/gluster/test_input')
    if output.strip() != "123456789":
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
