#!/bin/bash

set -e
DESIGNATE_BIND_IP=$(juju status designate-bind --format short | grep designate-bind | awk '{print $3}')
juju config neutron-gateway dns-servers=$DESIGNATE_BIND_IP


${MOJO_SPEC_DIR}/${MOJO_STAGE}/designate_setup.py -r $DESIGNATE_BIND_IP

