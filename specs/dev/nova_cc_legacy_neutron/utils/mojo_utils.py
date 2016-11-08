#!/usr/bin/python

import subprocess
import yaml
import os
import mojo
import logging
import time
import sys
from collections import Counter

JUJU_STATUSES = {
    'good': ['ACTIVE', 'started'],
    'bad': ['error'],
    'transitional': ['pending', 'pending', 'down', 'installed', 'stopped'],
}

def get_juju_status(service=None):
    cmd = ['juju', 'status', '--format=yaml']
    if service:
        cmd.append(service)
    status_file = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout
    return yaml.load(status_file)


def get_juju_units(juju_status=None, service=None):
    if not juju_status:
        juju_status = get_juju_status()
    units = []
    if service:
        services = [service]
    else:
        services = [service for service in juju_status['services']]
    for svc in services:
        if 'units' in juju_status['services'][svc]:
            for unit in juju_status['services'][svc]['units']:
                units.append(unit)
    return units


def convert_machineno_to_unit(machineno, juju_status=None):
    if not juju_status:
        juju_status = get_juju_status()
    services = [service for service in juju_status['services']]
    for svc in services:
        if 'units' in juju_status['services'][svc]:
            for unit in juju_status['services'][svc]['units']:
                unit_info = juju_status['services'][svc]['units'][unit]
                if unit_info['machine'] == machineno:
                    return unit


def remote_shell_check(unit):
    cmd = ['juju', 'run', '--unit', unit, 'uname -a']
    FNULL = open(os.devnull, 'w')
    return not subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)


def remote_run(unit, remote_cmd=None):
    cmd = ['juju', 'run', '--unit', unit]
    if remote_cmd:
        cmd.append(remote_cmd)
    else:
        cmd.append('uname -a')
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    output = p.communicate()
    if p.returncode != 0:
        raise Exception('Error running remote command')
    return output


def remote_upload(unit, script, remote_dir=None):
    if remote_dir:
        dst = unit + ':' + remote_dir
    else:
        dst = unit + ':/tmp/'
    cmd = ['juju', 'scp', script, dst]
    return subprocess.check_call(cmd)


def delete_unit(unit):
    service = unit.split('/')[0]
    unit_count = len(get_juju_units(service=service))
    logging.info('Removing unit ' + unit)
    cmd = ['juju', 'destroy-unit', unit]
    subprocess.check_call(cmd)
    target_num = unit_count - 1
    # Wait for the unit to disappear from juju status
    while len(get_juju_units(service=service)) > target_num:
        time.sleep(5)
    juju_wait_finished()


def delete_machine(machine):
    mach_no = machine.split('-')[-1]
    unit = convert_machineno_to_unit(mach_no)
    delete_unit(unit)


def add_unit(service, unit_num=None):
    unit_count = len(get_juju_units(service=service))
    if unit_num:
        additional_units = int(unit_num)
    else:
        additional_units = 1
    logging.info('Adding %i unit(s) to %s' % (additional_units, service))
    cmd = ['juju', 'add-unit', service, '-n', str(additional_units)]
    subprocess.check_call(cmd)
    target_num = unit_count + additional_units
    # Wait for the new unit to appear in juju status
    while len(get_juju_units(service=service)) < target_num:
        time.sleep(5)
    juju_wait_finished()


def juju_set(service, option):
    subprocess.check_call(['juju', 'set', service, option])
    juju_wait_finished()


def juju_get(service, option):
    cmd = ['juju', 'get', service]
    juju_get_output = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout
    service_config = yaml.load(juju_get_output)
    if 'value' in service_config['settings'][option]:
        return service_config['settings'][option]['value']


def get_undercloud_auth():
    juju_env = subprocess.check_output(['juju', 'switch']).strip('\n')
    juju_env_file = open(os.environ['HOME'] + "/.juju/environments.yaml", 'r')
    juju_env_contents = yaml.load(juju_env_file)
    novarc_settings = juju_env_contents['environments'][juju_env]
    auth_settings = {
        'OS_AUTH_URL': novarc_settings['auth-url'],
        'OS_TENANT_NAME': novarc_settings['tenant-name'],
        'OS_USERNAME': novarc_settings['username'],
        'OS_PASSWORD': novarc_settings['password'],
        'OS_REGION_NAME': novarc_settings['region'],
    }
    return auth_settings


# Openstack Client helpers
def get_auth_url(juju_status=None):
    if juju_get('keystone', 'vip'):
        return juju_get('keystone', 'vip')
    if not juju_status:
        juju_status = get_juju_status()
    unit = juju_status['services']['keystone']['units'].itervalues().next()
    return unit['public-address']


def get_overcloud_auth(juju_status=None):
    if not juju_status:
        juju_status = get_juju_status()
    if juju_get('keystone', 'use-https').lower() == 'yes':
        transport = 'https'
        port = 35357
    else:
        transport = 'http'
        port = 5000
    address = get_auth_url()
    auth_settings = {
        'OS_AUTH_URL': '%s://%s:%i/v2.0' % (transport, address, port),
        'OS_TENANT_NAME': 'admin',
        'OS_USERNAME': 'admin',
        'OS_PASSWORD': 'openstack',
        'OS_REGION_NAME': 'RegionOne',
    }
    return auth_settings


def get_mojo_file(filename):
    if 'MOJO_SPEC_DIR' in os.environ:
        spec = mojo.Spec(os.environ['MOJO_SPEC_DIR'])
        mfile = spec.get_config(filename, stage=os.environ['MOJO_STAGE'])
    else:
        if os.path.isfile(filename):
            mfile = filename
    return mfile


def get_mojo_config(filename):
    config_file = get_mojo_file(filename)
    logging.info('Using config %s' % (config_file))
    return yaml.load(file(config_file, 'r'))


def get_charm_dir():
    return os.path.join(os.environ['MOJO_REPO_DIR'],
                        os.environ['MOJO_SERIES'])


def sync_charmhelpers(charmdir):
    p = subprocess.Popen(['make', 'sync'], cwd=charmdir)
    p.communicate()


def sync_all_charmhelpers():
    charm_base_dir = get_charm_dir()
    for direc in os.listdir(charm_base_dir):
        charm_dir = os.path.join(charm_base_dir, direc)
        if os.path.isdir(charm_dir):
            sync_charmhelpers(charm_dir)


def parse_mojo_arg(options, mojoarg, multiargs=False):
    if mojoarg.upper() in os.environ:
        if multiargs:
            return os.environ[mojoarg.upper()].split()
        else:
            return os.environ[mojoarg.upper()]
    else:
        return getattr(options, mojoarg)


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


def juju_status_summary(heading, statetype, states):
    print heading
    print "   " + statetype
    for state in states:
        print "    %s: %i" % (state, states[state])


def juju_status_error_check(states):
    for state in states:
        if state in JUJU_STATUSES['bad']:
            logging.error('Some statuses are in a bad state')
            return True
    logging.info('No statuses are in a bad state')
    return False


def juju_status_all_stable(states):
    for state in states:
        if state in JUJU_STATUSES['transitional']:
            logging.info('Some statuses are in a transitional state')
            return False
    logging.info('Statuses are in a stable state')
    return True


def juju_status_check_and_wait():
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
        juju_status = get_juju_status()
        stable_state = []
        for juju_objtype, check_info in checks.iteritems():
            for check in check_info:
                check_function = check['check_func']
                states = check_function(juju_status)
                if juju_status_error_check(states):
                    raise Exception("Error in juju status")
                stable_state.append(juju_status_all_stable(states))
        time.sleep(5)
    for juju_objtype, check_info in checks.iteritems():
        for check in check_info:
            check_function = check['check_func']
            states = check_function(juju_status)
            juju_status_summary(juju_objtype, check['Heading'], states)


def remote_runs(units):
    for unit in units:
        if not remote_shell_check(unit):
            raise Exception('Juju run failed on ' + unit)


def juju_check_hooks_complete():
    juju_units = get_juju_units()
    remote_runs(juju_units)
    remote_runs(juju_units)


def juju_wait_finished():
    # Wait till all statuses are green
    juju_status_check_and_wait()
    # juju status may report all has finished but hooks are still firing. So check..
    juju_check_hooks_complete()
    # Check nothing has subsequently gone bad
    juju_status_check_and_wait()
