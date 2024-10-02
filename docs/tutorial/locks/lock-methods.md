# Lock - Lock Methods in Py-Cachify

Parameters are not the only things that locks in py-cachify have.
There are also a couple of handy methods.

## ///is_locked()/// and //is_alocked()///

The method `is_locked()` checks if the lock associated with the specified key is currently held.
The method `is_alocked()` is the asynchronous counterpart of `is_locked()`. It checks if the lock is held, but it is designed to be used in an async context.

Both methods return a `bool`.

## Example for ///is_alocked()///

Let's modify the previous example a little bit:

```python
import asyncio

from py_cachify import init_cachify, lock


# Initialize py-cachify to use in-memory cache
init_cachify()


async def main() -> None:
    example_lock = lock(key='example-lock', nowait=False, timeout=4, exp=2)

    async with example_lock:
        print('This code is executing under a lock with a timeout of 4 seconds and expiration set to 2 seconds')
        while await example_lock.is_alocked():
            print('Lock is still active! Waiting...')
            await asyncio.sleep(1)
        
        print('Lock has been released')
        async with example_lock:
            print('Acquire the same lock again')

            
if __name__ == '__main__':
    asyncio.run(main())
```

After running the example:

<!-- termynal -->
```bash
$ python main.py

# The output will be
This code is executing under a lock with a timeout of 4 seconds and expiration set to 2 seconds
Lock is still active! Waiting...
Lock is still active! Waiting...
Lock has been released
Acquire the same lock again
```

As you can see we were checking if the lock has been released inside a `while` loop before reacquiring it.

Remember that we are talking about distributed locks, that means that you could check if the lock is being held from another process or even another machine in a real app!


## ///release()/// and ///arelease()///

The method `release()` releases the lock associated with the given key. 
It is called internally when a lock context manager exits.

The method `arelease()` is similar to the `release()` but is used in an asynchronous context.

## Modifying the example

We'll introduce some small changes to the previous code:

```python
import asyncio

from py_cachify import init_cachify, lock


# Initialize py-cachify to use in-memory cache
init_cachify()


async def main() -> None:
    example_lock = lock(key='example-lock', nowait=False, timeout=4, exp=2)

    async with example_lock:
        print('This code is executing under a lock with a timeout of 4 seconds and expiration set to 2 seconds')
        
        await example_lock.arelease()
        
        print(f'Is the lock currently locked: {await example_lock.is_alocked()}')
        async with example_lock:
            print('Acquire the same lock again')

            
if __name__ == '__main__':
    asyncio.run(main())
```

After running the example:

<!-- termynal -->
```bash
$ python main.py

# The output
This code is executing under a lock with a timeout of 4 seconds and expiration set to 2 seconds
Is the lock currently locked: False
Acquire the same lock again
```

This time we forcefully reset the lock instead of relying on our `while` loop to check if it has expired.

## Conclusion

Understanding these methods allows for better management of locks within your applications. 
Depending on your application’s architecture (sync vs. async), you'll choose between the synchronous or asynchronous methods to check lock status or release locks after use. 
This ensures that resources are managed efficiently and concurrently executed code does not produce race conditions or inconsistent data.

## What's next

We'll see how can we use `lock` as a decorator and see the ✨magic✨ that py-cachify does.