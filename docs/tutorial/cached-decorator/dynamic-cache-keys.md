# Cached - Dynamic cache key arguments

In this tutorial, we will continue from the previous example and customize the key in the decorator.

The full code will look like this:

```python
import asyncio

from py_cachify import init_cachify, cached


# here we are initializing py-cachify to use an in-memory cache
init_cachify()


# notice that we now have {a} and {b} in the cache key
@cached(key='sum_two-{a}-{b}')
async def sum_two(a: int, b: int) -> int:
    # Let's put print here to see what was the function called with
    print(f'Called with {a} {b}')
    return a + b


async def main() -> None:
    # Call the function first time with (5, 5)
    print(f'First call result: {await sum_two(5, 5)}')

    # And we will call it again to make sure it's not called but the result is the same
    print(f'Second call result: {await sum_two(5, 5)}')

    # Now we will call it with different args to make sure the function is indeed called for another set of arguments
    print(f'Third call result: {await sum_two(5, 10)}')


if __name__ == '__main__':
    asyncio.run(main())
```


## Understanding what has changed

As you can see, we now have `{a}` and `{b}` inside our key,
what it allows py-cachify to do is dynamically craft a key for a function the decorator is being applied to.

This way it will cache the result for each set of arguments instead of creating just one key.

Note, that in this current example key `'sum_two-{}-{}'` will have the same effect.
Providing a not named placeholders is supported to allow creating dynamic cache keys even for the functions that accept `*args, **kwargs` as their arguments.

We have also modified our main function to showcase the introduced changes.

## Let's run our code

After running the example:
<!-- termynal -->
```bash
# Run our example
$ python main.py

# The ouput will be
Called with 5 5
First call result: 10
Second call result: 10
Called with 5 10
Third call result: 15

```

As you can see, the function result is being cached based on the arguments provided.

## What's next

In the next chapter we'll learn what other parameters `@cached()` decorator has.
