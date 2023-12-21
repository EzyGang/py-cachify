# Py-Cachify

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://github.com/EzyGang/py-cachify/actions/workflows/checks.yml/badge.svg)]()
[![Coverage Status](https://coveralls.io/repos/github/EzyGang/py-cachify/badge.png?branch=main)](https://coveralls.io/github/EzyGang/py-cachify?branch=main)

py-cachify is a library that provides small but useful cache utilities.

Some parts were heavily inspired by [douglasfarinelli's python-cachelock](https://github.com/douglasfarinelli/python-cachelock) lib,
which is sadly no longer maintained.

py-cachify works well in both sync and async environments, has 100% test coverage, and supports Python from 3.8 and upward.

## Table of Contents

- [Documentation](#documentation)
- [Installation](#installation)
- [Examples](#examples)
- [Contributing](#contributing)
- [License](#license)

## Documentation

Detailed documentation can be found at .

## Installation
To install:
```
pip install py-cachify

# or if using poetry
poetry add py-cachify
```

## Examples

To start working with it, you'll have to initialize it using `init_cachify`:
```
from py_cachify import init_cachify

init_cachify()
```
By default, it will use an in-memory cache.

If you want to use Redis:
```
from py_cachify import init_cachify
from redis.asyncio import from_url as async_from_url
from redis import from_url as from_url

init_cachify(sync_client=from_url(redis_url), async_clien=async_from_url(async_redis_client))
```
Normally you wouldn't have to use both sync and async clients since an application usually works in a single mode i.e. sync/async.

For more detailed documentation and examples please visit .

## Contributing

If you'd like to contribute, please first discuss the changes using Issues, and then don't hesitate to shoot a PR which will be reviewed shortly.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
