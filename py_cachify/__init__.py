from ._backend.cached import async_cached, cached, sync_cached
from ._backend.exceptions import CachifyInitError, CachifyLockError
from ._backend.lib import init_cachify
from ._backend.lock import async_once, lock, once, sync_once
from ._backend.types import AsyncClient, Decoder, Encoder, SyncClient


try:
    from importlib.metadata import version

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
    'AsyncClient',
    'SyncClient',
    # The following are deprecated (and are just aliases)
    'async_once',
    'sync_once',
    'async_cached',
    'sync_cached',
]
