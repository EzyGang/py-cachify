import pytest

import py_cachify.backend.lib
from py_cachify.backend.lib import init_cachify


@pytest.fixture(scope='function')
def init_cachify_fixture():
    init_cachify()
    yield
    py_cachify.backend.lib._cachify._sync_client._cache = {}
    py_cachify.backend.lib._cachify = None
