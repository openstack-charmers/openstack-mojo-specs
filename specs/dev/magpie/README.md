# Example of a successful deploy:

```
[Services]
NAME       STATUS EXPOSED CHARM
magpie     active false   local:xenial/magpie-0

[Units]
ID       WORKLOAD-STATE AGENT-STATE VERSION MACHINE PORTS PUBLIC-ADDRESS MESSAGE
magpie/0 active         idle        1.25.6  1             172.17.121.41  icmp ok, local hostname ok, dns ok
magpie/1 active         idle        1.25.6  3             172.17.121.43  icmp ok, local hostname ok, dns ok
magpie/2 active         idle        1.25.6  2             172.17.121.42  icmp ok, local hostname ok, dns ok
magpie/3 active         idle        1.25.6  5             172.17.121.45  icmp ok, local hostname ok, dns ok
magpie/4 active         idle        1.25.6  4             172.17.121.44  icmp ok, local hostname ok, dns ok
magpie/5 active         idle        1.25.6  7             172.17.121.47  icmp ok, local hostname ok, dns ok
magpie/6 active         idle        1.25.6  6             172.17.121.46  icmp ok, local hostname ok, dns ok
magpie/7 active         idle        1.25.6  8             172.17.121.48  icmp ok, local hostname ok, dns ok

[Machines]
ID         STATE   VERSION DNS           INS-ID                               SERIES HARDWARE
0          started 1.25.6  172.17.121.40 eb33cd61-9332-4ab2-bb0d-796ca72a240d xenial arch=amd64 cpu-cores=1 mem=1536M root-disk=10240M availability-zone=nova
1          started 1.25.6  172.17.121.41 1a7d0255-248d-47ed-ad57-545e359e54d1 xenial arch=amd64 cpu-cores=1 mem=1536M root-disk=10240M availability-zone=nova
2          started 1.25.6  172.17.121.42 785eaa59-3795-4b10-9822-810780d28415 xenial arch=amd64 cpu-cores=1 mem=1536M root-disk=10240M availability-zone=nova
3          started 1.25.6  172.17.121.43 9ffe62e1-0f15-46e6-90cc-93976d3460ae xenial arch=amd64 cpu-cores=1 mem=1536M root-disk=10240M availability-zone=nova
4          started 1.25.6  172.17.121.44 518a4705-716b-44bd-a407-0ec1a6c01c77 xenial arch=amd64 cpu-cores=1 mem=1536M root-disk=10240M availability-zone=nova
5          started 1.25.6  172.17.121.45 573bdd9f-80a2-40ec-98e5-2e4d0a71febe xenial arch=amd64 cpu-cores=1 mem=1536M root-disk=10240M availability-zone=nova
6          started 1.25.6  172.17.121.46 2c777056-365b-4dd6-a8d6-82ef18239536 xenial arch=amd64 cpu-cores=1 mem=1536M root-disk=10240M availability-zone=nova
7          started 1.25.6  172.17.121.47 82336764-d13a-45a2-811d-bd32048c4fe7 xenial arch=amd64 cpu-cores=1 mem=1536M root-disk=10240M availability-zone=nova
8          started 1.25.6  172.17.121.48 e165b572-48b7-4d84-b978-3dd69118f8fc xenial arch=amd64 cpu-cores=1 mem=1536M root-disk=10240M availability-zone=nova
```
