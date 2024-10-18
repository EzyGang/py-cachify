import pytest

import py_cachify._backend._lib
from py_cachify import init_cachify


@pytest.fixture(scope='function')
def init_cachify_fixture():
    init_cachify()
    yield
    py_cachify._backend._lib._cachify._sync_client._cache = {}
    py_cachify._backend._lib._cachify = None
