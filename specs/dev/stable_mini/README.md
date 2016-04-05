# Example of the mini deployment:

```
[Services]
NAME                  STATUS EXPOSED CHARM
glance                active false   local:trusty/glance-150
keystone              active false   local:trusty/keystone-0
mysql                 active false   local:trusty/percona-cluster-45
neutron-api           active false   local:trusty/neutron-api-0
neutron-gateway       active false   local:trusty/neutron-gateway-64
neutron-openvswitch          false   local:trusty/neutron-openvswitch-0
nova-cloud-controller active false   local:trusty/nova-cloud-controller-501
nova-compute          active false   local:trusty/nova-compute-133
rabbitmq-server       active false   local:trusty/rabbitmq-server-150

[Units]
ID                      WORKLOAD-STATE AGENT-STATE VERSION MACHINE PORTS             PUBLIC-ADDRESS MESSAGE
glance/0                active         idle        1.25.3  1       9292/tcp          172.17.118.81  Unit is ready
keystone/0              active         idle        1.25.3  2                         172.17.118.82  Unit is ready
mysql/0                 active         idle        1.25.3  3                         172.17.118.83  Unit is ready
neutron-api/0           active         idle        1.25.3  4       9696/tcp          172.17.118.84  Unit is ready
neutron-gateway/0       active         idle        1.25.3  5                         172.17.118.85  Unit is ready
nova-cloud-controller/0 active         idle        1.25.3  6       8774/tcp,9696/tcp 172.17.118.86  Unit is ready
nova-compute/0          active         idle        1.25.3  7                         172.17.118.3   Unit is ready
  neutron-openvswitch/0 active         idle        1.25.3                            172.17.118.3   Unit is ready  
rabbitmq-server/0       active         idle        1.25.3  8       5672/tcp          172.17.118.4   Unit is ready

[Machines]
ID         STATE   VERSION DNS           INS-ID                               SERIES HARDWARE
0          started 1.25.3  172.17.118.80 4757052d-92b0-4914-b246-9667f7dfdc37 trusty arch=amd64 cpu-cores=1 mem=1536M root-disk=10240M availability-zone=nova
1          started 1.25.3  172.17.118.81 9c2580dc-32ec-4a2e-90f3-d2ee40883dfa trusty arch=amd64 cpu-cores=1 mem=1536M root-disk=10240M availability-zone=nova
2          started 1.25.3  172.17.118.82 2653dce8-37fb-4f92-b01d-ffc5a88f4209 trusty arch=amd64 cpu-cores=1 mem=1536M root-disk=10240M availability-zone=nova
3          started 1.25.3  172.17.118.83 3c8c8c9e-3168-4cf1-87d9-7aaa11299407 trusty arch=amd64 cpu-cores=1 mem=1536M root-disk=10240M availability-zone=nova
4          started 1.25.3  172.17.118.84 3d13702a-3010-4f25-9d0e-20f389e58e3e trusty arch=amd64 cpu-cores=1 mem=1536M root-disk=10240M availability-zone=nova
5          started 1.25.3  172.17.118.85 1d1804f4-8e2c-43a5-a947-fbad2dc66d15 trusty arch=amd64 cpu-cores=1 mem=1536M root-disk=10240M availability-zone=nova
6          started 1.25.3  172.17.118.86 510ecbb4-1ef7-4b81-bff1-95fde6ac71f7 trusty arch=amd64 cpu-cores=1 mem=1536M root-disk=10240M availability-zone=nova
7          started 1.25.3  172.17.118.3  73f987af-606b-4c60-b039-a76faa40b85b trusty arch=amd64 cpu-cores=1 mem=1536M root-disk=10240M availability-zone=nova
8          started 1.25.3  172.17.118.4  b51543e6-90e1-4bdc-b256-3776a6792390 trusty arch=amd64 cpu-cores=1 mem=1536M root-disk=10240M availability-zone=nova
```
