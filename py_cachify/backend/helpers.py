import asyncio
import inspect
from typing import Any, Awaitable, Callable, TypeVar, Union

from typing_extensions import ParamSpec, TypeIs

from .lib import get_cachify
from .types import Decoder, Encoder


R = TypeVar('R', covariant=True)
P = ParamSpec('P')


def get_full_key_from_signature(bound_args: inspect.BoundArguments, key: str) -> str:
    args_dict = bound_args.arguments
    args = args_dict.pop('args', ())
    kwargs = args_dict.pop('kwargs', {})
    kwargs.update(args_dict)

    try:
        return key.format(*args, **kwargs)
    except IndexError:
        raise ValueError('Arguments in a key do not match function signature') from None


def is_coroutine(
    func: Union[Callable[P, Awaitable[R]], Callable[P, R]],
) -> TypeIs[Callable[P, Awaitable[R]]]:
    return asyncio.iscoroutinefunction(func)


def encode_decode_value(encoder_decoder: Union[Encoder, Decoder, None], val: Any) -> Any:
    if not encoder_decoder:
        return val

    return encoder_decoder(val)


def reset(*args: Any, key: str, signature: inspect.Signature, **kwargs: Any) -> None:
    cachify = get_cachify()
    _key = get_full_key_from_signature(bound_args=signature.bind(*args, **kwargs), key=key)

    cachify.delete(key=_key)

    return None


async def a_reset(*args: Any, key: str, signature: inspect.Signature, **kwargs: Any) -> None:
    cachify = get_cachify()
    _key = get_full_key_from_signature(bound_args=signature.bind(*args, **kwargs), key=key)

    await cachify.a_delete(key=_key)

    return None


async def is_alocked(*args: Any, key: str, signature: inspect.Signature, **kwargs: Any) -> bool:
    cachify = get_cachify()
    _key = get_full_key_from_signature(bound_args=signature.bind(*args, **kwargs), key=key)

    return bool(await cachify.a_get(key=_key))


def is_locked(*args: Any, key: str, signature: inspect.Signature, **kwargs: Any) -> bool:
    cachify = get_cachify()
    _key = get_full_key_from_signature(bound_args=signature.bind(*args, **kwargs), key=key)

    return bool(cachify.get(key=_key))
