<p align="center">
<a href="https://py-cachify.readthedocs.io/latest/" target="_blank">
    <img src="https://i.imgur.com/kObXEhW.png" alt="header">
</a>
<a href="https://opensource.org/licenses/MIT" target="_blank">
    <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
</a>
<a href="https://badge.fury.io/py/py-cachify" target="_blank">
    <img src="https://badge.fury.io/py/py-cachify.svg" alt="PyPI version">
</a>
<a href="https://pypi.org/project/py-cachify/" target="_blank">
    <img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dm/py-cachify">
</a>
<a href="https://pypi.org/project/py-cachify/" target="_blank">
    <img src="https://img.shields.io/pypi/pyversions/py-cachify.svg?color=%2334D058" alt="supported versions">
</a>
<a href="https://coveralls.io/github/EzyGang/py-cachify?branch=main" target="_blank">
    <img src="https://coveralls.io/repos/github/EzyGang/py-cachify/badge.png?branch=main" alt="Coverage Status">
</a>
</p>
<p align="center">
<a href="https://github.com/EzyGang/py-cachify/actions/workflows/checks.yml/badge.svg" target="_blank">
    <img src="https://github.com/EzyGang/py-cachify/actions/workflows/checks.yml/badge.svg" alt="Pre-build checks and Tests">
</a>
<a href="https://github.com/EzyGang/py-cachify/actions/workflows/integration-tests.yml/badge.svg" target="_blank">
    <img src="https://github.com/EzyGang/py-cachify/actions/workflows/integration-tests.yml/badge.svg" alt="Tests Status">
</a>
<a href="https://py-cachify.readthedocs.io/en/latest/?badge=latest" target="_blank">
    <img src="https://readthedocs.org/projects/py-cachify/badge/?version=latest" alt="Documentation Status">
</a>
<a href="https://sonarcloud.io/summary/new_code?id=EzyGang_py-cachify" target="_blank">
    <img src="https://sonarcloud.io/api/project_badges/measure?project=EzyGang_py-cachify&metric=reliability_rating" alt="Reliability Rating">
</a>
</p>

---

**Documentation**: <a href="https://py-cachify.readthedocs.io/latest/" target="_blank">https://py-cachify.readthedocs.io/latest/</a>

**Source Code**: <a href="https://github.com/EzyGang/py-cachify" target="_blank">https://github.com/EzyGang/py-cachify</a>

**FastAPI Integration Guide**: <a href="https://github.com/EzyGang/py-cachify-fastapi-demo" target="_blank">Repo</a>

---

**Py-Cachify** is a robust library tailored for developers looking to enhance their Python applications with elegant caching and locking mechanisms.
Whether you're building synchronous or asynchronous applications, Py-Cachify has you covered!
It acts as a thin, backend-agnostic wrapper over your favorite cache client, letting you focus on business logic instead of juggling low-level get/set calls.


## Key Features:
- **Flexible Caching**: Effortlessly cache your function results, dramatically reducing execution time for expensive computations and I/O-bound tasks.
Utilize customizable keys and time-to-live (TTL) parameters.

- **Distributed Locks**: Ensure safe concurrent operation of functions with distributed locks. 
Prevent race conditions and manage shared resources effectively across both sync and async contexts.

- **Backend Agnostic**: Easily integrate with different cache backends. 
Choose between in-memory, Redis, DragonflyDB, or any custom backend that adheres to the provided client interfaces.

- **Decorators for Ease**: Use intuitive decorators like `@cached()` and `@lock()` to wrap your functions, 
maintain clean code, and benefit from automatic cache management.

- **Type Safety & Documentation**: Fully type-annotated for enhanced IDE support and readability, 
featuring comprehensive documentation and examples to guide you through various use cases.

- **Production Ready**: With 100% test coverage and usage in multiple commercial projects, 
Py-Cachify is trusted for production environments, ensuring reliability and stability for your applications.

---

## Table of Contents

- [Installation](#installation)
- [How to use](#how-to-use)
- [Basic examples](#basic-examples)
- [Contributing](#contributing)
- [License](#license)

## Installation

<!-- termynal -->
```bash
$ pip install py-cachify

---> 100%
Successfully installed py-cachify
```

## How to use

You can read more in-depth tutorials [here](https://py-cachify.readthedocs.io/latest/tutorial/).

First, to start working with the library, you will have to initialize it by using the provided `init_cachify` function:
```python
from py_cachify import init_cachify

init_cachify()
```

This call:

- Configures the **global** client used by the top-level decorators: `cached`, `lock`, and `once`.
- Returns a `Cachify` instance, but you don't have to use it if you only work with the global decorators.
- Uses an in-memory cache by default (both for sync and async usage).


If you want to use Redis:
```python
from py_cachify import init_cachify
from redis.asyncio import from_url as async_from_url
from redis import from_url


# Example: configure global cachify with Redis for both sync and async flows
init_cachify(
    sync_client=from_url(redis_url),
    async_client=async_from_url(redis_url),
)
```
Normally you wouldn't have to use both sync and async clients since an application usually works in a single mode i.e. sync/async. You can pass only `sync_client` **or** only `async_client` if that matches your usage.


Once initialized you can use everything that the library provides straight up without being worried about managing the cache yourself.


❗ If you forgot to call `init_cachify` with `is_global=True` at least once, using the global decorators (`cached`, `lock`, `once`) will raise `CachifyInitError` during runtime.

You can also create **dedicated instances** without touching the global client:

```python
from py_cachify import init_cachify

# Global initialization for the top-level decorators
init_cachify()

# Local instance that does NOT touch the global client
local_cache = init_cachify(is_global=False, prefix='LOCAL-')

@local_cache.cached(key='local-{x}')
def compute_local(x: int) -> int:
    return x * 2
```


## Basic examples


### Caching


Caching by using `@cached` decorator utilizing the flexibility of a dynamic key:


```python
# Cache the result of the following function with dynamic key
@cached(key='sum_two-{a}-{b}')
async def sum_two(a: int, b: int) -> int:
    # Let's put print here to see what was the function called with
    print(f'Called with {a} {b}')
    return a + b
    
    
# Reset the cache for the call with arguments a=1, b=2
await sub_two.reset(a=1, b=2)
```

### Multi-layer Usage

It is possible to layer caches by stacking `cached` decorators (for example, a global cache inside a local instance cache).

```python
from py_cachify import cached, init_cachify

# Global initialization for the top-level decorators
init_cachify()

# Local instance with a shorter TTL that wraps the global one
local = init_cachify(is_global=False, prefix='LOCAL-')

@local.cached(key='local-expensive-{x}', ttl=5)
@cached(key='expensive-{x}', ttl=60)
def expensive(x: int) -> int:
    return x * 10
```

Read more about `@cached` [here](https://py-cachify.readthedocs.io/latest/reference/cached/).

### Locking

Locking through context manager:

```python
from py_cachify import lock


async_lock = lock('resource_key')
# Use it within an asynchronous context
async with async_lock:
    # Your critical section here
    print('Critical section code')

# Check if it's locked
await async_lock.is_alocked()

# Forcefully release
await async_lock.arelease()

# Use it within a synchronous context
with lock('resource_key'):
    # Your critical section here
    print('Critical section code')
```

Locking via decorator:

```python

from py_cachify import lock

@lock(key='critical_function_lock-{arg}', nowait=False, timeout=10)
async def critical_function(arg: int) -> None:
    # critical code
    

# Check if it's locked for arg=5
await critical_function.is_locked(arg=5)

# Forcefully release for arg=5
await critical_function.release(arg=5)
```

Read more about `lock` [here](https://py-cachify.readthedocs.io/latest/reference/lock/).

For a more detailed tutorial visit [Tutorial](https://py-cachify.readthedocs.io/latest/tutorial/) or [full API reference](https://py-cachify.readthedocs.io/latest/reference).

## Contributing

If you'd like to contribute, please first discuss the changes using Issues, and then don't hesitate to shoot a PR which will be reviewed shortly.

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/EzyGang/py-cachify/blob/main/LICENSE) file for details.
