#!/usr/bin/python

import utils.mojo_utils as mojo_utils
import sys
from collections import Counter
import time
import logging

def get_machine_state(juju_status, state_type):
    states = Counter()
    for machine_no in juju_status['machines']:
        if state_type in juju_status['machines'][machine_no]:
            state = juju_status['machines'][machine_no][state_type]
        else:
            state = 'unknown'
        states[state] += 1
    return states


def get_machine_agent_states(juju_status):
    return get_machine_state(juju_status, 'agent-state')


def get_machine_instance_states(juju_status):
    return get_machine_state(juju_status, 'instance-state')


def get_service_agent_states(juju_status):
    service_state = Counter()
    for service in juju_status['services']:
        if 'units' in juju_status['services'][service]:
            for unit in juju_status['services'][service]['units']:
                unit_info = juju_status['services'][service]['units'][unit]
                service_state[unit_info['agent-state']] += 1
                if 'subordinates' in unit_info:
                    for sub_unit in unit_info['subordinates']:
                        sub_sstate = \
                            unit_info['subordinates'][sub_unit]['agent-state']
                        service_state[sub_sstate] += 1
    return service_state


def status_summary(heading, statetype, states):
    print heading
    print "   " + statetype
    for state in states:
        print "    %s: %i" % (state, states[state])


def error_check(states):
    for state in states:
        if state in mojo_utils.JUJU_STATUSES['bad']:
            logging.error('Some statuses are in a bad state')
            return True
    logging.info('No statuses are in a bad state')
    return False


def all_stable(states):
    for state in states:
        if state in mojo_utils.JUJU_STATUSES['transitional']:
            logging.info('Some statuses are in a transitional state')
            return False
    logging.info('Statuses are in a stable state')
    return True


def run_check():
    checks = {
        'Machines': [{ 
                     'Heading': 'Instance State',
                     'check_func': get_machine_instance_states,
                    },
                    {
                     'Heading': 'Agent State',
                     'check_func': get_machine_agent_states,
                    }],
        'Services': [{
                     'Heading': 'Agent State',
                     'check_func': get_service_agent_states,
                    }]
    }
    stable_state = [False]
    while False in stable_state:
        juju_status = mojo_utils.get_juju_status()
        stable_state = []
        for juju_objtype, check_info in checks.iteritems():
            for check in check_info:
                check_function = check['check_func']
                states = check_function(juju_status)
                if error_check(states):
                    raise Exception("Error in juju status")
                stable_state.append(all_stable(states))
        time.sleep(5)
    for juju_objtype, check_info in checks.iteritems():
        for check in check_info:
            check_function = check['check_func']
            states = check_function(juju_status)
            status_summary(juju_objtype, check['Heading'], states)

def main(argv):
    return run_check()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
