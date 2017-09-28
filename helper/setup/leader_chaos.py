#!/usr/bin/env python
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils
import logging
import argparse
import xml.dom.minidom
import re
import ast


def rabbit_unit_status(unit):
    cmd = 'rabbitmqctl -q cluster_status'
    output = mojo_utils.remote_run(unit, remote_cmd=cmd)[0]
    output = output.replace('\n', '')
    matchObj = re.search(r'running_nodes,(.*)}, {partitions', output)
    machine_numbers = []
    for machine in ast.literal_eval(matchObj.group(1)):
        machine_numbers.append(int(machine.split('-')[-1]))
    return machine_numbers


def rabbit_status():
    juju_units = mojo_utils.get_juju_units(service='rabbitmq-server')
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
    output = mojo_utils.remote_run(unit, remote_cmd='crm_mon -X')
    xml_out = output[0]
    tree = xml.dom.minidom.parseString(xml_out)
    itemlist = tree.getElementsByTagName('node')
    online_units = []
    for s in itemlist:
        if 'online' in s.attributes.keys() \
                and s.attributes['online'].value == 'true':
            online_units.append(int(s.attributes['name'].value.split('-')[-1]))
    online_units.sort()
    return online_units


def get_machine_numbers(service):
    juju_units = mojo_utils.get_juju_units(service=service)
    machine_numbers = []
    for unit in juju_units:
        machine_numbers.append(mojo_utils.convert_unit_to_machinename(unit))
    machine_numbers.sort()
    return machine_numbers


def check_crm_status(service):
    juju_units = mojo_utils.get_juju_units(service=service)
    if not juju_units:
        return
    cmd = 'which crm_mon || echo "Not Found"'
    output = mojo_utils.remote_run(juju_units[0], remote_cmd=cmd)
    if output[0].rstrip() == "Not Found":
        return
    for unit in juju_units:
        mach_nums = get_machine_numbers(service)
        crm_online = unit_crm_online(unit)
        if mach_nums == crm_online:
            logging.info('Service %s status on %s look good' % (service, unit))
        else:
            logging.info('%s != %s' % (str(mach_nums), str(crm_online)))
            msg = ('Mismatch on crm status for service {} '
                   'on unit {}'.format(service, unit))
            raise Exception(msg)


def check_cluster_status(service):
    if service == 'rabbitmq-service':
        rabbit_status()
    else:
        check_crm_status(service)


def main(argv):
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("term_method", default='juju', nargs='?')
    skip_services = ['neutron-gateway', 'mongodb', 'heat', 'rabbitmq-server']
    princ_services = mojo_utils.get_principle_services()
    services = [item for item in princ_services if item not in skip_services]
    for svc in services:
        doomed_service = services.pop(0)
        mojo_os_utils.delete_juju_leader(doomed_service)
        mojo_utils.juju_check_hooks_complete()
        mojo_utils.juju_status_check_and_wait()
        check_cluster_status(doomed_service)
        mojo_utils.add_unit(doomed_service, unit_num=1)
        mojo_utils.juju_status_check_and_wait()
        mojo_utils.juju_check_hooks_complete()
        check_crm_status(doomed_service)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
