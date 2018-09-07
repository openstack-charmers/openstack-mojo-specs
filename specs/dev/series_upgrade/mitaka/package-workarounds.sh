#!/bin/bash

# Clean up packages that fail to upgrade non-interactively
rm -f /etc/default/ipmievd
sudo cp /home/ubuntu/corosync.conf /etc/corosync/corosync.conf || :
sudo cp /home/ubuntu/corosync /etc/default/corosync || :
sudo chmod 644 /etc/corosync/corosync.conf || :
sudo chmod 644 /etc/default/corosync || :
