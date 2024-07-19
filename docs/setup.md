## Installation
To install:
```bash
pip install py-cachify

# or if using poetry
poetry add py-cachify
```

## Initialization (working with in-memory cache or `redis`)

To start working with it, you'll have to initialize it using `init_cachify`:
```python
from py_cachify import init_cachify

init_cachify()
```
By default, it will use an in-memory cache and `prefix='_PYC_'` as a cache key prefix (you can set it to whatever you like if needed)

If you want to use Redis:
```python
from py_cachify import init_cachify
from redis.asyncio import from_url as async_from_url
from redis import from_url

init_cachify(sync_client=from_url(redis_url), async_client=async_from_url(redis_url))
```
Normally you wouldn't have to use both sync and async clients since an application usually works in a single mode i.e. sync/async.

Once initialized you can use everything that the library provides straight up without being worried about managing the cache yourself. 

If you forgot to call `init_cachify` the `CachifyInitError` will be raised during runtime.

See [Examples](examples.md).

## Changing cache key prefix
To change the prefix for each key you can provide `prefix` into the `init_cachify` function. 

It could be useful when you have a single cache instance that is being used by multiple apps to perform cache 
resets for example.

```python
from py_cachify import init_cachify
from redis.asyncio import from_url as async_from_url

init_cachify(prefix='EXAMPLE-', async_client=async_from_url(redis_url))
```

So every cache key cachify creates is going to start with our set prefix, i.e. `EXAMPLE-{rest of the key}`, this way you will have no problems
finding the keys created by this client.

## Working with a different cache backend
If you want to use any other backend cache provider like for example `memcached`, 
you'll probably have to provide a small wrapper around its client to match the `py-cachify`'s signature.

To make it easier you can subclass the provided client's protocols.
```python
from py_cachify import AsyncClient, SyncClient

class YourCoolCacheClient(SyncClient):
    ...
```
