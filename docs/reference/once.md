# API Reference for ///@once()/// Decorator

## Overview

The `once` decorator ensures that a decorated function can only be called once at a time based on a specified key.
It can be applied to both synchronous and asynchronous functions, facilitating locking mechanisms to prevent concurrent executions.

---

## Function: `once()`

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
- `SyncOrAsyncRelease`: A wrapped function (either synchronous or asynchronous) with additional methods attached for lock management, specifically:
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

@once('my_async_function_lock', return_on_locked='Function already running')
async def my_async_function():
    # Critical section of async code goes here
    return 'Async function executed'
```

### Note
- If py-cachify is not initialized through `init_cachify`, a `CachifyInitError` will be raised.
