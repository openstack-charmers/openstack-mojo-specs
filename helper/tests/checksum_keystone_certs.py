#!/usr/bin/env python
import hashlib
import filecmp
import glob
import os
import sys
import tempfile

root = '/var/lib/keystone/juju_ssl/'
sha = hashlib.sha256()
paths = [os.path.join(root, 'ubuntu_cloud_root_ca'),
         os.path.join(root, 'ubuntu_cloud_intermediate_ca'),
         '/usr/local/share/ca-certificates',
         '/etc/apache2/ssl/keystone']


def update_hash_from_path(hash, path, recurse_depth=10):
    """Recurse through path and update the provided hash for every file found.
    """
    if not recurse_depth:
        msg = ("Max recursion depth (%s) reached for update_hash_from_path() "
               "at path='%s' - not going any deeper" % (recurse_depth, path))
        raise msg

    if not os.path.isdir(path):
        print("WARNING: {} does not exist".format(path))

    for p in glob.glob("%s/*" % path):
        if os.path.isdir(p):
            update_hash_from_path(hash, p, recurse_depth=recurse_depth - 1)
        else:
            with open(p, 'r') as fd:
                data = fd.read()
                print("Found: {} - {}".format(
                    p, hashlib.sha256(data).hexdigest()))
                hash.update(data)

for path in paths:
    update_hash_from_path(sha, path)

# Check CA
with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
    name = tmpfile.name
    for path in [root + '/ubuntu_cloud_intermediate_ca/cacert.pem',
                 root + '/ubuntu_cloud_root_ca/cacert.pem']:
        if not os.path.exists(path):
            print("WARNING: {} does not exist".format(path))
            continue

        with open(path, 'r') as fd:
            tmpfile.write(fd.read())

ca = '/usr/local/share/ca-certificates/keystone_juju_ca_cert.crt'
if not os.path.exists(ca):
    print("WARNING: {} does not exist".format(ca))
elif not filecmp.cmp(ca, name):
    print("{} not consistent with root and intermediate ca .pems".format(ca))
    print(name)

os.unlink(tmpfile.name)

print("TOTAL: {}".format(sha.hexdigest()))
sys.exit(0)
