#!/usr/bin/env python3

import sys

# In this case, the utility get_mojo_file is very specific to mojo and
# may be required for the duration of mojo's use
from utils.mojo_utils import get_mojo_file

from zaza.configure import network

if __name__ == "__main__":
    net_topology_file = get_mojo_file("network.yaml")
    sys.exit(network.run_from_cli(net_topology_file=net_topology_file))
