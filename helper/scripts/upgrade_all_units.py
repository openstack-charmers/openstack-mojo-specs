#!/usr/bin/env python
import sys
import utils.mojo_utils as mojo_utils
import os
import argparse


def main(args):
    mojo_utils.setup_logging()
    mojo_utils.upgrade_all_units(config=args)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--from')
    parser.add_argument('--to')
    options = parser.parse_args()
    args = {}
    args['from'] = mojo_utils.parse_mojo_arg(options, 'from')
    args['to'] = mojo_utils.parse_mojo_arg(options, 'to')
    sys.exit(main(args))
