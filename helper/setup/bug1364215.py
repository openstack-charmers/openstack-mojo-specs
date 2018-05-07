#!/usr/bin/env python3
import sys
import utils.mojo_utils as mojo_utils
from zaza.utilitites import _local_utils


def main(argv):
    for unit in mojo_utils.get_juju_units('neutron-gateway'):
        cmd = 'sudo service neutron-plugin-openvswitch-agent restart'
        _local_utils.remote_run(unit, remote_cmd=cmd)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
