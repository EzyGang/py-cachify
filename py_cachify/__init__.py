from ._backend._cached import async_cached, cached, sync_cached
from ._backend._exceptions import CachifyInitError, CachifyLockError
from ._backend._lib import init_cachify
from ._backend._lock import async_once, lock, once, sync_once
from ._backend._types._common import AsyncClient, Decoder, Encoder, SyncClient


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
