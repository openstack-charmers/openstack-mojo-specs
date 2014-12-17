Using mojo:

Packages:
sudo apt-get install bzr juju juju-deployer python-cinderclient python-jinja2\
     lxc python-novaclient python-neutronclient python-keystoneclient\
     python-glanceclient python-oslotest python-boto pep8\
     python-testresources python-flake8 python-tempest

Branches:
( bzr branch lp:codetree; cd codetree; sudo python setup.py install )
( bzr branch lp:mojo; cd mojo; sudo python setup.py install )

Hack:
Currently mojo uses privileged lxc containers which require root access. Until
this is fixed root needs to know credentials for accessing lp. eg append the
below snippet to ssh config (/root/.ssh/config):

Host bazaar.launchpad.net
    User <username>
    IdentityFile /home/ubuntu/.ssh/id_rsa


Running Mojo:
juju bootstrap
sudo mojo project-new --series trusty mojo-openstack-specs
sudo mojo workspace-new --project mojo-openstack-specs --series trusty --stage next-deploy/devel lp:~ost-maintainers/openstack-mojo-specs/mojo-openstack-specs run1
sudo mojo run --project mojo-openstack-specs --series trusty --stage next-deploy/devel lp:~ost-maintainers/openstack-mojo-specs/mojo-openstack-specs run1
