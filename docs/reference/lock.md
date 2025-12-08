# API Reference for ///lock()///

## Overview

The `lock` module provides a mechanism for managing locking within synchronous and asynchronous contexts. 
The main class, `lock`, combines both synchronous and asynchronous locking operations. 

There are two main ways to use locking with py-cachify:

- Via the **global** `lock` factory exported from `py_cachify`, which relies on a globally initialized client.
- Via **instance-based** locking obtained from a `Cachify` object created by `init_cachify(is_global=False)`.


## Class: ///lock///

### Description
The `lock` class manages locks using a specified key, with options for waiting and expiration. 
It can be used in both synchronous and asynchronous contexts.

### Parameters

| Parameter | Type                            | Description                                                                                       |
|-----------|---------------------------------|---------------------------------------------------------------------------------------------------|
| `key`     | `str`                           | The key used to identify the lock.                                                                |
| `nowait`  | `bool`, optional                | If `True`, do not wait for the lock to be released and raise immediately. Defaults to `True`.                           |
| `timeout` | `Union[int, float]`, optional   | Time in seconds to wait for the lock if `nowait` is `False`. Defaults to `None`.                  |
| `exp`     | `Union[int, None]`, optional    | Expiration time for the lock. Defaults to `UNSET` and falls back to the global setting in cachify.|

### Methods

- `__enter__() -> Self`
    - Acquire a lock for the specified key as a context manager, synchronous.

- `release() -> None`
    - Release the lock that is currently being held, synchronous.

- `is_locked() -> bool`
    - Check if the lock is currently held, synchronous.

- `__aenter__() -> Self`
    - Async version of `__enter__` to acquire a lock as an async context manager.

- `arelease() -> None`
    - Release the lock that is currently held, asynchronously.

- `is_alocked() -> bool`
    - Check if the lock is currently held asynchronously.

- as a `decorator`
    - Decorator to acquire a lock for the wrapped function on call, for both synchronous and asynchronous functions.
    - Attaches the following methods to the wrapped function:
        - `is_locked(*args, **kwargs)`: Check if the function is currently locked.
        - `release(*args, **kwargs)`: Release the lock associated with the function.

## Error Handling

- **`CachifyLockError`**: Raised when an operation on a lock is invalid or a lock cannot be acquired.

## Usage Example

```python
from py_cachify import lock

@lock('my_lock_key-{arg}', nowait=True)
def my_function(arg: str) -> None:
    # Critical section of code goes here
    pass
    
    
with lock('my_lock_key'):
    # Critical section of code goes here
    pass

async with lock('my_async_lock_key'):
    # Critical section of async code goes here
    pass

```


By using the `lock` class, you'll ensure that your function calls are properly synchronized, preventing race conditions in shared resources.

### Instance-based usage

If you need multiple, independent locking backends (for example, per module or subsystem), you can create dedicated `Cachify` instances via `init_cachify(is_global=False)` and use their `lock` method instead of the global factory:

```python
from py_cachify import init_cachify

# Create a dedicated instance that does not affect the global client
local_cachify = init_cachify(is_global=False, prefix='LOCAL-')

local_lock = local_cachify.lock(key='local-lock-{name}')

with local_lock:
    # Critical section protected by the local instance
    ...
```

- Global `lock(...)` uses the client configured by a global `init_cachify()` call.
- `local_cachify.lock(...)` uses a client that is completely independent from the global one.


### Releasing the Lock or checking whether it's locked or not
```python
my_function.is_locked(arg='arg-value')  # returns bool

my_function.release(arg='arg-value')  # forcefully releases the lock
```

### Note


- If py-cachify is not initialized through `init_cachify` with `is_global=True`, using the global `lock` factory or decorators will raise a `CachifyInitError`.
- `Cachify` instances created with `is_global=False` do not depend on global initialization and can be used independently.


### Type Hints Remark (Decorator only application)

Currently, Python's type hints have limitations in fully capturing a function's 
original signature when transitioning to a protocol-based callable in a decorator, 
particularly for methods (i.e., those that include `self`). 
`ParamSpec` can effectively handle argument and keyword types for functions 
but doesn't translate well to methods within protocols like `WrappedFunctionLock`. 
I'm staying updated on this issue and recommend checking the following resources 
for more insights into ongoing discussions and proposed solutions:

- [Typeshed Pull Request #11662](https://github.com/python/typeshed/pull/11662)
- [Mypy Pull Request #17123](https://github.com/python/mypy/pull/17123)
- [Python Discussion on Allowing Self-Binding for Generic ParamSpec](https://discuss.python.org/t/allow-self-binding-for-generic-paramspec/50948)

Once any developments occur, I will quickly update the source code to incorporate the changes.