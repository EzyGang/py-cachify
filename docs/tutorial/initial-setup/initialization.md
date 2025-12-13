# Initializing a library

## Description



First, to start working with the library, you will have to initialize it by using the provided `init_cachify` function for global usage, or create one or more dedicated instances when you need isolated caches:


```python
from py_cachify import init_cachify



# Configure the global Cachify instance used by top-level decorators
init_cachify()
```


By default, the global client uses an **in-memory** cache.


<details>
<summary>⚠ In-memory cache details</summary>
<p>
The in-memory cache is not suitable to use in any sort of serious applications, since every python process will use its own memory, 
and caching/locking won't work as expected. So be careful using it and make sure it is suitable for your particular use case, 
for example, some simple script will probably be OK utilizing an in-memory cache, but a FastAPI app won't work as expected.
</p>
</details>

If you want to use Redis:
```python
from py_cachify import init_cachify
from redis.asyncio import from_url as async_from_url
from redis import from_url


# Example: configure global Cachify with Redis for both sync and async flows
init_cachify(
    sync_client=from_url(redis_url),
    async_client=async_from_url(redis_url),
    default_cache_ttl=300,
)
```
Normally you wouldn't have to use both sync and async clients since an application usually works in a single mode i.e. sync/async. You can pass only `sync_client` **or** only `async_client` if that matches your usage, or both if you want sync and async code paths to share the same backend. The `default_cache_ttl` parameter lets you configure a global default TTL (in seconds) that is used for `@cached` when `ttl` is omitted.


Once the global client is initialized you can use everything that the library provides straight up without being worried about managing the cache yourself.


❗ If you forgot to call `init_cachify` with `is_global=True` at least once, using the global decorators (`cached`, `lock`, `once`) will raise `CachifyInitError` during runtime. Instance-based usage via `init_cachify(is_global=False)` does not depend on this global initialization and can be used independently.


## Additional info on initialization

The clients are not the only thing that this function accepts. You can also configure `default_cache_ttl`, `default_lock_expiration`, prefixes, and whether a particular call should register a global client or return a dedicated instance. Make sure to check out the **[Detailed initialization reference](../../reference/init.md)** for the full list of options and defaulting rules.



## What's next


Next, we'll learn about the `@cached()` decorator and how to use it, including how it interacts with `default_cache_ttl` and how to use it both with the global decorators and with dedicated `Cachify` instances.

