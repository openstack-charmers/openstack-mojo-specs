#!/usr/bin/python

import sys

import utils.mojo_utils as mojo_utils


def main(argv):
    # Mount the storage volume
    mojo_utils.remote_run('gluster/0', 'mkdir /mnt/gluster && mount -t glusterfs localhost:test /mnt/gluster')
    mojo_utils.remote_run('gluster/1', 'mkdir /mnt/gluster && mount -t glusterfs localhost:test /mnt/gluster')
    mojo_utils.remote_run('gluster/2', 'mkdir /mnt/gluster && mount -t glusterfs localhost:test /mnt/gluster')

    # Check
    mojo_utils.remote_run('gluster/0', 'echo 123456789 > /mnt/gluster/test_input')

    # Check
    output = mojo_utils.remote_run('gluster/1', 'cat /mnt/gluster/test_input')

    # Cleanup
    mojo_utils.remote_run('gluster/2', 'rm /mnt/gluster/test_input')
    if output[0].strip() != "123456789":
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
