import inspect

import pytest

from py_cachify.base import get_full_key_from_signature


def method_with_args_kwargs_args(*args, **kwargs) -> None:
    pass


@pytest.fixture
def args_kwargs_signature():
    return inspect.signature(method_with_args_kwargs_args)


def test_get_full_key_valid_arguments(args_kwargs_signature):
    bound_args = args_kwargs_signature.bind('value1', 'value2', arg3='value3')
    result = get_full_key_from_signature(bound_args, 'key_{}_{}_{arg3}')
    assert result == 'key_value1_value2_value3'


def test_get_full_key_invalid_key_format(args_kwargs_signature):
    bound_args = args_kwargs_signature.bind('value1', 'value2')
    with pytest.raises(ValueError, match='Arguments in a key do not match function signature'):
        get_full_key_from_signature(bound_args, 'key_{}_{}_{}')


def test_get_full_key_empty_key_and_arguments(args_kwargs_signature):
    bound_args = args_kwargs_signature.bind()
    result = get_full_key_from_signature(bound_args, 'key_with_no_args')
    assert result == 'key_with_no_args'


def test_get_full_key_mixed_placeholders(args_kwargs_signature):
    bound_args = args_kwargs_signature.bind('value1', 'value2', arg3='value3')
    with pytest.raises(ValueError, match='Arguments in a key do not match function signature'):
        get_full_key_from_signature(bound_args, 'key_{}_{}_{}_{invalid_arg}')
