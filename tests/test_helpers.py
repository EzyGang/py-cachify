import inspect
import re

import pytest
from pytest_mock import MockerFixture

from py_cachify._backend._helpers import a_reset, get_full_key_from_signature, is_alocked, is_locked, reset


def method_with_args_kwargs_args(*args, **kwargs) -> None:
    pass


@pytest.fixture
def args_kwargs_signature():
    return inspect.signature(method_with_args_kwargs_args)


def test_get_full_key_valid_arguments(args_kwargs_signature):
    bound_args = args_kwargs_signature.bind('value1', 'value2', arg3='value3')
    result = get_full_key_from_signature(bound_args, 'key_{}_{}_{arg3}', operation_postfix='cached')
    assert result == 'key_value1_value2_value3-cached'


def test_get_full_key_invalid_key_format(args_kwargs_signature):
    bound_args = args_kwargs_signature.bind('value1', 'value2')
    bound_args.apply_defaults()

    with pytest.raises(
        ValueError,
        match=re.escape(f'Arguments in a key(key_{{}}_{{}}_{{}}) do not match function signature params({bound_args})'),
    ):
        get_full_key_from_signature(bound_args, 'key_{}_{}_{}', operation_postfix='cached')


def test_get_full_key_empty_key_and_arguments(args_kwargs_signature):
    bound_args = args_kwargs_signature.bind()
    result = get_full_key_from_signature(bound_args, 'key_with_no_args', operation_postfix='cached')
    assert result == 'key_with_no_args-cached'


def test_get_full_key_mixed_placeholders(args_kwargs_signature):
    bound_args = args_kwargs_signature.bind('value1', 'value2', arg3='value3')
    bound_args.apply_defaults()

    with pytest.raises(
        ValueError,
        match=re.escape(
            'Arguments in a key(key_{}_{}_{}_{invalid_arg}) ' + f'do not match function signature params({bound_args})'
        ),
    ):
        _ = get_full_key_from_signature(bound_args, 'key_{}_{}_{}_{invalid_arg}', operation_postfix='cached')


def test_reset_calls_delete_with_key(init_cachify_fixture, args_kwargs_signature, mocker: MockerFixture):
    mock = mocker.patch('py_cachify._backend._lib.Cachify.delete')

    reset(
        'val1', 'val2', arg3='val3', key='key_{}_{}_{arg3}', signature=args_kwargs_signature, operation_postfix='cached'
    )

    mock.assert_called_once_with(key='key_val1_val2_val3-cached')


@pytest.mark.asyncio
async def test_a_reset_calls_delete_with_key(init_cachify_fixture, args_kwargs_signature, mocker: MockerFixture):
    mock = mocker.patch('py_cachify._backend._lib.Cachify.a_delete')

    await a_reset(
        'val1', 'val2', arg3='val3', key='key_{}_{}_{arg3}', signature=args_kwargs_signature, operation_postfix='cached'
    )

    mock.assert_called_once_with(key='key_val1_val2_val3-cached')


@pytest.mark.asyncio
@pytest.mark.parametrize('val', [0, 1])
async def test_is_alocked_accesses_a_get_with_key(
    init_cachify_fixture, args_kwargs_signature, mocker: MockerFixture, val
):
    mock = mocker.patch('py_cachify._backend._lib.Cachify.a_get', return_value=val)

    res = await is_alocked(
        'val1', 'val2', arg3='val3', key='key_{}_{}_{arg3}', signature=args_kwargs_signature, operation_postfix='cached'
    )

    mock.assert_called_once_with(key='key_val1_val2_val3-cached')
    assert res is bool(val)


@pytest.mark.parametrize('val', [0, 1])
def test_is_locked_accesses_get_with_key(init_cachify_fixture, args_kwargs_signature, mocker: MockerFixture, val):
    mock = mocker.patch('py_cachify._backend._lib.Cachify.get', return_value=val)

    res = is_locked(
        'val1', 'val2', arg3='val3', key='key_{}_{}_{arg3}', signature=args_kwargs_signature, operation_postfix='cached'
    )

    mock.assert_called_once_with(key='key_val1_val2_val3-cached')
    assert res is bool(val)
