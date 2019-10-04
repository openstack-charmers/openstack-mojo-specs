#!/usr/bin/env python3
import logging
import os
import threading
import hashlib
import string
import random
import utils.mojo_os_utils as mojo_os_utils
import sys

from zaza.openstack.utilities import openstack as openstack_utils


class ObjectPushPull(threading.Thread):
    def __init__(self, runs, thread_name, payload_size='s'):
        super(ObjectPushPull, self).__init__()
        self.runs = runs
        self.thread_name = thread_name
        self.payload_size = payload_size
        self.container = thread_name
        self.sc = self.get_swiftclient()
        self.sc.put_container(container=self.container)
        self.successes = 0
        self.failures = 0

    def get_hash(self, rstring):
        hash_object = hashlib.sha1(rstring.encode('UTF-8'))
        return hash_object.hexdigest()

    def get_test_string(self,):
        # Large ~ 100Mb
        sizes = {
            's': 10000,
            'm': 100000,
            'l': 100000000,
        }
        root_str = random.choice(string.ascii_letters)
        root_str += random.choice(string.ascii_letters)
        return root_str*sizes[self.payload_size]

    def run(self):
        for i in range(0, self.runs):
            test_string = self.get_test_string()
            string_hash = self.get_hash(test_string)
            test_file = 'testfile.' + self.thread_name
            self.upload_file(test_file, test_string)
            if self.verify_file(test_file, string_hash):
                self.successes += 1
            else:
                self.failures += 1

    def get_swiftclient(self):
        try:
            cacert = os.path.join(
                os.environ.get('MOJO_LOCAL_DIR'), 'cacert.pem')
            os.stat(cacert)
        except FileNotFoundError:
            cacert = None
        print(cacert)
        keystone_session = openstack_utils.get_overcloud_keystone_session(
            verify=cacert)
        swift_client = mojo_os_utils.get_swift_session_client(keystone_session, cacert=cacert)
        return swift_client

    def get_checkstring(self, fname):
        return fname.split('-')[1]

    def verify_file(self, fname, check_hash):
        headers, content = self.sc.get_object(self.container, fname,
                                              headers={'If-Match': self.etag})
        return check_hash == self.get_hash(content.decode('UTF-8'))

    def upload_file(self, fname, contents):
        response = {}
        self.sc.put_object(self.container, fname, contents,
                           response_dict=response)
        self.etag = response['headers']['etag']


def main(argv):
    thread1 = ObjectPushPull(10, 'thread1', payload_size='l')
    thread2 = ObjectPushPull(100, 'thread2', payload_size='s')
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()
    print("Thread 1")
    print("    Successes: {}".format(thread1.successes))
    print("    Failures: {}".format(thread1.failures))
    print("Thread 2")
    print("    Successes: {}".format(thread2.successes))
    print("    Failures: {}".format(thread2.failures))
    if (thread1.successes != 10 or thread2.successes != 100):
        logging.error("Object Storage Test Failed")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
