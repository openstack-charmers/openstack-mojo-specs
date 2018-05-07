#!/usr/bin/env python3

import logging
import os

REQUIRED = [
    'MOJO_STAGE',
    'MOJO_WORKSPACE',
    'MOJO_PROJECT',
    'MOJO_SERIES',
    'MOJO_SPEC',
    'OS_REGION_NAME',
    'OS_PASSWORD',
    'OS_AUTH_URL',
    'OS_USERNAME',
    'OS_PROJECT_NAME',
    'MOJO_OS_VIP01',
    'MOJO_OS_VIP02',
    'MOJO_OS_VIP03',
    'MOJO_OS_VIP04',
    'MOJO_OS_VIP05',
    'MOJO_OS_VIP06',
    'MOJO_OS_VIP07',
    'MOJO_OS_VIP08',
    'MOJO_OS_VIP09',
    'MOJO_OS_VIP10',
]


class MissingEnvVariableExeption(Exception):
    pass


logging.info("Running pre-flight check for environment variables")
for var in REQUIRED:
    if os.environ.get(var) is None:
        raise MissingEnvVariableExeption(
            "The variable, {}, is missing from the environment.\n"
            "Make sure all required variables in the {} "
            "script are available before running mojo\n\n"
            "Required: {}"
            "".format(var, os.path.basename(__file__),
                      ", ".join(REQUIRED)))

logging.debug("All required environment variables successfully found.")
