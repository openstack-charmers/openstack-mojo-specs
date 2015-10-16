#!/usr/bin/python
import sys
import utils.mojo_utils as mojo_utils
import os


def main(argv):
    mojo_utils.setup_logging()
    switch_map = {
        'neutron-gateway': 'local:{}/{}'.format(os.environ['MOJO_SERIES'],
                                                'neutron-gateway')
    }
    mojo_utils.upgrade_all_services(switch=switch_map)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
