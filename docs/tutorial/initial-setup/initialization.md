# Initializing a library

## Description

First, to start working with the library, you will have to initialize it by using provided `init_cachify` function:
```python
from py_cachify import init_cachify

init_cachify()
```
By default, it will use an **in-memory** cache.

<details>
<summary>⚠ In-memory cache details</summary>
<p>
The in-memory cache is not suitable to use in any sort of serious applications,
since every python process will use it's own memory and caching/locking won't work as expected.

So be carefull using it and make sure it is suitable for your particular use case,
for example some simple script will probably be OK utilizing an in-memory cache, but a FastAPI app won't work as expected.
</p>
</details>

If you want to use Redis:
```python
from py_cachify import init_cachify
from redis.asyncio import from_url as async_from_url
from redis import from_url

init_cachify(sync_client=from_url(redis_url), async_client=async_from_url(async_redis_client))
```
Normally you wouldn't have to use both sync and async clients since an application usually works in a single mode i.e. sync/async.

Once initialized you can use everything that the library provides straight up without being worried about managing the cache yourself.

❗ If you forgot to call `init_cachify` the `CachifyInitError` will be raised during runtime.


## Additional info on initialization

The clients are not the only thing that this function accepts, so make sure to check out the **[Detailed initialization reference](../../reference/init.md)**.

## What's next

Next we'll learn about the `@cached()` decorator and how to use it.
