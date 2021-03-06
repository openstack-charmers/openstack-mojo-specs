#!/usr/bin/python

import swiftclient
import glanceclient
from keystoneclient.v2_0 import client as keystoneclient
import mojo_utils
from novaclient.v1_1 import client as novaclient
from neutronclient.v2_0 import client as neutronclient
import logging
import re
import sys
import tempfile
import urllib
import os
import time
import subprocess
import paramiko
import StringIO


# Openstack Client helpers
def get_nova_creds(cloud_creds):
    auth = {
        'username': cloud_creds['OS_USERNAME'],
        'api_key': cloud_creds['OS_PASSWORD'],
        'auth_url': cloud_creds['OS_AUTH_URL'],
        'project_id': cloud_creds['OS_TENANT_NAME'],
        'region_name': cloud_creds['OS_REGION_NAME'],
    }
    return auth


def get_ks_creds(cloud_creds):
    auth = {
        'username': cloud_creds['OS_USERNAME'],
        'password': cloud_creds['OS_PASSWORD'],
        'auth_url': cloud_creds['OS_AUTH_URL'],
        'tenant_name': cloud_creds['OS_TENANT_NAME'],
        'region_name': cloud_creds['OS_REGION_NAME'],
    }
    return auth


def get_swift_creds(cloud_creds):
    auth = {
        'user': cloud_creds['OS_USERNAME'],
        'key': cloud_creds['OS_PASSWORD'],
        'authurl': cloud_creds['OS_AUTH_URL'],
        'tenant_name': cloud_creds['OS_TENANT_NAME'],
        'auth_version': '2.0',
    }
    return auth



def get_nova_client(novarc_creds):
    nova_creds = get_nova_creds(novarc_creds)
    return novaclient.Client(**nova_creds)


def get_neutron_client(novarc_creds):
    neutron_creds = get_ks_creds(novarc_creds)
    return neutronclient.Client(**neutron_creds)


def get_keystone_client(novarc_creds):
    keystone_creds = get_ks_creds(novarc_creds)
    keystone_creds['insecure'] = True
    return keystoneclient.Client(**keystone_creds)


def get_swift_client(novarc_creds, insecure=True):
    swift_creds = get_swift_creds(novarc_creds)
    swift_creds['insecure'] = insecure
    return swiftclient.client.Connection(**swift_creds)


def get_glance_client(novarc_creds):
    kc = get_keystone_client(novarc_creds)
    glance_endpoint = kc.service_catalog.url_for(service_type='image',
                                                 endpoint_type='publicURL')
    return glanceclient.Client('1', glance_endpoint, token=kc.auth_token)


# Glance Helpers
def download_image(image, image_glance_name=None):
    logging.info('Downloading ' + image)
    tmp_dir = tempfile.mkdtemp(dir='/tmp')
    if not image_glance_name:
        image_glance_name = image.split('/')[-1]
    local_file = os.path.join(tmp_dir, image_glance_name)
    urllib.urlretrieve(image, local_file)
    return local_file


def upload_image(gclient, ifile, image_name, public, disk_format,
                 container_format):
    logging.info('Uploading %s to glance ' % (image_name))
    with open(ifile) as fimage:
        gclient.images.create(
            name=image_name,
            is_public=public,
            disk_format=disk_format,
            container_format=container_format,
            data=fimage)


def get_images_list(gclient):
    return [image.name for image in gclient.images.list()]


# Keystone helpers
def tenant_create(kclient, tenants):
    current_tenants = [tenant.name for tenant in kclient.tenants.list()]
    for tenant in tenants:
        if tenant in current_tenants:
            logging.warning('Not creating tenant %s it already'
                            'exists' % (tenant))
        else:
            logging.info('Creating tenant %s' % (tenant))
            kclient.tenants.create(tenant_name=tenant)


def user_create(kclient, users):
    current_users = [user.name for user in kclient.users.list()]
    for user in users:
        if user['username'] in current_users:
            logging.warning('Not creating user %s it already'
                            'exists' % (user['username']))
        else:
            logging.info('Creating user %s' % (user['username']))
            tenant_id = get_tenant_id(kclient, user['tenant'])
            kclient.users.create(name=user['username'],
                                 password=user['password'],
                                 email=user['email'],
                                 tenant_id=tenant_id)


def get_roles_for_user(kclient, user_id, tenant_id):
    roles = []
    ksuser_roles = kclient.roles.roles_for_user(user_id, tenant_id)
    for role in ksuser_roles:
        roles.append(role.id)
    return roles


def add_users_to_roles(kclient, users):
    for user_details in users:
        tenant_id = get_tenant_id(kclient, user_details['tenant'])
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


def get_tenant_id(ks_client, tenant_name):
    for t in ks_client.tenants.list():
        if t._info['name'] == tenant_name:
            return t._info['id']
    return None


# Neutron Helpers
def get_gateway_uuids():
    gateway_config = mojo_utils.get_juju_status('neutron-gateway')
    uuids = []
    for machine in gateway_config['machines']:
        uuids.append(gateway_config['machines'][machine]['instance-id'])
    return uuids


def get_net_uuid(neutron_client, net_name):
    network = neutron_client.list_networks(name=net_name)['networks'][0]
    return network['id']


def configure_gateway_ext_port(novaclient):
    uuids = get_gateway_uuids()
    for uuid in uuids:
        server = novaclient.servers.get(uuid)
        mac_addrs = [a.mac_addr for a in server.interface_list()]
        if len(mac_addrs) < 2:
            logging.info('Adding additional port to Neutron Gateway')
            server.interface_attach(port_id=None, net_id=None, fixed_ip=None)
        else:
            logging.warning('Neutron Gateway already has additional port')
    if uuids:
        logging.info('Seting Neutron Gateway external port to eth1')
        mojo_utils.juju_set('neutron-gateway', 'ext-port=eth1')


def create_tenant_network(neutron_client, tenant_id, net_name='private',
                          shared=False, network_type='gre'):
    networks = neutron_client.list_networks(name=net_name)
    if len(networks['networks']) == 0:
        logging.info('Creating network: %s',
                     net_name)
        network_msg = {
            'network': {
                'name': net_name,
                'shared': shared,
                'tenant_id': tenant_id,
            }
        }
        if network_type == 'vxlan':
            network_msg['network']['provider:segmentation_id'] = 1233
            network_msg['network']['provider:network_type'] = network_type
        network = neutron_client.create_network(network_msg)['network']
    else:
        logging.warning('Network %s already exists.', net_name)
        network = networks['networks'][0]
    return network


def create_external_network(neutron_client, tenant_id, net_name='ext_net',
                            network_type='gre'):
    networks = neutron_client.list_networks(name=net_name)
    if len(networks['networks']) == 0:
        logging.info('Configuring external bridge')
        network_msg = {
            'name': net_name,
            'router:external': True,
            'tenant_id': tenant_id,
        }
        if network_type == 'vxlan':
            network_msg['provider:segmentation_id'] = 1234
            network_msg['provider:network_type'] = network_type

        logging.info('Creating new external network definition: %s',
                     net_name)
        network = neutron_client.create_network(
            {'network': network_msg})['network']
        logging.info('New external network created: %s', network['id'])
    else:
        logging.warning('Network %s already exists.', net_name)
        network = networks['networks'][0]
    return network


def create_tenant_subnet(neutron_client, tenant_id, network, cidr, dhcp=True,
                         subnet_name='private_subnet'):
    # Create subnet
    subnets = neutron_client.list_subnets(name=subnet_name)
    if len(subnets['subnets']) == 0:
        logging.info('Creating subnet')
        subnet_msg = {
            'subnet': {
                'name': subnet_name,
                'network_id': network['id'],
                'enable_dhcp': dhcp,
                'cidr': cidr,
                'ip_version': 4,
                'tenant_id': tenant_id
            }
        }
        subnet = neutron_client.create_subnet(subnet_msg)['subnet']
    else:
        logging.warning('Subnet %s already exists.', subnet_name)
        subnet = subnets['subnets'][0]
    return subnet


def create_external_subnet(neutron_client, tenant_id, network,
                           default_gateway=None, cidr=None,
                           start_floating_ip=None, end_floating_ip=None,
                           subnet_name='ext_net_subnet'):
    subnets = neutron_client.list_subnets(name=subnet_name)
    if len(subnets['subnets']) == 0:
        subnet_msg = {
            'name': subnet_name,
            'network_id': network['id'],
            'enable_dhcp': False,
            'ip_version': 4,
            'tenant_id': tenant_id
        }

        if default_gateway:
            subnet_msg['gateway_ip'] = default_gateway
        if cidr:
            subnet_msg['cidr'] = cidr
        if (start_floating_ip and end_floating_ip):
            allocation_pool = {
                'start': start_floating_ip,
                'end': end_floating_ip,
            }
            subnet_msg['allocation_pools'] = [allocation_pool]

        logging.info('Creating new subnet')
        subnet = neutron_client.create_subnet({'subnet': subnet_msg})['subnet']
        logging.info('New subnet created: %s', subnet['id'])
    else:
        logging.warning('Subnet %s already exists.', subnet_name)
        subnet = subnets['subnets'][0]
    return subnet


def update_subnet_dns(neutron_client, subnet, dns_servers):
    msg = {
        'subnet': {
            'dns_nameservers': dns_servers.split(',')
        }
    }
    logging.info('Updating dns_nameservers (%s) for subnet',
                 dns_servers)
    neutron_client.update_subnet(subnet['id'], msg)


def create_provider_router(neutron_client, tenant_id):
    routers = neutron_client.list_routers(name='provider-router')
    if len(routers['routers']) == 0:
        logging.info('Creating provider router for external network access')
        router_info = {
            'router': {
                'name': 'provider-router',
                'tenant_id': tenant_id
            }
        }
        router = neutron_client.create_router(router_info)['router']
        logging.info('New router created: %s', (router['id']))
    else:
        logging.warning('Router provider-router already exists.')
        router = routers['routers'][0]
    return router


def plug_extnet_into_router(neutron_client, router, network):
    ports = neutron_client.list_ports(device_owner='network:router_gateway',
                                      network_id=network['id'])
    if len(ports['ports']) == 0:
        logging.info('Plugging router into ext_net')
        router = neutron_client.add_gateway_router(
            router=router['id'],
            body={'network_id': network['id']})
        logging.info('Router connected')
    else:
        logging.warning('Router already connected')


def plug_subnet_into_router(neutron_client, router, network, subnet):
    routers = neutron_client.list_routers(name=router)
    if len(routers['routers']) == 0:
        logging.error('Unable to locate provider router %s', router)
        sys.exit(1)
    else:
        # Check to see if subnet already plugged into router
        ports = neutron_client.list_ports(
            device_owner='network:router_interface',
            network_id=network['id'])
        if len(ports['ports']) == 0:
            logging.info('Adding interface from subnet to %s' % (router))
            router = routers['routers'][0]
            neutron_client.add_interface_router(router['id'],
                                                {'subnet_id': subnet['id']})
        else:
            logging.warning('Router already connected to subnet')


# Nova Helpers
def create_keypair(nova_client, keypair_name):
    if nova_client.keypairs.findall(name=keypair_name):
        _oldkey = nova_client.keypairs.find(name=keypair_name)
        logging.info('Deleting key %s' % (keypair_name))
        nova_client.keypairs.delete(_oldkey)
    logging.info('Creating key %s' % (keypair_name))
    new_key = nova_client.keypairs.create(name=keypair_name)
    return new_key.private_key


def boot_instance(nova_client, image_name, flavor_name, key_name):
    image = nova_client.images.find(name=image_name)
    flavor = nova_client.flavors.find(name=flavor_name)
    net = nova_client.networks.find(label="private")
    nics = [{'net-id': net.id}]
    # Obviously time may not produce a unique name
    vm_name = time.strftime("%Y%m%d%H%M%S")
    logging.info('Creating %s %s '
                 'instance %s' % (flavor_name, image_name, vm_name))
    instance = nova_client.servers.create(name=vm_name,
                                          image=image,
                                          flavor=flavor,
                                          key_name=key_name,
                                          nics=nics)
    return instance


def wait_for_active(nova_client, vm_name, wait_time):
    logging.info('Waiting %is for %s to reach ACTIVE '
                 'state' % (wait_time, vm_name))
    for counter in range(wait_time):
        instance = nova_client.servers.find(name=vm_name)
        if instance.status == 'ACTIVE':
            logging.info('%s is ACTIVE' % (vm_name))
            return True
        elif instance.status != 'BUILD':
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
        time.sleep(1)
    logging.error('Ping failed for %s' % (ip))
    return False


def assign_floating_ip(nova_client, vm_name):
    floating_ip = nova_client.floating_ips.create()
    logging.info('Assigning floating IP %s to %s' % (floating_ip.ip, vm_name))
    instance = nova_client.servers.find(name=vm_name)
    instance.add_floating_ip(floating_ip)
    return floating_ip.ip


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
        key = paramiko.RSAKey.from_private_key(StringIO.StringIO(privkey))
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
        logging.info('SSH to %s(%s) failed' % (vm_name, ip))
        return False


def boot_and_test(nova_client, image_name, flavor_name, number, privkey,
                  active_wait=600, cloudinit_wait=600, ping_wait=600):
    image_config = mojo_utils.get_mojo_config('images.yaml')
    for counter in range(number):
        instance = boot_instance(nova_client,
                                 image_name=image_name,
                                 flavor_name=flavor_name,
                                 key_name='mojo')
        wait_for_boot(nova_client, instance.name,
                      image_config[image_name]['bootstring'], active_wait,
                      cloudinit_wait)
        ip = assign_floating_ip(nova_client, instance.name)
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
            raise Exception('SSH failed' % (ip))


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
    for unit in mojo_utils.get_juju_units(service=service):
        crm_out = mojo_utils.remote_run(unit, 'sudo crm status')[0]
        for line in crm_out.splitlines():
            line = line.lstrip()
            if re.match(resource, line):
                  leader.add(line.split()[-1])
    if len(leader) != 1:
        raise Exception('Unexpected leader count: ' + str(len(leader)))
    return leader.pop().split('-')[-1]


def delete_crm_leader(service, resource=None):
    mach_no = get_crm_leader(service, resource)
    unit = mojo_utils.convert_machineno_to_unit(mach_no)
    mojo_utils.delete_unit(unit)
