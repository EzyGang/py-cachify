from importlib.metadata import version

from . import asyncio, sync
from .backend.cached import cached
from .backend.exceptions import CachifyInitError, CachifyLockError
from .backend.lib import init_cachify
from .backend.lock import lock, once
from .backend.types import Decoder, Encoder


try:
    __version__ = version('py-cachify')
except ModuleNotFoundError:
    __version__ = f'No version available for {__name__}'


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
