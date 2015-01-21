#!/usr/bin/python
import sys
import utils.mojo_utils as mojo_utils
import logging
import argparse


def main(argv):
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    default_service = 'all'
    parser.add_argument("--service", default=default_service)
    options = parser.parse_args()
    service = mojo_utils.parse_mojo_arg(options, 'service')
    if service == 'all':
        units = mojo_utils.get_juju_units()
    else:
        units = mojo_utils.get_juju_units(service=service)
    for unit in units:
        logging.info('Running nagios check(s) on ' + unit)
        cmd = "ls -l /etc/nagios/nrpe.d/* 2>/dev/null | wc -l"
        check_count = mojo_utils.remote_run(unit, cmd)[0]
        if int(check_count) > 0:
            try:
                cmd = "grep -Eoh '/usr.*' /etc/nagios/nrpe.d/* | bash -e"
                mojo_utils.remote_run(unit, cmd)
            except:
                pass
        else:
            logging.warn('No nagios checks found on ' + unit)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
