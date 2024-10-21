# API Reference for ///init_cachify()///

## Overview

The `init_cachify` function initializes the `Cachify` library, setting up the necessary synchronous and asynchronous clients along with configuration options.
This function must be called before utilizing the caching or locking functionality provided by the library.

## Function: ///init_cachify///

### Description
`init_cachify` initializes the core `Cachify` instance with specified caching clients, expiration settings, and key prefixes.
The function sets up the environment required for caching operations, ensuring it operates correctly across both synchronous and asynchronous contexts.

### Parameters

| Parameter                            | Type                                | Description                                                                                                        |
|--------------------------------------|-------------------------------------|--------------------------------------------------------------------------------------------------------------------|
| `sync_client`                        | `Union[SyncClient, MemoryCache]`   | The synchronous client used for caching operations. Defaults to a new instance of `MemoryCache`.                   |
| `async_client`                       | `Union[AsyncClient, AsyncWrapper]` | The asynchronous client used for caching operations. Defaults to a new instance of `AsyncWrapper` wrapping a `MemoryCache`. |
| `default_lock_expiration`           | `Optional[int]`, optional           | Default expiration time (in seconds) for locks. Defaults to `30`.                                                |
| `prefix`                             | `str`, optional                     | String prefix to prepend to all keys used in caching. Defaults to `'PYC-'`.                                       |

### Returns
- This function does not return a value. It configures the caching environment for subsequent use.

### Usage Example

```python
from py_cachify import init_cachify

# Initialize the Cachify library
init_cachify(
    sync_client=YourSyncClient(),   # Synchronous client instance
    async_client=YourAsyncClient(),  # Asynchronous client instance
    default_lock_expiration=60,      # Set default lock expiration to 60 seconds
    prefix='MY_CACHE_'                # Set custom prefix for keys
)
```

### Custom Clients

The py-cachify library supports Redis synchronous and asynchronous clients out of the box.
However, if you want to use other caching backends (such as Memcached, database-based, or file-based solutions),
you can create custom clients by complying with the `SyncClient` and `AsyncClient` protocols.

These custom implementations should match the following method signatures:

- For **synchronous clients (SyncClient)**:
    - `get(name: str) -> Optional[Any]`
    - `set(name: str, value: Any, ex: Optional[int] = None) -> Any`
    - `delete(*names: str) -> Any`

- For **asynchronous clients (AsyncClient)**:
    - `get(name: str) -> Awaitable[Optional[Any]]`
    - `set(name: str, value: Any, ex: Optional[int] = None) -> Awaitable[Any]`
    - `delete(*names: str) -> Awaitable[Any]`

By adhering to these protocols, you can integrate your custom backend while maintaining compatibility with the py-cachify caching mechanisms.

#### Example Custom Client Integration

```python
class CustomSyncClient:
    def get(self, name: str) -> Optional[Any]:
        # Implementation for getting a value from the cache
        pass

    def set(self, name: str, value: Any, ex: Optional[int] = None) -> Any:
        # Implementation for setting a value in the cache
        pass

    def delete(self, *names: str) -> Any:
        # Implementation for deleting keys from the cache
        pass

class CustomAsyncClient:
    async def get(self, name: str) -> Optional[Any]:
        # Implementation for asynchronously getting a value from the cache
        pass

    async def set(self, name: str, value: Any, ex: Optional[int] = None) -> Any:
        # Implementation for asynchronously setting a value in the cache
        pass

    async def delete(self, *names: str) -> Any:
        # Implementation for asynchronously deleting keys from the cache
        pass

# Initialize Cachify with custom clients
init_cachify(
    sync_client=CustomSyncClient(),       # Your custom synchronous client
    async_client=CustomAsyncClient(),      # Your custom asynchronous client
)
```

This flexibility allows you to utilize a caching backend of your choice while leveraging the `Cachify` library's capabilities effectively.

### Notes
- It is crucial to call `init_cachify` before performing any caching or locking operations.
Failing to do so will result in a `CachifyInitError` when attempting to access caching features.
- The `sync_client` and `async_client` parameters should comply with the `SyncClient` and `AsyncClient` protocols, respectively.
