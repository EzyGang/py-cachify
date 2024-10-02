from importlib.metadata import version

from . import asyncio, sync
from .backend.cached import cached
from .backend.exceptions import CachifyInitError, CachifyLockError
from .backend.lib import init_cachify
from .backend.lock import lock, once
from .backend.types import Decoder, Encoder


__version__ = version('py-cachify')

__all__ = [
    'CachifyInitError',
    'CachifyLockError',
    'init_cachify',
    'lock',
    'Encoder',
    'Decoder',
    'cached',
    'once',
    'sync',
    'asyncio',
]
