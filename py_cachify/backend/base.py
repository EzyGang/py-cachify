import asyncio
import inspect
from typing import Awaitable, Callable, TypeVar, Union

from typing_extensions import ParamSpec, TypeGuard


R = TypeVar('R')
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


def is_coroutine(func: Union[Callable[P, R], Callable[P, Awaitable[R]]]) -> TypeGuard[Callable[P, Awaitable[R]]]:
    return asyncio.iscoroutinefunction(func)
