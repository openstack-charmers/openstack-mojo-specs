#!/usr/bin/python

import utils.mojo_utils as mojo_utils
import sys
from collections import Counter


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
    error_states = ['error']
    for state in states:
        if state in error_states:
            return True
    return False


def run_check():
    juju_status = mojo_utils.get_juju_status()

    machine_instance_states = get_machine_instance_states(juju_status)
    machine_agent_states = get_machine_agent_states(juju_status)
    service_agent_states = get_service_agent_states(juju_status)

    status_summary('Machines', 'Instance State', machine_instance_states)
    status_summary('Machines', 'Agent State', machine_agent_states)
    status_summary('Services', 'Agent State', service_agent_states)
    if (error_check(machine_instance_states) or
            error_check(machine_agent_states) or
            error_check(service_agent_states)):
        raise Exception("Error in juju status")


def main(argv):
    return run_check()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
