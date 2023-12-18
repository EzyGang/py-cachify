import inspect
from typing import Any, Awaitable, Callable, Union

from typing_extensions import ParamSpec


P = ParamSpec('P')
SyncFunc = Callable[P, Any]
AsyncFunc = Callable[P, Awaitable[Any]]
DecoratorFunc = Callable[[Union[SyncFunc, AsyncFunc]], Union[AsyncFunc, SyncFunc]]


def get_full_key_from_signature(bound_args: inspect.BoundArguments, key: str) -> str:
    args_dict = bound_args.arguments
    args = args_dict.pop('args', ())
    kwargs = args_dict.pop('kwargs', {})
    kwargs.update(args_dict)

    try:
        return key.format(*args, **kwargs)
    except IndexError:
        raise ValueError('Arguments in a key do not match function signature') from None
