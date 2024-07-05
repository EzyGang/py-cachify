import sys

import pytest
from pytest_mock import MockerFixture

from py_cachify import cached


class UnpicklableClass:
    def __init__(self, arg1: str, arg2: str) -> None:
        self._arg1 = arg1
        self._arg2 = arg2

    def __eq__(self, other: 'UnpicklableClass') -> bool:
        return self._arg1 == other._arg1 and self._arg2 == other._arg2

    def __reduce__(self):
        raise TypeError('This class is not picklable')


def create_unpicklable_class(arg1: str, arg2: str) -> UnpicklableClass:
    return UnpicklableClass(arg1=arg1, arg2=arg2)


def test_cached_decorator_without_encoder():
    wrapped_create = cached(key='test_create_unpicklable-{arg1}-{arg2}')(create_unpicklable_class)

    with pytest.raises(TypeError, match='This class is not picklable'):
        wrapped_create('arg1', 'arg2')


def test_cached_decorator_with_encoder_decoder(mocker: MockerFixture):
    def encoder(val: UnpicklableClass) -> dict:
        return {'arg1': val._arg1, 'arg2': val._arg2}

    def decoder(val: dict) -> UnpicklableClass:
        return UnpicklableClass(**val)

    spy_on_create = mocker.spy(sys.modules[__name__], 'create_unpicklable_class')

    wrapped_create = cached(key='test_create_unpicklable_dec_enc-{arg1}-{arg2}', enc_dec=(encoder, decoder))(
        create_unpicklable_class
    )

    res_1 = wrapped_create('test1', 'test2')
    res_2 = wrapped_create('test1', 'test2')

    assert res_1 == res_2
    spy_on_create.assert_called_once_with('test1', 'test2')
