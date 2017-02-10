#!/usr/bin/python


import logging
import os
import subprocess
import sys


class Juju(object):
    """ This class creates a translation between juju-1 and juju-2
    """

    @property
    def bin(self):
        if os.environ.get('JUJU_BINARY'):
            juju = os.environ.get('JUJU_BINARY')
        elif os.environ.get('JUJU_VERSION'):
            version = (".".join(os.environ.get('JUJU_VERSION')
                       .split('-')[0].split('.')[:2]))
            juju = 'juju-{}'.format(version)
        else:
            juju = 'juju'
        return juju

    @property
    def version(self):
        try:
            return float(".".join(subprocess
                                  .check_output([self.bin, 'version'])
                         .split('-')[0].split('.')[:2]))
        except OSError as e:
            logging.error("Juju is not installed at {}. Error: {}"
                          "".format(self.bin, e))
            sys.exit(1)

    @property
    def service(self):
        if self.version < 2:
            return "service"
        else:
            return "application"

    @property
    def services(self):
        return '{}s'.format(self.service)

    @property
    def set(self):
        if self.version >= 2.1:
            return "config"
        elif self.version < 2:
            return "set"
        elif self.version == 2.0:
            return "set-config"

    @property
    def get(self):
        if self.version >= 2.1:
            return "config"
        elif self.version < 2:
            return "get"
        elif self.version == 2.0:
            return "get-config"

    @property
    def set_environment(self):
        if self.version >= 2.1:
            return "model-config"
        elif self.version < 2:
            return "set-environment"
        elif self.version == 2.0:
            return "set-model-config"

    @property
    def destroy_unit(self):
        if self.version < 2:
            return "destroy-unit"
        else:
            return "remove-unit"

    @property
    def action(self):
        if self.version < 2:
            return "action"
        else:
            return "actions"

    @property
    def action_fetch(self):
        if self.version < 2:
            return "fetch"
        else:
            return "show-action-output"

    @property
    def action_do(self):
        if self.version < 2:
            return "do"
        else:
            return "run-action"
