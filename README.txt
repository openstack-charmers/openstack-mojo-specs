Using mojo:

Install mojo (Stolen from https://launchpad.net/mojo)
sudo add-apt-repository ppa:mojo-maintainers/ppa
sudo apt-get update
sudo apt-get install mojo

sudo mojo project-new --series trusty mojo-openstack-specs
sudo adduser ubuntu mojo
sudo chmod 755 /var/lib/lxc/mojo-openstack-specs.trusty && sudo chmod 755 /var/lib/lxc

mojo workspace-new --project mojo-openstack-specs --series trusty --stage full_stack/next_deploy lp:~ost-maintainers/openstack-mojo-specs/mojo-openstack-specs run1
