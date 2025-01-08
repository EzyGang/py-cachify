import asyncio
import inspect
from typing import Any, Awaitable, Callable, Dict, Tuple, TypeVar, Union

from typing_extensions import ParamSpec, TypeIs

from ._lib import get_cachify
from ._types._common import Decoder, Encoder


_R = TypeVar('_R', covariant=True)
_P = ParamSpec('_P')
_S = TypeVar('_S')


def get_full_key_from_signature(bound_args: inspect.BoundArguments, key: str) -> str:
    bound_args.apply_defaults()
    _args_repr = f'{bound_args}'

    args_dict = bound_args.arguments
    args: Tuple[Any, ...] = args_dict.pop('args', ())
    kwargs: Dict[str, Any] = args_dict.pop('kwargs', {})
    kwargs.update(args_dict)

    try:
        return key.format(*args, **kwargs)
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
