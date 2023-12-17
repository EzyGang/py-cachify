from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any, Awaitable

from typing_extensions import ParamSpec


P = ParamSpec('P')
SyncFunc = Callable[[P.args, P.kwargs], Any]
AsyncFunc = Callable[[P.args, P.kwargs], Awaitable[Any]]
DecoratorFunc = Callable[[SyncFunc | AsyncFunc], AsyncFunc | SyncFunc]


def get_full_key_from_signature(bound_args: inspect.BoundArguments, key: str) -> str:
    args_dict = bound_args.arguments
    args = args_dict.pop('args', ())
    kwargs = args_dict.pop('kwargs', {})
    kwargs.update(args_dict)

    try:
        return key.format(*args, **kwargs)
    except IndexError:
        raise ValueError('Arguments in a key do not match function signature') from None
