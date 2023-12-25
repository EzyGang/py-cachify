# `once` decorator

The once decorator is designed to ensure that a function is executed only once at a time for a given key, 
preventing multiple concurrent executions for a given key. It utilizes a lock mechanism to control access to the 
function based on the provided key.

It detects the type of function that it is being applied to automatically using a compatible cache client for it (sync or async).

### Parameters

| Param name         | Param type       | Description                                                                                                                                                                      | Default |
|--------------------|------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|
| `key`              | `str`            | The unique identifier used to determine whether the function has already been executed. The key can be a string containing placeholders to be formatted with function arguments. |         |
| `raise_on_locked`  | `bool, optional` | If `True`, raises a `CachifyLockError` when the function is already locked.                                                                                                      | `False` |
| `return_on_locked` | `Any, optional`  | If provided and the function is already locked, return this value instead of executing the function.                                                                             | `None`  |


### Usage

```python
from datetime import date
from time import sleep
from py_cachify import once
from .celery import celery


@once(key='long_running_function')
async def long_running_function() -> str:
    # Executing long-running operation...
    pass


@celery.task
@once(key='create-transactions-{for_date.year}-{for_date.month}-{for_date.day}')
def create_transactions(for_date: date) -> None:
    # Creating...
    pass


@once(key='another_long_running_task', return_on_locked='In progress')
def another_long_running_function() -> str:
    sleep(10)
    return 'Completed'


@once(key='exception_if_more_than_one_is_running', raise_on_locked=True)
def one_more_long_running_function() -> None:
    # Executing
    pass
```

In the first example, the async `long_running_function` is being locked with a key in the cache that matches the function name, 
which allows you to not worry about accidentally launching the same operation concurrently as it will just silently exit without executing any logic. 

In the second example, the key is being constructed dynamically from a function 
arguments making it prevent concurrent execution only for the same parameters, but allowing the execution for a different date.

In the third example, if the function is being called while the first one has not finished its execution, 
it will immediately return `'In progress'` instead of `None` by default.

In the fourth example, if the function is being called while the first one has not finished its execution, 
it will raise `CachifyLockError`.
