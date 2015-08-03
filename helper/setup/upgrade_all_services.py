#!/usr/bin/python
import sys
import utils.mojo_utils as mojo_utils
import logging
import os

def main(argv):
    logging.basicConfig(level=logging.INFO)
    switch_map = {
        'neutron-gateway': 'local:{}/{}'.format(os.environ['MOJO_SERIES'],
                                                'neutron-gateway')
    }
    mojo_utils.upgrade_all_services(switch=switch_map)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
