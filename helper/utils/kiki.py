#!/usr/bin/python


import logging
import os
import subprocess
import sys


def cmd():
    if os.environ.get('JUJU_BINARY'):
        juju = os.environ.get('JUJU_BINARY')
    elif os.environ.get('JUJU_VERSION'):
        ver = (".".join(os.environ.get('JUJU_VERSION')
               .split('-')[0].split('.')[:2]))
        juju = 'juju-{}'.format(ver)
    else:
        juju = 'juju'
    return juju


def version():
    try:
        return float(".".join(subprocess
                              .check_output([cmd(), 'version'])
                     .split('-')[0].split('.')[:2]))
    except OSError as e:
        logging.error("Juju is not installed at {}. Error: {}"
                      "".format(cmd(), e))
        sys.exit(1)


def application():
    if version() < 2:
        return "service"
    else:
        return "application"


def applications():
    return '{}s'.format(application())


def config(change=False):
    if version() >= 2.1:
        return "config"
    elif version() < 2:
        if change:
            return "set"
        else:
            return "get"


def model_config(change=False):
    if version() >= 2.1:
        return "model-config"
    elif version() < 2:
        if change:
            return "set-environment"
        else:
            return "get-environment"


def remove_unit():
    if version() < 2:
        return "destroy-unit"
    else:
        return "remove-unit"


def actions():
    if version() < 2:
        return "action"
    else:
        return "actions"


def action_fetch():
    if version() < 2:
        return "fetch"
    else:
        return "show-action-output"


def action_run():
    if version() < 2:
        return "do"
    else:
        return "run-action"


def show_action_output_cmd():
    command = [cmd()]
    if version() < 2:
        command.append(actions())
    command.append(action_fetch())
    return command


def action_run_cmd():
    command = [cmd()]
    if version() < 2:
        command.append(actions())
    command.append(action_run())
    return command
