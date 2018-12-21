#
# conftest.py
#
# Pytest fixtures
#
# You must set environment variable DIGITALGLOBE_STAC_PASSWORD.
#

import os
import pytest

from dgcatalog import Stac


def get_connection_params():
    """
    Read connection values from the environment variables STAC_SERVICE_URL, STAC_USERNAME,
    and STAC_PASSWORD.
    :return: Tuple (url, username, password)
    """
    url = os.getenv('STAC_SERVICE_URL')
    if not url:
        raise Exception('Environment variable STAC_SERVICE_URL is not set.')
    username = os.getenv('STAC_USERNAME')
    if not username:
        raise Exception('Environment variable STAC_USERNAME is not set.')
    password = os.getenv('STAC_PASSWORD')
    if not password:
        raise Exception('Environment variable STAC_PASSWORD is not set.')
    return (url, username, password)


@pytest.fixture(scope='session')
def stac():
    """
    Pytest fixture that constructs a Stac object by connecting to a Stac service.
    :return:
    """
    (url, username, password) = get_connection_params()
    print('Using STAC service {} with user {}'.format(url, username))
    stac = Stac(url=url, username=username, password=password)
    print('Connection succeeded')
    return stac
