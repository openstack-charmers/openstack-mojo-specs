#!/usr/bin/python
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils
import logging
import argparse
import time
import xml.dom.minidom
import re
import ast

def rabbit_status(unit)
    output = mojo_utils.remote_run(unit, remote_cmd='rabbitmqctl -q cluster_status')
    output = output.replace('\n', '')
    matchObj = re.search( r'running_nodes,(.*)}, {partitions', output)
    node_list = ast.literal_eval(matchObj.group(1))
    return [unit.replace('rabbit@' for unit in node_list ]


def unit_crm_online(unit):
    output = mojo_utils.remote_run(unit, remote_cmd='crm_mon -X')
    xml_out = output[0]
    tree = xml.dom.minidom.parseString(xml_out)
    itemlist = tree.getElementsByTagName('node')
    online_units = []
    for s in itemlist:
        if 'online' in s.attributes.keys() and s.attributes['online'].value == 'true':
            online_units.append(int(s.attributes['name'].value.split('-')[-1]))
    online_units.sort()
    return online_units

def check_crm_status(service):
    machine_numbers = []
    juju_units = mojo_utils.get_juju_units(service=service)
    if not juju_units:
        return
    output = mojo_utils.remote_run(juju_units[0], remote_cmd='which crm_mon || echo "Not Found"')
    if output[0].rstrip() == "Not Found":
        return
    for unit in juju_units:
        machine_numbers.append(mojo_utils.convert_unit_to_machinename(unit))
    machine_numbers.sort()
    for unit in juju_units:
        if machine_numbers != unit_crm_online(unit):
            raise Exception('Mismatch on crm status for service %s on unit %s' % (service, unit))

def main(argv):
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("term_method", default='juju', nargs='?')
    options = parser.parse_args()
    term_method = mojo_utils.parse_mojo_arg(options, 'term_method')
    skip_services = ['neutron-gateway', 'mongodb', 'heat']
    principle_services = mojo_utils.get_principle_services()
    services = [item for item in principle_services if item not in skip_services]
    for svc in services:
        doomed_service = services.pop(0)
        mojo_os_utils.delete_juju_leader(doomed_service)
        mojo_utils.juju_check_hooks_complete()
        mojo_utils.juju_status_check_and_wait()
        check_crm_status(doomed_service)
        mojo_utils.add_unit(doomed_service, unit_num=1)
        mojo_utils.juju_status_check_and_wait()
        check_crm_status(doomed_service)
        

if __name__ == "__main__":
    sys.exit(main(sys.argv))
