#!/usr/bin/env python3
import sys
import utils.mojo_utils as mojo_utils
import logging

from zaza.openstack.utilities import juju as juju_utils


def process_ring_info(ring_info):
    ring_data = {}
    for line in ring_info.split('\n'):
        if line == "":
            continue
        hashsum, filename = line.split()
        ring_data[filename] = hashsum
    return ring_data


def verify_ring_data(ring_data):
    ring_dict = next(iter(ring_data.values()))
    for unit in ring_data.keys():
        if ring_data[unit] != ring_dict:
            return False
    return True


sp_units = mojo_utils.get_juju_units('swift-proxy')
ring_data = {}

for unit in sp_units:
    cmd = 'ls -1 /etc/swift/*{.builder,.ring.gz,arse} 2>/dev/null ' \
          '| xargs -l md5sum'
    out = juju_utils.remote_run(unit, remote_cmd=cmd)
    ring_data[unit] = process_ring_info(out)

if verify_ring_data(ring_data):
    logging.info('Ring data consistent accross proxies')
    sys.exit(0)
else:
    logging.error('Ring data inconsistent accross proxies')
    sys.exit(1)
