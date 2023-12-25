# Async and Sync lock context managers

## `async_lock` / `lock`

This asynchronous and synchronous context manager functions provide a simple locking mechanism using a cache to ensure 
that a particular resource or operation is not concurrently accessed by multiple tasks.

### Parameters
| Param name | Param type | Description                                                                                                                 |
|------------|------------|-----------------------------------------------------------------------------------------------------------------------------|
| `key`      | `str`      | A unique identifier for the lock. It is used as the key in the cache to determine whether the resource is currently locked. |

### Usage
```python
from py_cachify import async_lock, lock


# Use it within an asynchronous context
async with async_lock('resource_key'):
    # Your critical section here
    print('Critical section code')


# Use it within a synchronous context
with lock('resource_key'):
    # Your critical section here
    print('Critical section code')

```
### Explanation
Those functions internally verify whether the resource is already locked in the cache before proceeding. 
If the resource is not locked, it sets the lock in the cache. After the critical section, it releases the lock.

If the resource is already locked raises a `CachifyLockError`, indicating that the resource is unavailable.
