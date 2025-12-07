# API Reference for ///@once()/// Decorator

## Overview

The `once` decorator ensures that a decorated function can only be called once at a time based on a specified key.
It can be applied to both synchronous and asynchronous functions, facilitating locking mechanisms to prevent concurrent executions.

There are two main ways to use `once` with py-cachify:

- Via the **global** `once` decorator exported from `py_cachify`, which relies on a globally initialized client.
- Via **instance-based** `once` decorators obtained from a `Cachify` object created by `init_cachify(is_global=False)`.

---

## Function: ///once()///

### Description
The `once` decorator takes a key to manage function calls,
ensuring that only one invocation of the wrapped function occurs at a time.
If the function is called while it is still locked, it can either raise an exception or return a predefined value depending on the parameters.

### Parameters

| Parameter            | Type                            | Description                                                                                                   |
|---------------------|---------------------------------|---------------------------------------------------------------------------------------------------------------|
| `key`               | `str`                           | The key used to identify the lock for the function.                                                           |
| `raise_on_locked`   | `bool`, optional                | If `True`, raises an exception (`CachifyLockError`) when the function call is already locked. Defaults to `False`. |
| `return_on_locked`  | `Any`, optional                 | The value to return when the function is already locked. Defaults to `None`.                                  |

### Returns
- `WrappedFunctionLock`: A wrapped function (either synchronous or asynchronous) with additional methods attached for lock management, specifically:
      - `is_locked(*args, **kwargs)`: Method to check if the function is currently locked.
      - `release(*args, **kwargs)`: Method to release the lock.

### Method Behavior
- **If the wrapped function is called while locked**:
      - If `raise_on_locked` is `True`: A `CachifyLockError` exception is raised.
      - If `return_on_locked` is specified: The decorator returns the specified value instead of invoking the function.

### Usage Example

```python
from py_cachify import once

@once('my_function_lock', raise_on_locked=True)
def my_function():
    # Critical section of code goes here
    return 'Function executed'

@once('my_async_function_lock-{arg}', return_on_locked='Function already running')
async def my_async_function(arg: str):
    # Critical section of async code goes here
    return 'Async function executed'
```

### Instance-based Usage

If you need multiple, independent "once" semantics (for example, per module or subsystem), you can create dedicated `Cachify` instances via `init_cachify(is_global=False)` and use their `once` method instead of the global decorator:

```python
from py_cachify import init_cachify

# Create a dedicated instance that does not affect the global client
local_cachify = init_cachify(is_global=False, prefix='LOCAL-')

@local_cachify.once('local-once-{task_id}')
def local_task(task_id: str) -> None:
    # This function will be guarded by the local instance
    ...
```

- Global `@once(...)` uses the client configured by a global `init_cachify()` call.
- `@local_cachify.once(...)` uses a client that is completely independent from the global one.

### Releasing the once lock or checking if it is locked

```python

await my_async_function.is_locked(arg='arg-value')

await my_async_function.release(arg='arg-value')
```

The same pattern applies to instance-based usage:

```python
await local_task.is_locked(task_id='42')
await local_task.release(task_id='42')
```

### Note
- If py-cachify is not initialized through `init_cachify` with `is_global=True`, using the global `once` decorator will raise a `CachifyInitError`.
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