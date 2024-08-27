import asyncio
import inspect
from typing import Any, Awaitable, Callable, TypeVar, Union

from typing_extensions import ParamSpec, TypeIs

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
    func: Callable[P, Union[R, Awaitable[R]]],
) -> TypeIs[Callable[P, Awaitable[R]]]:
    return asyncio.iscoroutinefunction(func)


def encode_decode_value(encoder_decoder: Union[Encoder, Decoder, None], val: Any) -> Any:
    if not encoder_decoder:
        return val

    return encoder_decoder(val)
