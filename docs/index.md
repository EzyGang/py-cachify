# py-cachify

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://badge.fury.io/py/py-cachify.svg)](https://badge.fury.io/py/py-cachify)
[![Coverage Status](https://coveralls.io/repos/github/EzyGang/py-cachify/badge.png?branch=main)](https://coveralls.io/github/EzyGang/py-cachify?branch=main)

[![Homepage](https://github.githubassets.com/favicons/favicon-dark.png)](https://github.com/EzyGang/py-cachify)

py-cachify is a library that provides small but useful cache-based utilities.

Some parts were heavily inspired by [douglasfarinelli's python-cachelock](https://github.com/douglasfarinelli/python-cachelock) lib,
which is sadly no longer maintained.

## Features
* Offers distributed cache-based locks and decorators around them
* Offers convenient decorators to store function results in the cache
* Works well in both sync and async environments
* Fully type annotated
* Has 100% test coverage
* Has integration tests in place for the common scenarios
* Backend agnostic (you can provide your own client as long as it matches the signature)
* Supports Python from 3.8 and upward


## Quick navigation
To help you get started, see [Initial setup](setup.md).

Examples can be found [here](examples.md).

More information about [`cached` decorator](cached-decorator.md), [`once` decorator](once-decorator.md), 
and [locks](locks.md) can be found on linked pages.
