#!/usr/bin/env python3
import logging
import sys

import zaza.model

# Unused import
# from zaza.openstack.utilities import (
#     cli as cli_utils,
# )


def main(argv):
    zaza.openstack.utilities.cli.setup_logging()
    logging.info('Setting up ceilometer schema')
    action = zaza.model.run_action_on_leader(
        'ceilometer',
        'ceilometer-upgrade',
        action_params={})
    if action.status != "completed":
        raise Exception(
            "ceilometer-upgrade action returned {} status".format(
                action.status))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
