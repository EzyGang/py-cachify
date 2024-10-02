# Lock - Using Lock as a Decorator

## Parameters and Methods

You can also use the `lock` that py-cachify has as a decorator.

It accepts the same parameters as a normal `lock` and also automatically detects which function it is being applied to
(sync or async) and uses the correct wrapper.

## Differences with regular usage

- The first difference (and advantage) is that when using `lock` as a decorator you can create **dynamic** cache keys (same as in `cached` decorator).
- The second one is since the decorator \*knows\* what type of function it is being applied to there is no need to attach both `is_alocked` and `is_locked` to the wrapped function, so it only attaches `is_locked(*args, **kwargs)` that is going to be the same type as the function that was wrapped (i.e. sync or async)

## Examples

Let's write some code that showcases all the methods with default lock params.

```python
import asyncio

from py_cachify import init_cachify, lock, CachifyLockError


# Initialize py-cachify to use in-memory cache
init_cachify()


# Function that is wrapped in a lock and just sleeps for certain amount of time
@lock(key='sleep_for_lock-{arg}', nowait=True)
async def sleep_for(arg: int) -> None:
    await asyncio.sleep(arg)


async def main() -> None:
    # Calling a function with an arg=3
    _ = asyncio.create_task(sleep_for(3))
    await asyncio.sleep(0.1)
    
    # Checking if the arg 3 call is locked (should be locked)
    print(f'Sleep for is locked for argument 3: {await sleep_for.is_locked(3)}')
    # Checking if the arg 4 call is locked (should not be locked)
    print(f'Sleep for is locked for argument 4: {await sleep_for.is_locked(4)}')

    task = asyncio.create_task(sleep_for(5))
    await asyncio.sleep(0.1)
    # Checking if our call with arg=5 is locked
    print(f'Sleep for is locked for argument 5: {await sleep_for.is_locked(5)}')
    # Forcefully release a lock
    await sleep_for.release(5)
    # Doing a second check - shouldn't be locked now
    print(f'Sleep for is locked for argument 5: {await sleep_for.is_locked(5)}')
    await task
    
    # Trying to run 2 tasks with the same argument (and catching the exception)
    try:
        await asyncio.gather(sleep_for(1), sleep_for(1))
    except CachifyLockError as e:
        print(f'Exception: {e}')


if __name__ == '__main__':
    asyncio.run(main())
```

After running the example:
<!-- termynal -->
```bash
$ python main.py

# The output
Sleep for is locked for argument 3: True
Sleep for is locked for argument 4: False
Sleep for is locked for argument 5: True
Sleep for is locked for argument 5: False
sleep_for_lock-1 is already locked!
Exception: sleep_for_lock-1 is already locked!
```

Here we tried to showcase all the flexibility you have when wrapping functions with the `lock`.

## Conslusion

This concludes our tutorial for the `lock` that py-cachify provides.

The full API reference can be found here.