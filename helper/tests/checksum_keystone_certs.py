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

def update_hash_from_path(hash, path, recurse_depth=10):
    """Recurse through path and update the provided hash for every file found.
    """
    if not recurse_depth:
        msg = ("Max recursion depth (%s) reached for update_hash_from_path() "
               "at path='%s' - not going any deeper" % (recurse_depth, path))
        return sum

    for p in glob.glob("%s/*" % path):
        if os.path.isdir(p):
            update_hash_from_path(hash, p, recurse_depth=recurse_depth - 1)
        else:
            with open(p, 'r') as fd:
                data = fd.read()
                hash.update(data)

for path in paths:
    update_hash_from_path(sha, path)

print sha.hexdigest()
sys.exit(0)

