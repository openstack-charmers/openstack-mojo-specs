#!/usr/bin/env python
import sys
import utils.mojo_utils as mojo_utils
import logging
import argparse
import xml.dom.minidom
import re
import ast

from zaza.utilities import _local_utils


def rabbit_unit_status(unit):
    cmd = 'rabbitmqctl -q cluster_status'
    output = _local_utils.remote_run(
        unit, remote_cmd=cmd)
    output = output.replace('\n', '')
    matchObj = re.search(r'running_nodes,(.*)}, {partitions', output)
    machine_numbers = []
    for machine in ast.literal_eval(matchObj.group(1)):
        machine_numbers.append(int(machine.split('-')[-1]))
    return machine_numbers


def rabbit_status():
    juju_units = mojo_utils.get_juju_units('rabbitmq-server')
    machine_numbers = get_machine_numbers('rabbitmq-server')
    for unit in juju_units:
        units = rabbit_unit_status(unit)
        units.sort()
        if machine_numbers == units:
            logging.info('Rabbit status on %s look good' % (unit))
        else:
            msg = 'Mismatch on rabbit status for on unit {}'.format(unit)
            raise Exception(msg)


def unit_crm_online(unit):
    xml_out = _local_utils.remote_run(
        unit, remote_cmd='crm_mon -X')
    tree = xml.dom.minidom.parseString(xml_out)
    itemlist = tree.getElementsByTagName('node')
    online_units = []
    for s in itemlist:
        if 'online' in s.attributes.keys() \
                and s.attributes['online'].value == 'true':
            online_units.append(int(s.attributes['name'].value.split('-')[-1]))
    online_units.sort()
    return online_units


def get_machine_numbers(application):
    juju_units = mojo_utils.get_juju_units(application)
    machine_numbers = []
    for unit in juju_units:
        machine_numbers.append(mojo_utils.convert_unit_to_machinename(unit))
    machine_numbers.sort()
    return machine_numbers


def check_crm_status(application):
    juju_units = mojo_utils.get_juju_units(application)
    if not juju_units:
        return
    cmd = 'which crm_mon || echo "Not Found"'
    output = _local_utils.remote_run(
        juju_units[0], remote_cmd=cmd)
    if output.rstrip() == "Not Found":
        return
    for unit in juju_units:
        mach_nums = get_machine_numbers(application)
        crm_online = unit_crm_online(unit)
        if mach_nums == crm_online:
            logging.info('Service %s status on %s look good'
                         .format((application, unit)))
        else:
            logging.info('%s != %s' % (str(mach_nums), str(crm_online)))
            msg = ('Mismatch on crm status for application {} '
                   'on unit {}'.format(application, unit))
            raise Exception(msg)


def check_cluster_status(application):
    if application == 'rabbitmq-application':
        rabbit_status()
    else:
        check_crm_status(application)


def main(argv):
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("term_method", default='juju', nargs='?')
    skip_applications = ['neutron-gateway', 'mongodb',
                         'heat', 'rabbitmq-server']
    princ_applications = mojo_utils.get_principle_applications()
    applications = [item for item in princ_applications
                    if item not in skip_applications]
    for svc in applications:
        doomed_application = applications.pop(0)
        mojo_utils.delete_juju_leader(doomed_application)
        mojo_utils.juju_check_hooks_complete()
        mojo_utils.juju_wait_finished()
        check_cluster_status(doomed_application)
        mojo_utils.add_unit(doomed_application, unit_num=1)
        mojo_utils.juju_wait_finished()
        mojo_utils.juju_check_hooks_complete()
        check_crm_status(doomed_application)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
