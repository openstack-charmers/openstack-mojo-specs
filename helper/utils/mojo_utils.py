#!/usr/bin/env python

import logging
import os
import shutil
import subprocess
import time
import yaml
import utils.juju_wait as juju_wait
from collections import Counter

import kiki


JUJU_STATUSES = {
    'good': ['ACTIVE', 'started'],
    'bad': ['error'],
    'transitional': ['pending', 'pending', 'down', 'installed', 'stopped',
                     'allocating'],
}

JUJU_ACTION_STATUSES = {
    'good': ['completed'],
    'bad': ['fail'],
    'transitional': ['pending', 'running'],
}


class ConfigFileNotFound(Exception):
    pass


def get_juju_status(service=None, unit=None):
    cmd = [kiki.cmd(), 'status', '--format=yaml']
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
        services = [svc for svc in juju_status[kiki.applications()]]
    for svc in services:
        if 'units' in juju_status[kiki.applications()][svc]:
            for unit in juju_status[kiki.applications()][svc]['units']:
                units.append(unit)
    return units


def get_principle_services(juju_status=None):
    if not juju_status:
        juju_status = get_juju_status()
    p_services = []
    for svc in juju_status[kiki.applications()]:
        if 'subordinate-to' not in juju_status[kiki.applications()][svc]:
            p_services.append(svc)
    return p_services


def convert_unit_to_machineno(unit):
    juju_status = get_juju_status(unit)
    return juju_status['machines'].itervalues().next()['instance-id']


def convert_unit_to_machinename(unit):
    juju_status = get_juju_status(unit)
    service = unit.split('/')[0]
    return int(
        juju_status[kiki.applications()][service]['units'][unit]['machine'])


def convert_machineno_to_unit(machineno, juju_status=None):
    if not juju_status:
        juju_status = get_juju_status()
    services = [service for service in juju_status[kiki.applications()]]
    for svc in services:
        if 'units' in juju_status[kiki.applications()][svc]:
            for unit in juju_status[kiki.applications()][svc]['units']:
                unit_info = juju_status[
                    kiki.applications()][svc]['units'][unit]
                if unit_info['machine'] == machineno:
                    return unit


def remote_shell_check(unit, timeout=None):
    cmd = [kiki.cmd(), 'run']
    if timeout:
        cmd.extend(['--timeout', str(timeout)])
    cmd.extend(['--unit', unit, 'uname -a'])
    FNULL = open(os.devnull, 'w')
    return not subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)


def remote_run(unit, remote_cmd=None, timeout=None, fatal=None):
    if fatal is None:
        fatal = True
    cmd = [kiki.cmd(), 'run', '--unit', unit]
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
    cmd = [kiki.cmd(), 'scp', script, dst]
    return subprocess.check_call(cmd)


def delete_unit_juju(unit):
    service = unit.split('/')[0]
    unit_count = len(get_juju_units(service=service))
    logging.info('Removing unit ' + unit)
    cmd = [kiki.cmd(), kiki.remove_unit(), unit]
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


def delete_application(application, wait=True):
    logging.info('Removing application ' + application)
    cmd = [kiki.cmd(), kiki.remove_application(), application]
    subprocess.check_call(cmd)


def delete_oldest(service, method='juju'):
    units = unit_sorted(get_juju_units(service=service))
    delete_unit(units[0], method='juju')


def delete_machine(machine):
    mach_no = machine.split('-')[-1]
    unit = convert_machineno_to_unit(mach_no)
    delete_unit(unit)


def is_crm_clustered(service):
    juju_status = get_juju_status(service)
    return 'ha' in juju_status[kiki.applications()][service]['relations']


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
    cmd = [kiki.cmd(), 'add-unit', service, '-n', str(additional_units)]
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
    subprocess.check_call([kiki.cmd(), kiki.set_config(),
                           service, option])
    if wait:
        juju_wait_finished()


def juju_get_config_keys(service):
    cmd = [kiki.cmd(), kiki.get_config(), service]
    juju_get_output = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout
    service_config = yaml.load(juju_get_output)
    return service_config['settings'].keys()


def juju_get(service, option):
    cmd = [kiki.cmd(), kiki.get_config(), service]
    juju_get_output = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout
    service_config = yaml.load(juju_get_output)

    if (option in service_config['settings'] and
            'value' in service_config['settings'][option]):
        return service_config['settings'][option]['value']
    else:
        # Stable charms may not yet have the same config keys as next charms
        return None


def get_juju_environments_yaml():
    """ Get the environments.yaml data from a Juju 1 environment

    @returns Dictionary of the data from the environments.yaml file
    """
    juju_env_file = open(os.environ['HOME'] + "/.juju/environments.yaml", 'r')
    return yaml.load(juju_env_file)


def get_cloud_from_controller():
    """ Get the cloud name from the Juju 2.x controller

    @returns String name of the cloud for the current Juju 2.x controller
    """
    cmd = [kiki.cmd(), 'show-controller', '--format=yaml']
    cloud_config = yaml.load(subprocess.check_output(cmd))
    # There will only be one top level controller from show-controller,
    # but we do not know its name.
    assert len(cloud_config) == 1
    try:
        return cloud_config.values()[0]['details']['cloud']
    except KeyError:
        raise KeyError("Failed to get cloud information from the controller")


def get_provider_type():
    """ Get the type of the undercloud

    @returns String name of the undercloud type
    """
    juju_env = subprocess.check_output([kiki.cmd(), 'switch']).strip('\n')
    if kiki.version() < 2:
        juju_env_contents = get_juju_environments_yaml()
        return juju_env_contents['environments'][juju_env]['type']
    else:
        cloud = get_cloud_from_controller()
        if cloud:
            # If the controller was deployed from this system with
            # the cloud configured in ~/.local/share/juju/clouds.yaml
            # Determine the cloud type directly
            cmd = [kiki.cmd(), 'show-cloud', cloud, '--format=yaml']
            return yaml.load(subprocess.check_output(cmd))['type']
        else:
            # If the controller was deployed elsewhere
            # show-controllers unhelpfully returns an empty string for cloud
            # For now assume openstack
            return 'openstack'


class MissingOSAthenticationException(Exception):
    pass


def get_undercloud_auth():
    """ Get the undercloud OpenStack authentication settings from the
    environment.

    @raises MissingOSAthenticationException if one or more settings are
            missing.
    @returns Dictionary of authentication settings
    """

    os_auth_url = os.environ.get('OS_AUTH_URL')
    if os_auth_url:
        api_version = os_auth_url.split('/')[-1].translate(None, 'v')
    else:
        logging.error('Missing OS authentication setting: OS_AUTH_URL')
        raise MissingOSAthenticationException(
            'One or more OpenStack authetication variables could '
            'be found in the environment. Please export the OS_* '
            'settings into the environment.')

    logging.info('AUTH_URL: {}, api_ver: {}'.format(os_auth_url, api_version))

    if api_version == '2.0':
        # V2
        logging.info('Using keystone API V2 for undercloud auth')
        auth_settings = {
            'OS_AUTH_URL': os.environ.get('OS_AUTH_URL'),
            'OS_TENANT_NAME': os.environ.get('OS_TENANT_NAME'),
            'OS_USERNAME': os.environ.get('OS_USERNAME'),
            'OS_PASSWORD':  os.environ.get('OS_PASSWORD'),
            'OS_REGION_NAME': os.environ.get('OS_REGION_NAME'),
            'API_VERSION': 2,
        }
    elif api_version >= '3':
        # V3 or later
        logging.info('Using keystone API V3 (or later) for undercloud auth')
        domain = os.environ.get('OS_DOMAIN_NAME')
        auth_settings = {
            'OS_AUTH_URL': os.environ.get('OS_AUTH_URL'),
            'OS_USERNAME': os.environ.get('OS_USERNAME'),
            'OS_PASSWORD': os.environ.get('OS_PASSWORD'),
            'OS_REGION_NAME': os.environ.get('OS_REGION_NAME'),
            'API_VERSION': 3,
        }
        if domain:
            auth_settings['OS_DOMAIN_NAME': 'admin_domain'] = domain
        else:
            auth_settings['OS_USER_DOMAIN_NAME'] = (
                os.environ.get('OS_USER_DOMAIN_NAME'))
            auth_settings['OS_PROJECT_NAME'] = (
                os.environ.get('OS_PROJECT_NAME'))
            auth_settings['OS_PROJECT_DOMAIN_NAME'] = (
                os.environ.get('OS_PROJECT_DOMAIN_NAME'))
            os_project_id = os.environ.get('OS_PROJECT_ID')
            if os_project_id is not None:
                auth_settings['OS_PROJECT_ID'] = os_project_id

    # Validate settings
    for key, settings in auth_settings.items():
        if settings is None:
            logging.error('Missing OS authentication setting: {}'
                          ''.format(key))
            raise MissingOSAthenticationException(
                'One or more OpenStack authetication variables could '
                'be found in the environment. Please export the OS_* '
                'settings into the environment.')

    return auth_settings


# Openstack Client helpers
def get_auth_url(juju_status=None):
    if juju_get('keystone', 'vip'):
        return juju_get('keystone', 'vip')
    if not juju_status:
        juju_status = get_juju_status()
    unit = (juju_status[kiki.applications()]['keystone']['units']
            .itervalues()
            .next())
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

    if juju_get('keystone', 'preferred-api-version') in [2, None]:
        # V2 Explicitly, or None when charm does not possess the config key
        logging.info('Using keystone API V2 for overcloud auth')
        auth_settings = {
            'OS_AUTH_URL': '%s://%s:%i/v2.0' % (transport, address, port),
            'OS_TENANT_NAME': 'admin',
            'OS_USERNAME': 'admin',
            'OS_PASSWORD': 'openstack',
            'OS_REGION_NAME': 'RegionOne',
            'API_VERSION': 2,
        }
    elif juju_get('keystone', 'preferred-api-version') >= 3:
        # V3 or later
        logging.info('Using keystone API V3 (or later) for overcloud auth')
        auth_settings = {
            'OS_AUTH_URL': '%s://%s:%i/v3' % (transport, address, port),
            'OS_USERNAME': 'admin',
            'OS_PASSWORD': 'openstack',
            'OS_REGION_NAME': 'RegionOne',
            'OS_DOMAIN_NAME': 'admin_domain',
            'OS_USER_DOMAIN_NAME': 'admin_domain',
            'OS_PROJECT_NAME': 'admin',
            'OS_PROJECT_DOMAIN_NAME': 'admin_domain',
            'API_VERSION': 3,
        }
    return auth_settings


def get_mojo_file(filename):
    """Search for a stage specific version,
    then the current working directory,
    then in the directory where the script was called,
    then in the directory above where the script was called.

    @returns string path to configuration file
    @raises ConfigFileNotFound if no file can be located
    """
    files = []
    if 'MOJO_SPEC_DIR' in os.environ and 'MOJO_STAGE' in os.environ:
        # Spec location
        files.append('{}/{}/{}'.format(os.environ['MOJO_SPEC_DIR'],
                                       os.environ['MOJO_STAGE'], filename))

    # CWD
    files.append(filename)
    # Called file directory
    files.append(os.path.join(os.path.dirname(__file__), filename))
    # Up one directory from called file
    files.append(os.path.join(
                     os.path.dirname(os.path.dirname(__file__)),
                     filename))

    for file_path in files:
        if os.path.isfile(file_path):
            return file_path


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


def git_checkout_branch(charmdir, branch):
    # Check out branch, show remotes and branches
    logging.info('Checking out {} in {}'.format(branch, charmdir))
    cmds = [
        ['git', '-C', charmdir, 'checkout', branch],
        ['git', '-C', charmdir, 'remote', '-v'],
        ['git', '-C', charmdir, 'branch', '-lv', '--no-abbrev'],
    ]
    for cmd in cmds:
        subprocess.check_call(cmd)


def git_checkout_all(branch):
    charm_base_dir = get_charm_dir()
    for direc in os.listdir(charm_base_dir):
        charm_dir = os.path.join(charm_base_dir, direc)
        git_dir = os.path.join(charm_dir, '.git')
        if os.path.isdir(git_dir):
            git_checkout_branch(charm_dir, branch)


def upgrade_service(svc, charm_name=None, switch=None):
    if charm_name and os.path.exists(os.path.join(get_charm_dir(),
                                                  charm_name)):
         charm_dir = os.path.join(get_charm_dir(), charm_name)
    else:
         charm_dir = os.path.join(get_charm_dir(), svc)
    logging.info('Upgrading ' + svc)
    cmd = [kiki.cmd(), 'upgrade-charm']
    # Switch and path are now mutually exclusive
    if switch and switch.get(svc):
        cmd.extend(['--switch', charm_dir, svc])
    else:
        cmd.extend(['--path', charm_dir, svc])
    subprocess.check_call(cmd)


def upgrade_all_services(juju_status=None, switch=None):
    if not juju_status:
        juju_status = get_juju_status()
    # Upgrade base charms first
    base_charms = ['mysql', 'percona-cluster', 'rabbitmq-server',
                   'keystone']
    for svc in base_charms:
        if svc in juju_status[kiki.applications()]:
            charm_name = juju_status['applications'][svc]['charm-name']
            upgrade_service(svc, charm_name=charm_name, switch=switch)
            time.sleep(30)
    time.sleep(60)
    # Upgrade the rest
    for svc in juju_status[kiki.applications()]:
        if svc not in base_charms:
            charm_name = juju_status['applications'][svc]['charm-name']
            upgrade_service(svc, charm_name=charm_name, switch=switch)
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

    for service in juju_status[kiki.applications()]:
        if 'units' in juju_status[kiki.applications()][service]:
            for unit in juju_status[kiki.applications()][service]['units']:
                unit_info = juju_status[
                    kiki.applications()][service]['units'][unit]
                service_state[kiki.get_unit_info_state(unit_info)] += 1
                if 'subordinates' in unit_info:
                    for sub_unit in unit_info['subordinates']:
                        sub_sstate = (kiki.get_unit_info_state(
                            unit_info['subordinates'][sub_unit]))
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
    logging.warn('The juju_status_check_and_wait function is deprecated. '
                 ' Use juju_wait_finished instead.')
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


def juju_wait_finished(max_wait=2700):
    """Use juju-wait from local utils path to block until all service
    units quiesce and satisfy workload status ready state."""
    log = logging.getLogger()
    log.setLevel(logging.DEBUG)
    logging.info('Calling juju-wait')
    juju_wait.wait(log, wait_for_workload=True, max_wait=max_wait)
    logging.debug('End of juju-wait')


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


def action_get_output(action_id):
    cmd = kiki.show_action_output_cmd() + ['--format=yaml', action_id]
    return yaml.load(subprocess.check_output(cmd))


def action_get_status(action_id):
    return action_get_output(action_id)['status']


def action_wait(action_id, timeout=600):
    delay = 10
    run_time = 0
    while run_time < timeout:
        status = action_get_status(action_id)
        if status not in JUJU_ACTION_STATUSES['transitional']:
            break
        time.sleep(delay)
        run_time = run_time + delay


def action_run(unit, action_name, action_args=None, timeout=600):
    cmd = kiki.run_action_cmd() + ['--format=yaml', unit, action_name]
    if action_args:
        cmd.extend(action_args)
    action_out = yaml.load(subprocess.check_output(cmd))
    action_id = action_out['Action queued with id']
    if timeout:
        action_wait(action_id, timeout)
    return action_id
