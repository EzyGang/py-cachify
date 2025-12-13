# Examples

Here's a small list of possible usage applications.

Remember to make sure to call `init_cachify` (for global decorators) or create a local instance with `init_cachify(is_global=False)` when you need an isolated cache.

## ///cached/// decorator (global usage)

```python
from py_cachify import cached, init_cachify

# Configure global Cachify instance for top-level decorators
init_cachify()

@cached(key='example_key', ttl=60)
def expensive_function(x: int) -> int:
    print('Executing expensive operation...')
    return x ** 2


@cached(key='example_async_function-{arg_a}-{arg_b}')
async def async_expensive_function(arg_a: int, arg_b: int) -> int:
    print('Executing async expensive operation...')
    return arg_a + arg_b

# Reset the cache for a specific call
expensive_function.reset(10)
```

## ///cached/// with default_cache_ttl

```python
from py_cachify import cached, init_cachify

# Configure a global default TTL of 300 seconds
init_cachify(default_cache_ttl=300)

# Uses default_cache_ttl=300 because ttl is omitted
@cached(key='profile-{user_id}')
def get_profile(user_id: int) -> dict:
    ...

# Never expires, even though default_cache_ttl is set
@cached(key='feature-flags', ttl=None)
def get_feature_flags() -> dict:
    ...
```

## ///cached/// with instance-based usage

```python
from py_cachify import init_cachify

# Create a dedicated instance that does not affect the global client
local_cachify = init_cachify(is_global=False, prefix='LOCAL-', default_cache_ttl=10)

@local_cachify.cached(key='local-expensive-{x}')
def local_expensive_function(x: int) -> int:
    print('Executing local expensive operation...')
    return x ** 3
```

## ///cached/// multi-layer usage

```python
from py_cachify import cached, init_cachify

# Global initialization (used by the top-level @cached)
init_cachify(default_cache_ttl=60)

# Local instance that adds a shorter TTL on top of the global cache
local_cachify = init_cachify(is_global=False, prefix='LOCAL-', default_cache_ttl=5)

@local_cachify.cached(key='local-expensive-{x}')      # outer, short-lived layer
@cached(key='global-expensive-{x}')                   # inner, longer-lived layer
def expensive(x: int) -> int:
    print('Executing expensive operation...')
    return x * 10

# Reset both layers for a given argument
expensive.reset(42)
```


## ///cached/// decorator with encoder/decoder
```python
from py_cachify import cached


def encoder(val: 'UnpicklableClass') -> dict:
    return {'arg1': val.arg1, 'arg2': val.arg2}


def decoder(val: dict) -> 'UnpicklableClass':
    return UnpicklableClass(**val)


@cached(key='create_unpicklable_class-{arg1}-{arg2}', enc_dec=(encoder, decoder))
def create_unpicklable_class(arg1: str, arg2: str) -> 'UnpicklableClass':
    return UnpicklableClass(arg1=arg1, arg2=arg2)
```

## ///lock/// as a context manager

```python
from py_cachify import init_cachify, lock

# Ensure global client is initialized for locks
init_cachify()

# Use it within an asynchronous context
async with lock('resource_key'):
    # Your critical section here
    print('Critical section code')


# Use it within a synchronous context
with lock('resource_key'):
    # Your critical section here
    print('Critical section code')
```

## ///lock/// as a decorator

```python
from py_cachify import init_cachify, lock

# Initialize once at app startup
init_cachify()

@lock(key='critical_function_lock-{arg}', nowait=False, timeout=10)
def critical_function(arg: int) -> None:
    # critical code
    ...
```

## ///once/// decorator

```python
from datetime import date
from time import sleep

from py_cachify import once


@once(key='long_running_function')
async def long_running_function() -> str:
    # Executing long-running operation...
    ...


@once(key='create-transactions-{for_date.year}-{for_date.month}-{for_date.day}')
def create_transactions(for_date: date) -> None:
    # Creating...
    ...


@once(key='another_long_running_task', return_on_locked='In progress')
def another_long_running_function() -> str:
    sleep(10)
    return 'Completed'


@once(key='exception_if_more_than_one_is_running', raise_on_locked=True)
def one_more_long_running_function() -> None:
    # Executing
    ...
```
