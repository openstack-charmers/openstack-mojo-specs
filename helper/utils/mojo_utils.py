#!/usr/bin/python

import logging
import mojo
import os
import shutil
import subprocess
import time
import yaml
from collections import Counter

JUJU_STATUSES = {
    'good': ['ACTIVE', 'started'],
    'bad': ['error'],
    'transitional': ['pending', 'pending', 'down', 'installed', 'stopped',
                     'allocating'],
}


def get_juju_status(service=None, unit=None):
    cmd = ['juju', 'status', '--format=yaml']
    if service:
        cmd.append(service)
    if unit:
        cmd.append(unit)
    status_file = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout
    return yaml.load(status_file)


def get_juju_env_name(juju_status=None):
    if not juju_status:
        juju_status = get_juju_status()
    return juju_status['environment']


def get_juju_units(juju_status=None, service=None):
    if not juju_status:
        juju_status = get_juju_status()
    units = []
    if service:
        services = [service]
    else:
        services = [svc for svc in juju_status['services']]
    for svc in services:
        if 'units' in juju_status['services'][svc]:
            for unit in juju_status['services'][svc]['units']:
                units.append(unit)
    return units


def get_principle_services(juju_status=None):
    if not juju_status:
        juju_status = get_juju_status()
    p_services = []
    for svc in juju_status['services']:
        if 'subordinate-to' not in juju_status['services'][svc]:
            p_services.append(svc)
    return p_services


def convert_unit_to_machineno(unit):
    juju_status = get_juju_status(unit)
    return juju_status['machines'].itervalues().next()['instance-id']


def convert_unit_to_machinename(unit):
    juju_status = get_juju_status(unit)
    service = unit.split('/')[0]
    return int(juju_status['services'][service]['units'][unit]['machine'])


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


def remote_shell_check(unit, timeout=None):
    cmd = ['juju', 'run']
    if timeout:
        cmd.extend(['--timeout', str(timeout)])
    cmd.extend(['--unit', unit, 'uname -a'])
    FNULL = open(os.devnull, 'w')
    return not subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)


def remote_run(unit, remote_cmd=None, timeout=None, fatal=None):
    if fatal is None:
        fatal = True
    cmd = ['juju', 'run', '--unit', unit]
    if timeout:
        cmd.extend(['--timeout', str(timeout)])
    if remote_cmd:
        cmd.append(remote_cmd)
    else:
        cmd.append('uname -a')
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    output = p.communicate()
    if p.returncode != 0 and fatal:
        raise Exception('Error running remote command')
    return output


def remote_upload(unit, script, remote_dir=None):
    if remote_dir:
        dst = unit + ':' + remote_dir
    else:
        dst = unit + ':/tmp/'
    cmd = ['juju', 'scp', script, dst]
    return subprocess.check_call(cmd)


def delete_unit_juju(unit):
    service = unit.split('/')[0]
    unit_count = len(get_juju_units(service=service))
    logging.info('Removing unit ' + unit)
    cmd = ['juju', 'destroy-unit', unit]
    subprocess.check_call(cmd)
    target_num = unit_count - 1
    # Wait for the unit to disappear from juju status
    while len(get_juju_units(service=service)) > target_num:
        # Check no hooks are in error state
        juju_status_check_and_wait()
        time.sleep(5)
    juju_wait_finished()


def panic_unit(unit):
    panic_cmd = 'sudo bash -c "echo c > /proc/sysrq-trigger"'
    remote_run(unit, timeout='5s', remote_cmd=panic_cmd, fatal=False)


def delete_unit_openstack(unit):
    from novaclient.v1_1 import client as novaclient
    server_id = convert_unit_to_machineno(unit)
    cloud_creds = get_undercloud_auth()
    auth = {
        'username': cloud_creds['OS_USERNAME'],
        'api_key': cloud_creds['OS_PASSWORD'],
        'auth_url': cloud_creds['OS_AUTH_URL'],
        'project_id': cloud_creds['OS_TENANT_NAME'],
        'region_name': cloud_creds['OS_REGION_NAME'],
    }
    nc = novaclient.Client(**auth)
    server = nc.servers.find(id=server_id)
    server.delete()


def delete_unit_provider(unit):
    if get_provider_type() == 'openstack':
        delete_unit_openstack(unit)


def delete_unit(unit, method='juju'):
    if method == 'juju':
        delete_unit_juju(unit)
    elif method == 'kernel_panic':
        panic_unit(unit)
    elif method == 'provider':
        delete_unit_provider(unit)


def delete_oldest(service, method='juju'):
    units = unit_sorted(get_juju_units(service=service))
    delete_unit(units[0], method='juju')


def delete_machine(machine):
    mach_no = machine.split('-')[-1]
    unit = convert_machineno_to_unit(mach_no)
    delete_unit(unit)


def is_crm_clustered(service):
    juju_status = get_juju_status(service)
    return 'ha' in juju_status['services'][service]['relations']


def unit_sorted(units):
    """Return a sorted list of unit names."""
    return sorted(
        units, lambda a, b: cmp(int(a.split('/')[-1]), int(b.split('/')[-1])))


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


def juju_set(service, option, wait=None):
    if wait is None:
        wait = True
    logging.info('Setting %s to %s' % (service, option))
    subprocess.check_call(['juju', 'set', service, option])
    if wait:
        juju_wait_finished()


def juju_get_config_keys(service):
    cmd = ['juju', 'get', service]
    juju_get_output = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout
    service_config = yaml.load(juju_get_output)
    return service_config['settings'].keys()


def juju_get(service, option):
    cmd = ['juju', 'get', service]
    juju_get_output = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout
    service_config = yaml.load(juju_get_output)
    if 'value' in service_config['settings'][option]:
        return service_config['settings'][option]['value']


def get_juju_environments_yaml():
    juju_env_file = open(os.environ['HOME'] + "/.juju/environments.yaml", 'r')
    return yaml.load(juju_env_file)


def get_provider_type():
    juju_env = subprocess.check_output(['juju', 'switch']).strip('\n')
    juju_env_contents = get_juju_environments_yaml()
    return juju_env_contents['environments'][juju_env]['type']


def get_undercloud_auth():
    juju_env = subprocess.check_output(['juju', 'switch']).strip('\n')
    juju_env_contents = get_juju_environments_yaml()
    novarc_settings = juju_env_contents['environments'][juju_env]
    auth_settings = {
        'OS_AUTH_URL': novarc_settings['auth-url'],
        'OS_TENANT_NAME': novarc_settings['tenant-name'],
        'OS_USERNAME': novarc_settings['username'],
        'OS_PASSWORD': novarc_settings['password'],
        'OS_REGION_NAME': novarc_settings['region'],
    }
    return auth_settings


def get_undercloud_netid():
    juju_env = subprocess.check_output(['juju', 'switch']).strip('\n')
    juju_env_contents = get_juju_environments_yaml()
    if 'network' in juju_env_contents['environments'][juju_env]:
        return juju_env_contents['environments'][juju_env]['network']


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


def wipe_charm_dir():
    charm_base_dir = get_charm_dir()
    build_dir = os.environ['MOJO_BUILD_DIR']
    for charm in os.listdir(charm_base_dir):
        shutil.rmtree(os.path.join(charm_base_dir, charm))
    for charm in os.listdir(build_dir):
        shutil.rmtree(os.path.join(build_dir, charm))


def sync_all_charmhelpers():
    charm_base_dir = get_charm_dir()
    for direc in os.listdir(charm_base_dir):
        charm_dir = os.path.join(charm_base_dir, direc)
        if os.path.isdir(charm_dir):
            sync_charmhelpers(charm_dir)


def upgrade_service(svc, switch=None):
    repo_dir = os.environ['MOJO_REPO_DIR']
    logging.info('Upgrading ' + svc)
    cmd = ['juju', 'upgrade-charm']
    if switch and switch.get(svc):
        cmd.extend(['--switch', switch[svc]])
    cmd.extend(['--repository', repo_dir, svc])
    subprocess.check_call(cmd)


def upgrade_all_services(juju_status=None, switch=None):
    if not juju_status:
        juju_status = get_juju_status()
    # Upgrade base charms first
    base_charms = ['mysql', 'percona-cluster', 'rabbitmq-server',
                   'keystone']
    for svc in base_charms:
        if svc in juju_status['services']:
            upgrade_service(svc, switch=switch)
            time.sleep(30)
    time.sleep(60)
    # Upgrade the rest
    for svc in juju_status['services']:
        if svc not in base_charms:
            upgrade_service(svc, switch=switch)
            time.sleep(30)


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
    logging.debug(heading)
    logging.debug("   " + statetype)
    for state in states:
        logging.debug("    %s: %i" % (state, states[state]))


def juju_status_error_check(states):
    for state in states:
        if state in JUJU_STATUSES['bad']:
            logging.error('Some statuses are in a bad state')
            return True
    logging.debug('No statuses are in a bad state')
    return False


def juju_status_all_stable(states):
    for state in states:
        if state in JUJU_STATUSES['transitional']:
            logging.debug('Some statuses are in a transitional state')
            return False
    logging.debug('Statuses are in a stable state')
    return True


def juju_status_check_and_wait():
    checks = {
        'Machines': [
            {
                'Heading': 'Instance State',
                'check_func': get_machine_instance_states,
            },
            {
                'Heading': 'Agent State',
                'check_func': get_machine_agent_states,
            }
        ],
        'Services': [
            {
                'Heading': 'Agent State',
                'check_func': get_service_agent_states,
            }
        ]
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
    juju_wait.wait()


def dict_to_yaml(dict_data):
    return yaml.dump(dict_data, default_flow_style=False)


def get_network_env_vars():
    """Get environment variables with names which are consistent with
    network.yaml keys;  Also get network environment variables as commonly
    used by openstack-charm-testing and ubuntu-openstack-ci automation.
    Return a dictionary compatible with mojo-openstack-specs network.yaml
    key structure."""

    # Example o-c-t & uosci environment variables:
    #   NET_ID="a705dd0f-5571-4818-8c30-4132cc494668"
    #   GATEWAY="172.17.107.1"
    #   CIDR_EXT="172.17.107.0/24"
    #   CIDR_PRIV="192.168.121.0/24"
    #   NAMESERVER="10.5.0.2"
    #   FIP_RANGE="172.17.107.200:172.17.107.249"
    #   AMULET_OS_VIP00="172.17.107.250"
    #   AMULET_OS_VIP01="172.17.107.251"
    #   AMULET_OS_VIP02="172.17.107.252"
    #   AMULET_OS_VIP03="172.17.107.253"
    _vars = {}
    _vars['net_id'] = os.environ.get('NET_ID')
    _vars['external_dns'] = os.environ.get('NAMESERVER')
    _vars['default_gateway'] = os.environ.get('GATEWAY')
    _vars['external_net_cidr'] = os.environ.get('CIDR_EXT')
    _vars['private_net_cidr'] = os.environ.get('CIDR_PRIV')

    _fip_range = os.environ.get('FIP_RANGE')
    if _fip_range and ':' in _fip_range:
        _vars['start_floating_ip'] = os.environ.get('FIP_RANGE').split(':')[0]
        _vars['end_floating_ip'] = os.environ.get('FIP_RANGE').split(':')[1]

    _vips = [os.environ.get('AMULET_OS_VIP00'),
             os.environ.get('AMULET_OS_VIP01'),
             os.environ.get('AMULET_OS_VIP02'),
             os.environ.get('AMULET_OS_VIP03')]

    # Env var naming consistent with network.yaml takes priority
    _keys = ['default_gateway'
             'start_floating_ip',
             'end_floating_ip',
             'external_dns',
             'external_net_cidr',
             'external_net_name',
             'external_subnet_name',
             'network_type',
             'private_net_cidr',
             'router_name']
    for _key in _keys:
        _val = os.environ.get(_key)
        if _val:
            _vars[_key] = _val

    # Remove keys and items with a None value
    _vars['vips'] = filter(None, _vips)
    for k, v in _vars.items():
        if not v:
            del _vars[k]

    return _vars


def get_net_info(net_topology, ignore_env_vars=False):
    """Get network info from network.yaml, override the values if specific
    environment variables are set."""
    net_info = get_mojo_config('network.yaml')[net_topology]

    if not ignore_env_vars:
        logging.info('Consuming network environment variables as overrides.')
        net_info.update(get_network_env_vars())

    logging.info('Network info: {}'.format(dict_to_yaml(net_info)))
    return net_info


def get_pkg_version(service, pkg):
    versions = []
    for unit in get_juju_units(service=service):
        cmd = 'dpkg -l | grep {}'.format(pkg)
        out = remote_run(unit, cmd)
        versions.append(out[0].split()[2])
    if len(set(versions)) != 1:
        raise Exception('Unexpected output from pkg version check')
    return versions[0]


def get_ubuntu_version(service):
    versions = []
    for unit in get_juju_units(service=service):
        cmd = 'lsb_release -sc'
        out = remote_run(unit, cmd)
        versions.append(out[0].split()[0])
    if len(set(versions)) != 1:
        raise Exception('Unexpected output from ubuntu version check')
    return versions[0]


def setup_logging():
    logFormatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")
    rootLogger = logging.getLogger()
    rootLogger.setLevel('INFO')
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)
