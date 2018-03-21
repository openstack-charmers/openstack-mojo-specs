General
=======

These are the Mojo specs for running deployments of Openstack. For more
information on installing and running Mojo see lp:mojo

Directory Layouts
=================

Top Level
---------

This branch contains the following top level assets:

* *specs* directory contains the specs themselves.
* *SPEC\_SUMMARY.txt* contains descriptions of each spec
* *Makefile* has targets for checking lint and generating SPEC\_SUMMARY.txt
* *helper* directory contains scripts and libraries used by the specs

spec directory
--------------

The specs fall into the following catagories:

* *dev*: Specs which are still under development (these are not lint checked)
* *full\_stack*: These perform a full openstack deployment
* *bugs*: Specs that reproduce a bug. These are useful for verifying a bugs
  existence and then once the fix has landed they can be used to verify a
  regression has not occured.
* *features*: These do a minimal deployment to demonstrate a new feature.
* *object\_storage*: Specs for deploying a standalone object storage environment

Tip directory
-------------

The tip directory should be used to differentiate between Openstack versions.

Example
-------

*specs/full_stack/charmhelper_upgrade/juno/*

This spec is used to do a deployment of a full Juno Openstack environment and
to test an upgrade of charmhelpers

helper directory
----------------

The helper directory contains the following:

* *bundles*: Juju deployer bundles
* *collect*: Mojo collect and repo files, used to collect branches prior to
           running Juju Deployer
* *scripts*: Scripts for running lint checks etc
* *setup*: Manipulate the overcloud or provider
* *template*: An example spec
* *tests*: Tests to run against the deployment
* *utils*: Core set of utilities used by tests and setup

Spec Bulding Blocks
===================

Phase 1: Collection
-------------------

Directives: collect and repo

These specs collect the charm branches as a seperate step from deploying the
charms. Although Juju deployer can do the branch collection, having this done
as a seperate phase has a few advantages. It allows for the branches to be
manipulated prior to deployment, the charmhelper upgrade spec does exactly this
to check that a charmhelper sync will not break a deployment. It also allows
for an alternative branch location for a given charm to be clearly specified,
this is particulalry useful when an unmerged branch needs testing.

Phase 2: Deployment
-------------------

Directives: deploy

Mojo uses juju deployer to do the charm deployment. When specifying the target
to use in the bundle the ${MOJO\_SERIES} environment variable should be used in
place of the Ubuntu release version. This allows the same spec to be used for
deployments on different Ubuntu release.

deploy config=haphase1.yaml delay=0 target=${MOJO\_SERIES}-juno

Phase 3: Cloud Setup
--------------------

Directives: script

There are a number of helper scripts used to setup the cloud once it has been
deployed. In general they consist of the script to do the setup and a YAML file
of options.

* *image\_setup.py*: This script downloads guest images and uploads them to
                  Glance. *images.yaml* lists the images to be downloaded and
		  information about those images.
* *keystone\_setup.py*: Setup keystone users and roles. *keystone_users.yaml*
                     lists the users to be created and what roles they should
		     be given
* *network\_setup.py*: This sets up the SDN on the cloud. *network.yaml* describes
                    the SDN topology

Phase 4: Test
-------------

Directives: verify

There are a number of tests to choose from, some are specific to particular
bugs or features. However, the main tests used to verify the cloud are:

* *simple\_os\_checks.py*: This script creates guests on the cloud, associates
                           floating ips and then uses ssh to connect to the
			   cloud and verifies its hostname. This ensure that
			   the guest got a network and metadata on boot.
* *test\_obj\_store.py*: This script fires two streams of objects and the
                         object store and retireves them
* *tempest.py*: This doesn't actually exist in any real sense but will do rsn!

Phase 5: Manipulate the cloud
-----------------------------

Directives: script

There are scripts for manipulating the cloud, usually at the Juju level. These
include:

* *add_unit.py*: Use juju to add a unit to a given service
* *chaos_pony.py*: Kill, test and add units to all services
* *delete_crm_leader.py*: Delete the unit Corosync reports is the leader for a
                          given service
* *delete_router_home.py*: Delete the unit housing a particular Neutron router
* *delete_unit.py*: Delete a given unit
* *juju_set.py*: Juju set a kv pair for a given service
* *upgrade_all_services.py*: Perform a Juju charm upgrade on all services
* *upgrade_services.py*: Perform a Juju charm upgrade on a given service

Helper Libraries
================

There are two helper libraries in *helper/utils/*.

* *mojo_os_utils.py*: Functions for manipulating the deployed Openstack cloud.
* *mojo_utils.py*: Functions for manipulating the providor environment. Juju
                   add/remove unit etc

Using mojo
==========

Install mojo (Stolen from https://launchpad.net/mojo)
sudo add-apt-repository ppa:mojo-maintainers/ppa
sudo apt-get update
sudo apt-get install mojo

sudo mojo project-new --series trusty mojo-openstack-specs
sudo adduser ubuntu mojo
sudo chmod 755 /var/lib/lxc/mojo-openstack-specs.trusty && sudo chmod 755 /var/lib/lxc

mojo workspace-new --project mojo-openstack-specs --series trusty --stage full_stack/next_deploy lp:~ost-maintainers/openstack-mojo-specs/mojo-openstack-specs run1
mojo run --project mojo-openstack-specs --series trusty --stage full_stack/next_deploy lp:~ost-maintainers/openstack-mojo-specs/mojo-openstack-specs run1
