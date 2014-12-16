Using mojo:

Packages:
sudo apt-get install bzr juju juju-deployer python-cinderclient python-jinja2\
     lxc python-novaclient python-neutronclient python-keystoneclient\
     python-glanceclient python-oslotest python-boto pep8\
     python-testresources python-flake8 python-tempest

Branches:
( bzr branch lp:codetree; cd codetree; sudo python setup.py install )
( bzr branch lp:mojo; cd mojo; sudo python setup.py install )

Running Mojo:
sudo mojo project-new --series trusty mojo-openstack-specs

