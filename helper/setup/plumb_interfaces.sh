#!/bin/bash

# After adding the second interface we need to add it to the guest
#       OS so that it will persist after a reboot
#
# This script adds the second interface to /etc/netplan/60-dataport.yaml
#       and then runs a 'netplan apply' on the host

echo Adding data-port interface to netplan

OS_PORT_LIST=$(openstack port list -c "MAC Address" -c "Fixed IP Addresses")
OS_SERVER_LIST=$(openstack server list)

for IP in $(juju status neutron-gateway|grep "Machine  State" -A2|tail -n2|awk '{print $3}')
do
        IFS=''
        dataport_IP=$(echo $OS_SERVER_LIST | grep ${IP} | awk '{print $9}')
        mac_addr=$(echo $OS_PORT_LIST | grep $dataport_IP |awk '{print $2}')
        interface=$(juju ssh ${IP} "ip addr|grep ${mac_addr} -B1|head -n1")
        interface=$(echo $interface | awk '{print $2}' | tr -d ':')
        cat << EOF > temp_${IP}
network:
    ethernets:
        ${interface}:
            dhcp4: false
            dhcp6: true
            optional: true
            match:
                macaddress: ${mac_addr}
            set-name: ${interface}

    version: 2
EOF
cat temp_${IP}
juju scp temp_${IP} ${IP}:/home/ubuntu/
juju ssh ${IP} "sudo mv /home/ubuntu/temp_${IP} /etc/netplan/60-dataport.yaml ; sudo netplan apply"
rm temp_${IP}
done
