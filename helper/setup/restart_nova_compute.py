#!/usr/bin/env python3
import logging
import sys

import zaza.model

from zaza.openstack.utilities import (
    cli as cli_utils,
)


def main(argv):
    zaza.openstack.utilities.cli.setup_logging()
    logging.info('Restarting nova compute and scheduler')
    for unit in zaza.model.get_units('nova-compute'):
        zaza.model.run_on_unit(unit.name, 'systemctl restart nova-compute')
        logging.info('Restarted on {}'.format(unit.name))
    for unit in zaza.model.get_units('nova-cloud-controller'):
        zaza.model.run_on_unit(unit.name, 'systemctl restart nova-scheduler')
        logging.info('Restarted on {}'.format(unit.name))

if __name__ == "__main__":
    sys.exit(main(sys.argv))
