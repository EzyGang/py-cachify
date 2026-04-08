# Pool - Getting Started with Pools in Py-Cachify

## Starting Simple

Let us write a basic example using a pool as a context manager:

```python
import asyncio

from py_cachify import init_cachify, pool


# Initialize py-cachify
init_cachify()


async def main() -> None:
    # Create a pool that allows up to 2 concurrent executions
    worker_pool = pool(key='worker-pool', max_size=2)

    async with worker_pool:
        print('First worker executing')
        await asyncio.sleep(0.1)

    async with worker_pool:
        print('Second worker executing')
        await asyncio.sleep(0.1)

    print('All workers complete')


if __name__ == '__main__':
    asyncio.run(main())
```

Running this:

<!-- termynal -->
```bash
$ python main.py

# The output
First worker executing
Second worker executing
All workers complete
```

The code executes sequentially here because we await each context manager. The pool tracks that at most one slot is used at any moment.

## Multiple Concurrent Executions

Now let us see what happens when we exceed the pool capacity:

```python
import asyncio

from py_cachify import init_cachify, pool, CachifyPoolFullError


init_cachify()


async def worker(name: str, pool_instance) -> None:
    try:
        async with pool_instance:
            print(f'Worker {name} started')
            await asyncio.sleep(1)
            print(f'Worker {name} finished')
    except CachifyPoolFullError:
        print(f'Worker {name} could not acquire slot - pool full')


async def main() -> None:
    worker_pool = pool(key='concurrent-pool', max_size=2)

    # Start 4 workers simultaneously against a pool of size 2
    tasks = [
        asyncio.create_task(worker(f'W{i}', worker_pool))
        for i in range(4)
    ]
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.run(main())
```

<!-- termynal -->
```bash
$ python main.py

# The output
Worker W0 started
Worker W1 started
Worker W2 could not acquire slot - pool full
Worker W3 could not acquire slot - pool full
Worker W0 finished
Worker W1 finished
```

Only two workers enter the pool. The others fail immediately because the default behavior raises `CachifyPoolFullError` when the pool is full and `raise_on_full` is not set. We will see how to customize this in the decorator section.

## Synchronous Usage

Pools work in synchronous code too:

```python
from py_cachify import init_cachify, pool


init_cachify()


with pool(key='sync-pool', max_size=3):
    print('Synchronous work in pool')
```

The same slot management applies regardless of sync or async context.

## What's Next

We will explore pool parameters including `max_size` and `slot_exp` (slot TTL).
