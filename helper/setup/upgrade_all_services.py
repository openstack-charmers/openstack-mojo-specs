#!/usr/bin/env python3

import logging
import os
import sys

import utils.mojo_utils as mojo_utils

import zaza.model
from zaza.openstack.utilities import cli as cli_utils


def main(argv):
    cli_utils.setup_logging()
    switch_map = {
        'neutron-gateway': 'local:{}/{}'.format(os.environ['MOJO_SERIES'],
                                                'neutron-gateway')
    }

    logging.info("Upgrading base services")
    mojo_utils.upgrade_base_services(switch=switch_map)
    logging.info(
        "Waiting for units to begin executing upgrade of base services")
    zaza.model.wait_for_agent_status(status='executing')
    logging.info("Waiting for units to be idle")
    zaza.model.block_until_all_units_idle()

    logging.info("Upgrading remaining services")
    logging.info(
        "Waiting for units to begin executing upgrade of remaining services")
    mojo_utils.upgrade_non_base_services(switch=switch_map)
    logging.info("Waiting for units to be idle")
    zaza.model.block_until_all_units_idle()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
