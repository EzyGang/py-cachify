from ._backend._cached import async_cached as async_cached
from ._backend._cached import cached as cached
from ._backend._cached import sync_cached as sync_cached
from ._backend._exceptions import CachifyInitError as CachifyInitError
from ._backend._exceptions import CachifyLockError as CachifyLockError
from ._backend._lib import init_cachify as init_cachify
from ._backend._lock import async_once as async_once
from ._backend._lock import lock as lock
from ._backend._lock import once as once
from ._backend._lock import sync_once as sync_once
from ._backend._types._common import AsyncClient as AsyncClient
from ._backend._types._common import Decoder as Decoder
from ._backend._types._common import Encoder as Encoder
from ._backend._types._common import SyncClient as SyncClient
from ._backend._types._lock_wrap import AsyncLockWrappedF as AsyncLockWrappedF
from ._backend._types._lock_wrap import SyncLockWrappedF as SyncLockWrappedF
from ._backend._types._lock_wrap import WrappedFunctionLock as WrappedFunctionLock


try:
    from importlib.metadata import version

    __version__ = version('py-cachify')
except ModuleNotFoundError:
    __version__ = f'No version available for {__name__}'
