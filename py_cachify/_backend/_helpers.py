import asyncio
import inspect
from collections.abc import Awaitable
from typing import Any, Callable, TypeVar, Union

from typing_extensions import ParamSpec, TypeIs

from ._constants import OperationPostfix
from ._lib import CachifyClient
from ._logger import logger
from ._types._common import Decoder, Encoder


_R = TypeVar('_R', covariant=True)
_P = ParamSpec('_P')
_S = TypeVar('_S')


def _call_original(
    _pyc_original_func: Union[Callable[..., Any], None], _pyc_method_name: str, *args: Any, **kwargs: Any
) -> Any:
    if not _pyc_original_func:
        return

    orig_method = getattr(_pyc_original_func, _pyc_method_name, None)
    if not orig_method or not callable(orig_method):
        return

    try:
        return orig_method(*args, **kwargs)
    except Exception as e:
        logger.debug(f'Error calling original reset: {e}')

    return None


async def _acall_original(
    _pyc_original_func: Union[Callable[..., Awaitable[Any]], None], _pyc_method_name: str, *args: Any, **kwargs: Any
) -> Any:
    if not _pyc_original_func:
        return

    orig_method = getattr(_pyc_original_func, _pyc_method_name, None)
    if not orig_method or not is_coroutine(orig_method):
        return

    try:
        return await orig_method(*args, **kwargs)
    except Exception as e:
        logger.debug(f'Error calling original reset: {e}')

    return None


def get_full_key_from_signature(
    bound_args: inspect.BoundArguments,
    key: str,
    operation_postfix: OperationPostfix,
) -> str:
    bound_args.apply_defaults()
    _args_repr = f'{bound_args}'

    args_dict = bound_args.arguments
    args: tuple[Any, ...] = args_dict.pop('args', ())
    kwargs: dict[str, Any] = args_dict.pop('kwargs', {})
    kwargs.update(args_dict)

    try:
        return f'{key.format(*args, **kwargs)}-{operation_postfix}'
    except (IndexError, KeyError):
        raise ValueError(f'Arguments in a key({key}) do not match function signature params({_args_repr})') from None


def is_coroutine(
    func: Union[Callable[_P, Awaitable[_R]], Callable[_P, _R]],
) -> TypeIs[Callable[_P, Awaitable[_R]]]:
    return asyncio.iscoroutinefunction(func)


def encode_decode_value(encoder_decoder: Union[Encoder, Decoder, None], val: Any) -> Any:
    if not encoder_decoder:
        return val

    return encoder_decoder(val)


def reset(
    *args: Any,
    _pyc_key: str,
    _pyc_signature: inspect.Signature,
    _pyc_operation_postfix: OperationPostfix,
    _pyc_original_func: Union[Callable[..., Any], None],
    _pyc_client_provider: Callable[..., CachifyClient],
    **kwargs: Any,
) -> None:
    client = _pyc_client_provider()
    _key = get_full_key_from_signature(
        bound_args=_pyc_signature.bind(*args, **kwargs),
        key=_pyc_key,
        operation_postfix=_pyc_operation_postfix,
    )

    client.delete(key=_key)

    _call_original(_pyc_original_func, 'reset', *args, **kwargs)


async def a_reset(
    *args: Any,
    _pyc_key: str,
    _pyc_signature: inspect.Signature,
    _pyc_operation_postfix: OperationPostfix,
    _pyc_original_func: Union[Callable[..., Awaitable[Any]], None],
    _pyc_client_provider: Callable[..., CachifyClient],
    **kwargs: Any,
) -> None:
    client = _pyc_client_provider()
    _key = get_full_key_from_signature(
        bound_args=_pyc_signature.bind(*args, **kwargs), key=_pyc_key, operation_postfix=_pyc_operation_postfix
    )

    await client.a_delete(key=_key)

    await _acall_original(_pyc_original_func, 'reset', *args, **kwargs)


async def is_alocked(
    *args: Any,
    _pyc_key: str,
    _pyc_signature: inspect.Signature,
    _pyc_operation_postfix: OperationPostfix,
    _pyc_original_func: Union[Callable[..., Awaitable[Any]], None],
    _pyc_client_provider: Callable[..., CachifyClient],
    **kwargs: Any,
) -> bool:
    client = _pyc_client_provider()
    _key = get_full_key_from_signature(
        bound_args=_pyc_signature.bind(*args, **kwargs), key=_pyc_key, operation_postfix=_pyc_operation_postfix
    )

    if bool(await client.a_get(key=_key)):
        return True

    return await _acall_original(_pyc_original_func, 'is_locked', *args, **kwargs) or False


def is_locked(
    *args: Any,
    _pyc_key: str,
    _pyc_signature: inspect.Signature,
    _pyc_operation_postfix: OperationPostfix,
    _pyc_original_func: Union[Callable[..., Any], None],
    _pyc_client_provider: Callable[..., CachifyClient],
    **kwargs: Any,
) -> bool:
    client = _pyc_client_provider()
    _key = get_full_key_from_signature(
        bound_args=_pyc_signature.bind(*args, **kwargs), key=_pyc_key, operation_postfix=_pyc_operation_postfix
    )

    if bool(client.get(key=_key)):
        return True

    return _call_original(_pyc_original_func, 'is_locked', *args, **kwargs) or False
