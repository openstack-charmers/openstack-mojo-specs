#!/usr/bin/env python3
import sys
import utils.mojo_utils as mojo_utils
import os

import zaza.model
from zaza.openstack.utilities import cli as cli_utils


def main(argv):
    cli_utils.setup_logging()
    switch_map = {
        'neutron-gateway': 'local:{}/{}'.format(os.environ['MOJO_SERIES'],
                                                'neutron-gateway')
    }
    mojo_utils.upgrade_base_services(switch=switch_map)
    zaza.model.block_until_all_units_idle()
    mojo_utils.upgrade_non_base_services(switch=switch_map)
    zaza.model.block_until_all_units_idle()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
