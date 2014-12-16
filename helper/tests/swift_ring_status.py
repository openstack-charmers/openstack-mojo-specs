#!/usr/bin/python

import utils.mojo_utils as mojo_utils

def process_ring_info(ring_info):
    ring_data = {}
    for line in ring_info.split('\n'):
        if line == "":
            continue
        hashsum, filename = line.split()
        ring_data[filename] = hashsum
    return ring_data

juju_status = mojo_utils.get_juju_status(service='swift-proxy')
sp_units = mojo_utils.get_juju_units(juju_status=juju_status)
ring_data = {}
for unit in sp_units:
    cmd = "ls -1 /etc/swift/*{.builder,.ring.gz,arse} 2>/dev/null | xargs -l md5sum"
    out, err = mojo_utils.remote_run(unit, remote_cmd=cmd)
    ring_data[unit] = process_ring_info(out)
print ring_data
