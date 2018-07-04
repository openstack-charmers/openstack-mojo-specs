#!/usr/bin/env python3
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils
import logging
import os

from zaza.utilities import (
    cli as cli_utils,
    generic as generic_utils,
    openstack as openstack_utils,
)


def main(argv):
    cli_utils.setup_logging()
    try:
        cacert = os.path.join(os.environ.get('MOJO_LOCAL_DIR'), 'cacert.pem')
        os.stat(cacert)
    except FileNotFoundError:
        cacert = None
    session = openstack_utils.get_overcloud_keystone_session(verify=cacert)
    glance_client = mojo_os_utils.get_glance_session_client(session)
    current_images = mojo_os_utils.get_images_list(glance_client)
    image_file = mojo_utils.get_mojo_file('images.yaml')
    image_config = generic_utils.get_yaml_config(image_file)
    cache_dir = '/tmp/img_cache'
    for image in image_config.keys():
        if image_config[image]['glance_name'] in current_images:
            logging.warning('Skipping %s it is already in'
                            'glance' % (image_config[image]['glance_name']))
            continue
        image_name = image_config[image]['url'].split('/')[-1]
        if os.path.exists(cache_dir + '/' + image_name):
            local_file = cache_dir + '/' + image_name
        else:
            local_file = mojo_os_utils.download_image(
                image_config[image]['url'])
        mojo_os_utils.upload_image(
            glance_client,
            local_file,
            image_config[image]['glance_name'],
            image_config[image]['is_public'],
            image_config[image]['disk_format'],
            image_config[image]['container_format'])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
