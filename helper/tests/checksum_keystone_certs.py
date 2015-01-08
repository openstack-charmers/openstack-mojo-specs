#!/usr/bin/env python
import hashlib
import glob
import os
import sys

root = '/var/lib/keystone/juju_ssl/'
sha = hashlib.sha256()
paths = [os.path.join(root, 'ubuntu_cloud_root_ca/*'),
         os.path.join(root, 'ubuntu_cloud_intermediate_ca/*'),
         '/usr/local/share/ca-certificates/*',
         '/etc/apache2/ssl/keystone/*']

for path in paths:
    for p in glob.glob(path):
        if os.path.isfile(p):
            with open(p, 'rb') as fd:
                fd.seek(0)
                sha.update(fd.read())

print sha.hexdigest()
sys.exit(0)

