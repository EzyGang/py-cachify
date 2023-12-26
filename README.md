# Py-Cachify

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://badge.fury.io/py/py-cachify.svg)](https://badge.fury.io/py/py-cachify)
[![Documentation Status](https://readthedocs.org/projects/py-cachify/badge/?version=latest)](https://py-cachify.readthedocs.io/en/latest/?badge=latest)
[![Build Status](https://github.com/EzyGang/py-cachify/actions/workflows/checks.yml/badge.svg)]()
[![Tests Status](https://github.com/EzyGang/py-cachify/actions/workflows/integration-tests.yml/badge.svg)]()
[![Coverage Status](https://coveralls.io/repos/github/EzyGang/py-cachify/badge.png?branch=main)](https://coveralls.io/github/EzyGang/py-cachify?branch=main)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=EzyGang_py-cachify&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=EzyGang_py-cachify)

py-cachify is a library that provides small but useful cache utilities.

Some parts were heavily inspired by [douglasfarinelli's python-cachelock](https://github.com/douglasfarinelli/python-cachelock) lib,
which is sadly no longer maintained.

py-cachify works well in both sync and async environments, has 100% test coverage, 
is backend agnostic (you can provide your own client as long as it matches the signature), and supports Python from 3.8 and upward.

It offers cache-based locks and decorators for securing function executions and storing their results in the cache.

## Table of Contents

- [Documentation](#documentation)
- [Installation](#installation)
- [Examples](#examples)
- [Contributing](#contributing)
- [License](#license)

## Documentation

Detailed documentation can be found at https://py-cachify.readthedocs.io/en/latest/.

## Installation
To install:
```bash
pip install py-cachify

# or if using poetry
poetry add py-cachify
```

## Examples

To start working with it, you'll have to initialize it using `init_cachify`:
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

If you forgot to call `init_cachify` the `CachifyInitError` will be raised during runtime.
```python
from py_cachify import once


# Make sure there is just one copy of a function running at a time
@once(key='long_running_function')
async def long_running_function() -> str:
    # Executing long-running operation...
    pass
```

For more detailed documentation and examples please visit https://py-cachify.readthedocs.io/en/latest/.

## Contributing

If you'd like to contribute, please first discuss the changes using Issues, and then don't hesitate to shoot a PR which will be reviewed shortly.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
