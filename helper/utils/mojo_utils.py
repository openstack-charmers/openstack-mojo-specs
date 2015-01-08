#!/usr/bin/python

import subprocess
import yaml
import os
import mojo
import logging
import time

JUJU_STATUSES = {
    'good': ['ACTIVE', 'started'],
    'bad': ['error'],
    'transitional': ['pending', 'pending', 'down', 'installed'],
}

def get_juju_status(service=None):
    cmd = ['juju', 'status']
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
    return p.communicate()


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


def juju_set(service, option):
    subprocess.check_call(['juju', 'set', service, option])


def juju_get(service, option):
    cmd = ['juju', 'get', service]
    juju_get_output = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout
    service_config = yaml.load(juju_get_output)
    return service_config['settings'][option]['value']


def get_undercload_auth():
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


def get_overcloud_auth(juju_status=None):
    if not juju_status:
        juju_status = get_juju_status()
    # xxx Need to account for https
    if juju_get('keystone', 'use-https').lower() == 'yes':
        transport = 'https'
        port = 35357
    else:
        transport = 'http'
        port = 5000
    unit = juju_status['services']['keystone']['units'].itervalues().next()
    address = unit['public-address']
    auth_settings = {
        'OS_AUTH_URL': '%s://%s:%i/v2.0' % (transport, address, port),
        'OS_TENANT_NAME': 'admin',
        'OS_USERNAME': 'admin',
        'OS_PASSWORD': 'openstack',
        'OS_REGION_NAME': 'RegionOne',
    }
    return auth_settings


def get_mojo_config(filename):
    spec = mojo.Spec(os.environ['MOJO_SPEC_DIR'])
    config_file = spec.get_config(filename, stage=os.environ['MOJO_STAGE'])
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
