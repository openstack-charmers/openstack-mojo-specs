#!/usr/bin/env python
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils
import argparse

from zaza.utilitites import _local_utils


def main(argv):
    _local_utils.setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("term_method", default='juju', nargs='?')
    options = parser.parse_args()
    term_method = _local_utils.parse_arg(options, 'term_method')
    services = mojo_utils.get_principle_applications()
    for svc in services:
        doomed_service = services.pop(0)
        if mojo_utils.is_crm_clustered(doomed_service):
            mojo_os_utils.delete_crm_leader(doomed_service, method=term_method)
        else:
            mojo_utils.delete_oldest(doomed_service, method=term_method)
        mojo_utils.juju_check_hooks_complete()
        mojo_utils.juju_wait_finished()
        mojo_utils.add_unit(svc, unit_num=1)
        mojo_utils.juju_check_hooks_complete()
        mojo_utils.juju_wait_finished()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
