#!/bin/bash

set -e

DESIGNATE_BIND_IP=$(juju status designate-bind --format short | grep designate-bind | awk '{print $3}')
DESIGNATE_DOMAIN_NAME=mojo.serverstack
FLOATING_IP=$(${MOJO_SPEC_DIR}/${MOJO_STAGE}/get_floating_ip.py | tail -n 1)

dig @$DESIGNATE_BIND_IP +tcp +short -x $FLOATING_IP  | grep $DESIGNATE_DOMAIN_NAME
dig @$DESIGNATE_BIND_IP +tcp +short -x $FLOATING_IP
