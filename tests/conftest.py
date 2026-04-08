# pyright: reportPrivateUsage=false
from typing import Any

import pytest

import py_cachify._backend._lib
from py_cachify import init_cachify


@pytest.fixture(scope='function')
def init_cachify_fixture() -> Any:
    init_cachify()
    yield
    assert py_cachify._backend._lib._cachify
    py_cachify._backend._lib._cachify._sync_client._cache = {}  # pyright: ignore[reportAttributeAccessIssue]
    py_cachify._backend._lib._cachify = None
