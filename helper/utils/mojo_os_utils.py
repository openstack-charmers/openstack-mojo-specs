#!/usr/bin/env python3

import swiftclient
import glanceclient
from aodhclient.v2 import client as aodh_client
from novaclient import exceptions as novaclient_exceptions

import designateclient
import designateclient.client as designate_client
import designateclient.v1.domains as des_domains
import designateclient.v1.records as des_records
import designateclient.exceptions as des_exceptions

import logging
import re
import tempfile
import os
import six
import sys
import time
import subprocess
import paramiko
import dns.resolver

from zaza.openstack.utilities.os_versions import (
    OPENSTACK_CODENAMES,
)
from zaza.openstack.utilities import (
    generic as generic_utils,
    juju as juju_utils,
    openstack as openstack_utils,
)

if six.PY3:
    from urllib.request import urlretrieve
    from io import StringIO
else:
    from urllib import urlretrieve
    from StringIO import StringIO


sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import mojo_utils  # noqa


# Openstack Client helpers
def get_swift_creds(cloud_creds):
    auth = {
        'user': cloud_creds['OS_USERNAME'],
        'key': cloud_creds['OS_PASSWORD'],
        'authurl': cloud_creds['OS_AUTH_URL'],
        'tenant_name': cloud_creds['OS_TENANT_NAME'],
        'auth_version': '2.0',
    }
    return auth


def get_aodh_session_client(session):
    return aodh_client.Client(session=session)


def get_swift_client(novarc_creds):
    swift_creds = get_swift_creds(novarc_creds)
    return swiftclient.client.Connection(**swift_creds)


def get_swift_session_client(session):
    return swiftclient.client.Connection(session=session)


def get_designate_session_client(session, all_tenants=True,
                                 client_version=None):
    client_version = client_version or '2'
    if client_version == '1':
        client = designate_client.Client(
            version=client_version,
            session=session,
            all_tenants=all_tenants)
    else:
        client = designate_client.Client(
            version=client_version,
            session=session)
    return client


def get_glance_session_client(session):
    return glanceclient.Client('2', session=session)


# Glance Helpers
def download_image(image, image_glance_name=None):
    logging.info('Downloading ' + image)
    tmp_dir = tempfile.mkdtemp(dir='/tmp')
    if not image_glance_name:
        image_glance_name = image.split('/')[-1]
    local_file = os.path.join(tmp_dir, image_glance_name)
    urlretrieve(image, local_file)
    return local_file


def upload_image(gclient, ifile, image_name, visibility, disk_format,
                 container_format):
    logging.info('Uploading %s to glance ' % (image_name))
    image = gclient.images.create(
        name=image_name,
        visibility=visibility,
        disk_format=disk_format,
        container_format=container_format)
    with open(ifile, 'rb') as fimage:
        gclient.images.upload(image.id, fimage)


def get_images_list(gclient):
    return [image.name for image in gclient.images.list()]


# Keystone helpers
def tenant_create(kclient, tenants):
    current_tenants = [tenant.name for tenant in kclient.tenants.list()]
    for tenant in tenants:
        if tenant in current_tenants:
            logging.warning('Not creating tenant %s it already'
                            ' exists' % (tenant))
        else:
            logging.info('Creating tenant %s' % (tenant))
            kclient.tenants.create(tenant_name=tenant)


def project_create(kclient, projects, domain=None):
    domain_id = None
    for dom in kclient.domains.list():
        if dom.name == domain:
            domain_id = dom.id
    current_projects = []
    for project in kclient.projects.list():
        if not domain_id or project.domain_id == domain_id:
            current_projects.append(project.name)
    for project in projects:
        if project in current_projects:
            logging.warning('Not creating project %s it already'
                            ' exists' % (project))
        else:
            logging.info('Creating project %s' % (project))
            kclient.projects.create(project, domain_id)


def domain_create(kclient, domains):
    current_domains = [domain.name for domain in kclient.domains.list()]
    for dom in domains:
        if dom in current_domains:
            logging.warning('Not creating domain %s it already'
                            ' exists' % (dom))
        else:
            logging.info('Creating domain %s' % (dom))
            kclient.domains.create(dom)


def user_create_v2(kclient, users):
    current_users = [user.name for user in kclient.users.list()]
    for user in users:
        if user['username'] in current_users:
            logging.warning('Not creating user %s it already'
                            'exists' % (user['username']))
        else:
            logging.info('Creating user %s' % (user['username']))
            project_id = openstack_utils.get_project_id(
                kclient, user['project'])
            kclient.users.create(name=user['username'],
                                 password=user['password'],
                                 email=user['email'],
                                 tenant_id=project_id)


def user_create_v3(kclient, users):
    for user in users:
        project = user.get('project') or user.get('tenant')
        if kclient.users.find(username=user['username']):
            logging.warning('Not creating user %s it already'
                            'exists' % (user['username']))
        else:
            if user['scope'] == 'project':
                logging.info('Creating user %s' % (user['username']))
                project_id = openstack_utils.get_project_id(
                    kclient, project, api_version=3)
                kclient.users.create(name=user['username'],
                                     password=user['password'],
                                     email=user['email'],
                                     project_id=project_id)


def get_roles_for_user(kclient, user_id, tenant_id):
    roles = []
    ksuser_roles = kclient.roles.roles_for_user(user_id, tenant_id)
    for role in ksuser_roles:
        roles.append(role.id)
    return roles


def add_users_to_roles(kclient, users):
    for user_details in users:
        tenant_id = openstack_utils.get_project_id(
            kclient, user_details['project'])
        for role_name in user_details['roles']:
            role = kclient.roles.find(name=role_name)
            user = kclient.users.find(name=user_details['username'])
            users_roles = get_roles_for_user(kclient, user, tenant_id)
            if role.id in users_roles:
                logging.warning('Not adding role %s to %s it already has '
                                'it' % (user_details['username'], role_name))
            else:
                logging.info('Adding %s to role %s for tenant'
                             '%s' % (user_details['username'], role_name,
                                     tenant_id))
                kclient.roles.add_user_role(user_details['username'], role,
                                            tenant_id)


# Nova Helpers
def create_keypair(nova_client, keypair_name):
    if nova_client.keypairs.findall(name=keypair_name):
        _oldkey = nova_client.keypairs.find(name=keypair_name)
        logging.info('Deleting key %s' % (keypair_name))
        nova_client.keypairs.delete(_oldkey)
    logging.info('Creating key %s' % (keypair_name))
    new_key = nova_client.keypairs.create(name=keypair_name)
    return new_key.private_key


def boot_instance(nova_client, neutron_client, image_name,
                  flavor_name, key_name, boot_from_volume=False):
    image = nova_client.glance.find_image(image_name)
    flavor = nova_client.flavors.find(name=flavor_name)
    net = neutron_client.find_resource("network", "private")
    nics = [{'net-id': net.get('id')}]
    # Obviously time may not produce a unique name
    vm_name = time.strftime("%Y%m%d%H%M%S")
    vm_name = "mojo" + vm_name
    if boot_from_volume:
        bdmv2 = [{
                'boot_index': '0',
                'uuid': image.id,
                'source_type': 'image',
                'volume_size': flavor.disk,
                'destination_type': 'volume',
                'delete_on_termination': True,
                }]
        _image = None
    else:
        bdmv2 = None
        _image = image
    logging.info('Creating %s %s %s'
                 'instance %s' % (flavor_name, image_name, nics, vm_name))
    instance = nova_client.servers.create(name=vm_name,
                                          image=_image,
                                          flavor=flavor,
                                          key_name=key_name,
                                          nics=nics,
                                          block_device_mapping_v2=bdmv2,
                                          )
    logging.info('Issued boot')
    return instance


def wait_for_active(nova_client, vm_name, wait_time):
    logging.info('Waiting %is for %s to reach ACTIVE '
                 'state' % (wait_time, vm_name))
    # Pause here to avoid race
    time.sleep(10)
    for counter in range(wait_time):
        # trying getting the servers a few times; it seems that nova client
        # randomly generates 400 errors and just trying again can clear the
        # problem. See launchpad bug:
        # https://bugs.launchpad.net/python-novaclient/+bug/1772926
        count = 0
        while count < 10:
            try:
                # In pike+ servers.find throws a
                # novaclient.exceptions.NoUniqueMatch exception. Subsequent
                # calls work for some reason. Either way just use the first
                # element reduced by servers.findall
                instance = nova_client.servers.findall(name=vm_name)[0]
                break
            except (novaclient_exceptions.BadRequest, IndexError):
                count += 1
                time.sleep(1)
        else:
            raise Exception("Could get the instance name; nova client issue"
                            " probably ... :(")
        if instance.status == 'ACTIVE':
            logging.info('%s is ACTIVE' % (vm_name))
            return True
        elif instance.status not in ('BUILD', 'SHUTOFF'):
            logging.error('instance %s in unknown '
                          'state %s' % (instance.name, instance.status))
            return False
        time.sleep(1)
    logging.error('instance %s failed to reach '
                  'active state in %is' % (instance.name, wait_time))
    return False


def wait_for_cloudinit(nova_client, vm_name, bootstring, wait_time):
    logging.info('Waiting %is for cloudinit on %s to '
                 'complete' % (wait_time, vm_name))
    instance = nova_client.servers.find(name=vm_name)
    for counter in range(wait_time):
        instance = nova_client.servers.find(name=vm_name)
        console_log = instance.get_console_output()
        if bootstring in console_log:
            logging.info('Cloudinit for %s is complete' % (vm_name))
            return True
        time.sleep(1)
    logging.error('cloudinit for instance %s failed '
                  'to complete in %is' % (instance.name, wait_time))
    return False


def wait_for_boot(nova_client, vm_name, bootstring, active_wait,
                  cloudinit_wait):
    logging.info('Waiting for boot')
    if not wait_for_active(nova_client, vm_name, active_wait):
        raise Exception('Error initialising %s' % vm_name)
    if not wait_for_cloudinit(nova_client, vm_name, bootstring,
                              cloudinit_wait):
        raise Exception('Cloudinit error %s' % vm_name)


def wait_for_ping(ip, wait_time):
    logging.info('Waiting for ping to %s' % (ip))
    for counter in range(wait_time):
        if ping(ip):
            logging.info('Ping %s success' % (ip))
            return True
        time.sleep(10)
    logging.error('Ping failed for %s' % (ip))
    return False


def assign_floating_ip(nova_client, neutron_client, vm_name):
    ext_net_id = None
    instance_port = None
    for network in neutron_client.list_networks().get('networks'):
        if 'ext_net' in network.get('name'):
            ext_net_id = network.get('id')
    instance = nova_client.servers.find(name=vm_name)
    for port in neutron_client.list_ports().get('ports'):
        if instance.id in port.get('device_id'):
            instance_port = port
    floating_ip = neutron_client.create_floatingip({'floatingip':
                                                    {'floating_network_id':
                                                     ext_net_id,
                                                     'port_id':
                                                     instance_port.get('id')}})
    ip = floating_ip.get('floatingip').get('floating_ip_address')
    logging.info('Assigning floating IP %s to %s' % (ip, vm_name))
    return ip


def add_secgroup_rules(nova_client):
    secgroup = nova_client.security_groups.find(name="default")
    # Using presence of a 22 rule to indicate whether secgroup rules
    # have been added
    port_rules = [rule['to_port'] for rule in secgroup.rules]
    if 22 in port_rules:
        logging.warn('Security group rules for ssh already added')
    else:
        logging.info('Adding ssh security group rule')
        nova_client.security_group_rules.create(secgroup.id,
                                                ip_protocol="tcp",
                                                from_port=22,
                                                to_port=22)
    if -1 in port_rules:
        logging.warn('Security group rules for ping already added')
    else:
        logging.info('Adding ping security group rule')
        nova_client.security_group_rules.create(secgroup.id,
                                                ip_protocol="icmp",
                                                from_port=-1,
                                                to_port=-1)


def ping(ip):
    # Use the system ping command with count of 1 and wait time of 1.
    ret = subprocess.call(['ping', '-c', '1', '-W', '1', ip],
                          stdout=open('/dev/null', 'w'),
                          stderr=open('/dev/null', 'w'))
    return ret == 0


def ssh_test(username, ip, vm_name, password=None, privkey=None):
    logging.info('Attempting to ssh to %s(%s)' % (vm_name, ip))
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if privkey:
        key = paramiko.RSAKey.from_private_key(StringIO(privkey))
        ssh.connect(ip, username=username, password='', pkey=key)
    else:
        ssh.connect(ip, username=username, password=password)
    stdin, stdout, stderr = ssh.exec_command('uname -n')
    return_string = stdout.readlines()[0].strip()
    ssh.close()
    if return_string == vm_name:
        logging.info('SSH to %s(%s) succesfull' % (vm_name, ip))
        return True
    else:
        logging.info('SSH to %s(%s) failed (%s != %s)' % (vm_name, ip,
                                                          return_string,
                                                          vm_name))
        return False


def boot_and_test(nova_client, neutron_client, image_name, flavor_name,
                  number, privkey, active_wait=600, cloudinit_wait=600,
                  ping_wait=600, boot_from_volume=False):
    image_file = mojo_utils.get_mojo_file('images.yaml')
    image_config = generic_utils.get_yaml_config(image_file)
    for counter in range(int(number)):
        logging.info("Launching instance")
        instance = boot_instance(nova_client,
                                 neutron_client,
                                 image_name=image_name,
                                 flavor_name=flavor_name,
                                 key_name='mojo',
                                 boot_from_volume=boot_from_volume,
                                 )
        logging.info("Launched {}".format(instance))
        wait_for_boot(nova_client, instance.name,
                      image_config[image_name]['bootstring'], active_wait,
                      cloudinit_wait)
        ip = assign_floating_ip(nova_client, neutron_client, instance.name)
        wait_for_ping(ip, ping_wait)
        if not wait_for_ping(ip, ping_wait):
            raise Exception('Ping of %s failed' % (ip))
        ssh_test_args = {
            'username': image_config[image_name]['username'],
            'ip': ip,
            'vm_name': instance.name,
        }
        if image_config[image_name]['auth_type'] == 'password':
            ssh_test_args['password'] = image_config[image_name]['password']
        elif image_config[image_name]['auth_type'] == 'privkey':
            ssh_test_args['privkey'] = privkey
        if not ssh_test(**ssh_test_args):
            raise Exception('SSH failed to instance at %s' % (ip))


def check_guest_connectivity(nova_client, ping_wait=600):
    for guest in nova_client.servers.list():
        fip = nova_client.floating_ips.find(instance_id=guest.id).ip
        if not wait_for_ping(fip, ping_wait):
            raise Exception('Ping of %s failed' % (fip))


# Hacluster helper

def get_crm_leader(service, resource=None):
    if not resource:
        resource = 'res_.*_vip'
    leader = set()
    for unit in mojo_utils.get_juju_units(service):
        crm_out = juju_utils.remote_run(unit, 'sudo crm status')
        for line in crm_out.splitlines():
            line = line.lstrip()
            if re.match(resource, line):
                leader.add(line.split()[-1])
    if len(leader) != 1:
        raise Exception('Unexpected leader count: ' + str(len(leader)))
    return leader.pop().split('-')[-1]


def delete_crm_leader(service, resource=None, method='juju'):
    mach_no = get_crm_leader(service, resource)
    unit = mojo_utils.convert_machineno_to_unit(mach_no)
    mojo_utils.delete_unit(unit, method=method)


# OpenStack Version helpers
def next_release(release):
    old_index = list(OPENSTACK_CODENAMES.values()).index(release)
    new_index = old_index + 1
    return list(OPENSTACK_CODENAMES.items())[new_index]


def get_lowest_os_version(current_versions):
    lowest_version = 'zebra'
    for svc in current_versions.keys():
        if current_versions[svc] < lowest_version:
            lowest_version = current_versions[svc]
    return lowest_version


def update_network_dns(neutron_client, network, domain_name):
    msg = {
        'network': {
            'dns_domain': domain_name,
        }
    }
    logging.info('Updating dns_domain for network {}'.format(network))
    neutron_client.update_network(network, msg)


def get_designate_server_id(client, server_name):
    server_id = None
    for server in client.servers.list():
        if server.name == server_name:
            server_id = server.id
            break
    return server_id


def get_designate_domain_id(client, domain_name):
    domain_id = None
    for domain in client.domains.list():
        if domain.name == domain_name:
            domain_id = domain.id
            break
    return domain_id


def get_designate_record_id(client, domain_id, record_name):
    record_id = None
    for record in client.records.list(domain_id):
        if record.name == record_name:
            record_id = record.id
            break
    return record_id


def get_designate_domain_object_v1(designate_client, domain_name):
    """Get the one and only domain matching the given domain_name, if none are
    found or multiple are found then raise an AssertionError. To access a list
    matching the domain name use get_designate_domain_objects.

    @param designate_client: designateclient.v1.Client Client to query
                                                       designate
    @param domain_name: str Name of domain to lookup
    @returns designateclient.v1.domains.Domain
    @raises AssertionError: if domain_name not found or multiple domains with
                            the same name.
    """
    dns_zone_id = get_designate_domain_objects_v1(designate_client,
                                                  domain_name=domain_name)
    assert len(dns_zone_id) == 1, "Found {} domains for {}".format(
        len(dns_zone_id),
        domain_name)
    return dns_zone_id[0]


def get_designate_domain_object_v2(designate_client, domain_name):
    """Get the one and only domain matching the given domain_name, if none are
    found or multiple are found then raise an AssertionError. To access a list
    matching the domain name use get_designate_domain_objects.

    @param designate_client: designateclient.v1.Client Client to query
                                                       designate
    @param domain_name: str Name of domain to lookup
    @returns designateclient.v1.domains.Domain
    @raises AssertionError: if domain_name not found or multiple domains with
                            the same name.
    """
    dns_zone_id = get_designate_zone_objects_v2(designate_client,
                                                domain_name=domain_name)
    msg = "Found {} domains for {}".format(
        len(dns_zone_id),
        domain_name)
    assert len(dns_zone_id) == 1, msg
    return dns_zone_id[0]


def get_designate_domain_objects_v1(designate_client, domain_name=None,
                                    domain_id=None):
    """Get all domains matching a given domain_name or domain_id

    @param designate_client: designateclient.v1.Client Client to query
                                                       designate
    @param domain_name: str Name of domain to lookup
    @param domain_id: str UUID of domain to lookup
    @returns [] List of designateclient.v1.domains.Domain objects matching
                domain_name or domain_id
    """
    all_domains = designate_client.domains.list()
    a = [d for d in all_domains if d.name == domain_name or d.id == domain_id]
    return a


def get_designate_zone_objects_v2(designate_client, domain_name=None,
                                  domain_id=None):
    """Get all domains matching a given domain_name or domain_id

    @param designate_client: designateclient.v1.Client Client to query
                                                       designate
    @param domain_name: str Name of domain to lookup
    @param domain_id: str UUID of domain to lookup
    @returns [] List of designateclient.v1.domains.Domain objects matching
                domain_name or domain_id
    """
    all_zones = designate_client.zones.list()
    a = [z for z in all_zones
         if z['name'] == domain_name or z['id'] == domain_id]
    return a


def get_designate_dns_records_v1(designate_client, domain_name, ip):
    """Look for records in designate that match the given ip

    @param designate_client: designateclient.v1.Client Client to query
                                                       designate
    @param domain_name: str Name of domain to lookup
    @returns [] List of designateclient.v1.records.Record objects with
                a matching IP address
    """
    dns_zone = get_designate_domain_object_v1(designate_client, domain_name)
    domain = designate_client.domains.get(dns_zone.id)
    return [r for r in designate_client.records.list(domain) if r.data == ip]


def get_designate_dns_records_v2(designate_client, domain_name, ip):
    """Look for records in designate that match the given ip

    @param designate_client: designateclient.v1.Client Client to query
                                                       designate
    @param domain_name: str Name of domain to lookup
    @returns [] List of designateclient.v1.records.Record objects with
                a matching IP address
    """
    dns_zone = get_designate_domain_object_v2(designate_client, domain_name)
    return [r for r in designate_client.recordsets.list(dns_zone['id'])
            if r['records'] == ip]


def get_designate_zone(designate_client, zone_name):
    zone = None
    zones = [z for z in designate_client.zones.list()
             if z['name'] == zone_name]
    assert len(zones) <= 1, "Multiple matching zones found"
    if zones:
        zone = zones[0]
    return zone


def create_designate_zone(designate_client, domain_name, email):
    return designate_client.zones.create(
        name=domain_name,
        email=email)


def create_designate_dns_domain(designate_client, domain_name, email,
                                recreate=True):
    """Create the given domain in designate

    @param designate_client: designateclient.v1.Client Client to query
                                                       designate
    @param domain_name: str Name of domain to lookup
    @param email: str Email address to associate with domain
    @param recreate: boolean Whether to delete any matching domains first.
    """
    if recreate:
        delete_designate_dns_domain(designate_client, domain_name)
        for i in range(1, 10):
            try:
                dom_obj = create_designate_zone(
                    designate_client,
                    domain_name,
                    email)
            except des_exceptions.Conflict:
                print("Waiting for delete {}/10".format(i))
                time.sleep(10)
            else:
                break
        else:
            raise des_exceptions.Conflict
    else:
        domain = des_domains.Domain(name=domain_name, email=email)
        dom_obj = designate_client.domains.create(domain)
    return dom_obj


def create_designate_dns_record(designate_client, domain_id, name, rtype,
                                data):
    """Create the given record in designmate

    @param designate_client: designateclient.v1.Client Client to query
                                                       designate
    @param domain_id: str UUID of domain to create record in
    @param name: str DNS fqdn entry to be created
    @param rtype: str record type eg A, CNAME etc
    @param data: str data to be associated with record
    @returns designateclient.v1.records.Record
    """
    record = des_records.Record(name=name, type=rtype, data=data)
    return designate_client.records.create(domain_id, record)


def delete_designate_dns_domain(designate_client, domain_name):
    """Delete the domains matching the given domain_name

    @param designate_client: designateclient.v1.Client Client to query
                                                       designate
    @param domain_name: str Name of domain to lookup
    @raises AssertionError: if domain deletion fails
    """
    old_doms = get_designate_zone_objects_v2(designate_client, domain_name)
    for old_dom in old_doms:
        logging.info("Deleting old domain {}".format(old_dom['id']))
        designate_client.zones.delete(old_dom['id'])


def check_dns_record_exists(dns_server_ip, query_name, expected_ip,
                            retry_count=1):
    """Lookup a DNS record against the given dns server address

    @param dns_server_ip: str IP address to run query against
    @param query_name: str Record to lookup
    @param expected_ip: str IP address expected to be associated with record.
    @param retry_count: int Number of times to retry query. Useful if waiting
                            for record to propagate.
    @raises AssertionError: if record is not found or expected_ip is set and
                            does not match the IP associated with the record
    """
    my_resolver = dns.resolver.Resolver()
    my_resolver.nameservers = [dns_server_ip]
    for i in range(1, retry_count + 1):
        try:
            answers = my_resolver.query(query_name)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
            logging.info(
                'Attempt {}/{} to lookup {}@{} failed. Sleeping before '
                'retrying'.format(i, retry_count, query_name,
                                  dns_server_ip))
            time.sleep(15)
        else:
            break
    else:
        raise dns.resolver.NXDOMAIN
    assert len(answers) > 0
    if expected_ip:
        for rdata in answers:
            logging.info("Checking address returned by {} is correct".format(
                dns_server_ip))
            assert str(rdata) == expected_ip


def check_dns_entry(des_client, ip, domain, record_name, juju_status=None,
                    designate_api='2'):
    """Check that record for ip address is in designate and in bind if bind
       server is available.

    @param ip: str IP address to lookup
    @param domain: str domain to look for record in
    @param record_name: str record name
    @param juju_status: dict Current juju status
    """
    if designate_api == '1':
        check_dns_entry_in_designate_v1(des_client, ip, domain,
                                        record_name=record_name)
    else:
        check_dns_entry_in_designate_v2(des_client, [ip], domain,
                                        record_name=record_name)
    check_dns_entry_in_bind(ip, record_name)


def check_dns_entry_in_designate_v1(des_client, ip, domain, record_name=None):
    """Look for records in designate that match the given ip in the given
       domain

    @param designate_client: designateclient.v1.Client Client to query
                                                       designate
    @param ip: str IP address to lookup in designate
    @param domain: str Name of domain to lookup
    @param record_name: str Retrieved record should have this name
    @raises AssertionError: if no record is found or record_name is set and
                            does not match the name associated with the record
    """
    records = get_designate_dns_records_v1(des_client, domain, ip)
    assert records, "Record not found for {} in designate".format(ip)
    logging.info('Found record in {} for {} in designate'.format(domain, ip))

    if record_name:
        recs = [r for r in records if r.name == record_name]
        assert recs, "No DNS entry name matches expected name {}".format(
            record_name)
        logging.info('Found record in {} for {} in designate'.format(
            domain,
            record_name))


def check_dns_entry_in_designate_v2(des_client, ip, domain, record_name=None):
    """Look for records in designate that match the given ip in the given
       domain

    @param designate_client: designateclient.v1.Client Client to query
                                                       designate
    @param ip: str IP address to lookup in designate
    @param domain: str Name of domain to lookup
    @param record_name: str Retrieved record should have this name
    @raises AssertionError: if no record is found or record_name is set and
                            does not match the name associated with the record
    """
    records = get_designate_dns_records_v2(des_client, domain, ip)
    assert records, "Record not found for {} in designate".format(ip)
    logging.info('Found record in {} for {} in designate'.format(domain, ip))

    if record_name:
        recs = [r for r in records if r['name'] == record_name]
        assert recs, "No DNS entry name matches expected name {}".format(
            record_name)
        logging.info('Found record in {} for {} in designate'.format(
            domain,
            record_name))


def check_dns_entry_in_bind(ip, record_name, juju_status=None):
    """Check that record for ip address in bind if a bind
       server is available.

    @param ip: str IP address to lookup
    @param record_name: str record name
    @param juju_status: dict Current juju status
    """
    bind_units = mojo_utils.get_juju_units('designate-bind')

    for unit in bind_units:
        addr = mojo_utils.get_juju_unit_ip(unit)
        logging.info("Checking {} is {} against {} ({})".format(
            record_name,
            ip,
            unit,
            addr))
        check_dns_record_exists(addr, record_name, ip, retry_count=6)


def create_or_return_zone(client, name, email):
    try:
        zone = client.zones.create(
            name=name,
            email=email)
    except designateclient.exceptions.Conflict:
        logging.info('{} zone already exists.'.format(name))
        zones = [z for z in client.zones.list() if z['name'] == name]
        assert len(zones) == 1, "Wrong number of zones found {}".format(zones)
        zone = zones[0]
    return zone


def create_or_return_recordset(client, zone_id, sub_domain, record_type, data):
    try:
        rs = client.recordsets.create(
            zone_id,
            sub_domain,
            record_type,
            data)
    except designateclient.exceptions.Conflict:
        logging.info('{} record already exists.'.format(data))
        for r in client.recordsets.list(zone_id):
            if r['name'].split('.')[0] == sub_domain:
                rs = r
    return rs


# Aodh helpers
def get_alarm(aclient, alarm_name):
    for alarm in aclient.alarm.list():
        if alarm['name'] == alarm_name:
            return alarm
    return None


def delete_alarm(aclient, alarm_name, cache_wait=False):
    alarm = get_alarm(aclient, alarm_name)
    if alarm:
        aclient.alarm.delete(alarm['alarm_id'])
    # AODH has an alarm cache (see event_alarm_cache_ttl in aodh.conf). This
    # means deleted alarms can persist and fire. The default is 60s and is
    # currently not configrable via the charm so 61s is a safe assumption.
    if cache_wait:
        time.sleep(61)


def get_alarm_state(aclient, alarm_id):
    alarm = aclient.alarm.get(alarm_id)
    return alarm['state']
