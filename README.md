# Py-Cachify

<p align="center">
<a href="https://opensource.org/licenses/MIT" target="_blank">
    <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
</a>
<a href="https://badge.fury.io/py/py-cachify" target="_blank">
    <img src="https://badge.fury.io/py/py-cachify.svg" alt="PyPI version">
</a>
<a href="https://py-cachify.readthedocs.io/en/latest/?badge=latest" target="_blank">
    <img src="https://readthedocs.org/projects/py-cachify/badge/?version=latest" alt="Documentation Status">
</a>
</p>
<p align="center">
<a href="https://github.com/EzyGang/py-cachify/actions/workflows/checks.yml/badge.svg" target="_blank">
    <img src="https://github.com/EzyGang/py-cachify/actions/workflows/checks.yml/badge.svg" alt="Pre-build checks and Tests">
</a>
<a href="https://github.com/EzyGang/py-cachify/actions/workflows/integration-tests.yml/badge.svg" target="_blank">
    <img src="https://github.com/EzyGang/py-cachify/actions/workflows/integration-tests.yml/badge.svg" alt="Tests Status">
</a>
<a href="https://coveralls.io/github/EzyGang/py-cachify?branch=main" target="_blank">
    <img src="https://coveralls.io/repos/github/EzyGang/py-cachify/badge.png?branch=main" alt="Coverage Status">
</a>
<a href="https://sonarcloud.io/summary/new_code?id=EzyGang_py-cachify" target="_blank">
    <img src="https://sonarcloud.io/api/project_badges/measure?project=EzyGang_py-cachify&metric=reliability_rating" alt="Reliability Rating">
</a>
</p>

---

**Documentation**: <a href="https://py-cachify.readthedocs.io/latest/" target="_blank">https://py-cachify.readthedocs.io/latest/</a>

**Source Code**: <a href="https://github.com/EzyGang/py-cachify" target="_blank">https://github.com/EzyGang/py-cachify</a>

---

py-cachify is a small library that provides useful cache-based utilities (caching, distributed locks) that are
enhanced versions of those provided by similar packages.

py-cachify works well in both sync and async environments, has 100% test coverage, is fully type annotated,
is backend agnostic (you can provide your own client as long as it matches the signature), and supports Python from 3.8 and upward.

It offers distributed (cache-based) locks and decorators to lock function executions,
and also caching utilities and decorators for storing results in the cache.

The key features are:

* **Intuitive to write**: Great editor support. When applying decorators your IDE will still be able to autocomplete and highlight inline errors for applied functions.
* **Fully type annotated**: You don't have to constantly look into the docs. Everything is type annotated and easy to understand out of the box.
* **Short**: Minimize code duplication. Add just one line of code to implement a cache or lock on your function.
* **Start simple**: The simplest example adds only a couple of lines of code: initialize a library and use the needed utility.
* **Backend agnostic**: Use whatever cache-backend you want to use. Py-Cachify is not forcing you into anything.
* **Test coverage**: Has 100% test coverage and supports Python 3.8+

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
By default, it will use an in-memory cache.


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
```

Read more about `@cached` [here](https://py-cachify.readthedocs.io/latest/reference/cached/).

### Locking

Locking through context manager:

```python
from py_cachify import lock

# Use it within an asynchronous context
async with lock('resource_key'):
    # Your critical section here
    print('Critical section code')


# Use it within a synchronous context
with lock('resource_key'):
    # Your critical section here
    print('Critical section code')
```

Locking via decorator:

```python

from py_cachify import lock

@lock(key='critical_function_lock-{arg}', nowait=False, timeout=10)
def critical_function(arg: int) -> None:
    # critical code
```

Read more about `lock` [here](https://py-cachify.readthedocs.io/latest/reference/lock/).

For a more detailed tutorial visit [Tutorial](https://py-cachify.readthedocs.io/latest/tutorial/) or [full API reference](https://py-cachify.readthedocs.io/latest/reference).

## Contributing

If you'd like to contribute, please first discuss the changes using Issues, and then don't hesitate to shoot a PR which will be reviewed shortly.

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/EzyGang/py-cachify/blob/main/LICENSE) file for details.
