#!/usr/bin/python
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils
import logging
import os


def main(argv):
    logging.basicConfig(level=logging.INFO)
    overcloud_novarc = mojo_utils.get_overcloud_auth()
    glance_client = mojo_os_utils.get_glance_client(overcloud_novarc)
    current_images = mojo_os_utils.get_images_list(glance_client)
    image_config = mojo_utils.get_mojo_config('images.yaml')
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
