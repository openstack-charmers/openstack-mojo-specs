#!/usr/bin/python
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils
import logging
import argparse


def main(argv):
    cert_script = mojo_utils.get_mojo_config('checksum_keystone_certs.py')
    remote_script = '/home/ubuntu/checksum_keystone_certs.py'
    hashes = set()
    for unit in mojo_utils.get_juju_units(service='keystone'):
        mojo_utils.remote_upload(unit, cert_script, remote_script)
        hashes.add(mojo_utils.remote_run(unit, remote_script)[0].strip())
    if len(hashes) != 1:
        raise Exception('Keystone cert mismatch')


if __name__ == "__main__":
    sys.exit(main(sys.argv))
