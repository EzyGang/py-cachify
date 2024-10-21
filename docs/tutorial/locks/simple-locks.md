# Lock - Getting Started with Locks in Py-Cachify

## Starting slow

Let's write the following code:

```python
import asyncio

from py_cachify import init_cachify, lock


# here we initializing a py-cachify to use an in-memory cache, as usual
init_cachify()


async def main() -> None:

    # this is a sync lock
    with lock(key='cool-sync-lock'):
        print('this code is locked')
    
    # and this is an async lock
    async with lock(key='cool-async-lock'):
        print('this code is locked, but using async cache')


if __name__ == '__main__':
    asyncio.run(main())
```

If we run the example:

<!-- termynal -->
```bash
# Run our example
$ python main.py

# The output will be
this code is locked
this code is locked, but using async cache
```

As you can see, we just had both of our prints printed out without any exceptions.

Notice how we utilized both sync and async context managers from a single lock object,
by doing this `py-cachify` allows you to use the `lock` in any environment your application might work in (sync or async),
without splitting those into for example `async_lock` and `sync_lock`.

From now on we will do everything in async, but you can also follow the tutorial writing the same sync code :)

## Let's break it


Now, we'll adjust our previous example:

```python
import asyncio

from py_cachify import init_cachify, lock


# here we initializing a py-cachify to use an in-memory cache, as usual
init_cachify()


async def main() -> None:
    
    # and this is an async lock
    async with lock(key='cool-async-lock'):
        print('this code is locked and will be executed')
        
        async with lock(key='cool-async-lock'):
            print('we are attempting to acquire a new lock with the same key and will not make it to this print')


if __name__ == '__main__':
    asyncio.run(main())
```

After running this piece:

<!-- termynal -->
```bash
$ python main.py
# The output will be
poetry run python main.py
this code is locked and will be executed
cool-async-lock is already locked!  # this is a .warning from log

# traceback of an error
Traceback (most recent call last):
  ...
  File "/py_cachify/backend/lock.py", line 199, in _raise_if_cached
    raise CachifyLockError(msg)
py_cachify.backend.exceptions.CachifyLockError: cool-async-lock is already locked!
```

And as expected, at the line where we are trying to acquire a lock with the same name - we get an error that this key is already locked.

This was a showcase of the very basic piece of locks (or mutexes) and everything else everywhere is built on top of this basic concept.

## What's next

We will see what parameters does `lock` object has and what cases can we cover with the help of those.