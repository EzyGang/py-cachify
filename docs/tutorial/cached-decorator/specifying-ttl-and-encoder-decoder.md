# Cached - Providing a ttl (time-to-live) and custom encoder/decoder


## Explanation

Sometimes you don't need to cache a function result indefinitely and you need to cache it let's say for a day (a common case for web apps).

Py-Cachify has got you covered and allows for an optional `ttl` param to pass into the decorator.
This value will be passed down to a cache client and usually means how long the set value will live for in seconds.

## Let's see it in action


```python
import asyncio

from py_cachify import init_cachify, cached


# here we are initializing py-cachify to use an in-memory cache
init_cachify()


# notice ttl, that will cache the result for one second
@cached(key='sum_two-{a}-{b}', ttl=1)
async def sum_two(a: int, b: int) -> int:
    # Let's put print here to see what was the function called with
    print(f'Called with {a} {b}')
    return a + b


async def main() -> None:
    # Call the function first time with (5, 5)
    print(f'First call result: {await increment_int_by(5, 5)}')

    # Let's wait for 2 seconds
    await asyncio.sleep(2)

    # And we will call it again to check what will happen
    print(f'Second call result: {await increment_int_by(5, 5)}')


if __name__ == '__main__':
    asyncio.run(main())
```

The only changes we introduced are the removal of the third call, adding the sleep, and providing a `ttl` param.

After running the example:
<!-- termynal -->
```console
// Run our example
$ python main.py

// The ouput will be
Called with 5 5
First call result: 10
Called with 5 5
Second call result: 10

```

As you can see the cache has expired and allowed the function to be called again.

## Encoders/Decoders

`ttl` is not the only param that `@cached()` has available.
There is also an `enc_dec` which accepts a tuple of `(Encoder, Decoder)`,
those being the methods that are going to be applied to the function result on caching and retrieving the cache value.

The required signature is `Callable[[Any], Any]`.
But keep in mind that results should be picklable, py-cachify uses pickle, before passing the value to the cache backend.

<details>
<summary>ℹ Why it was introduced</summary>
<p>
The main reason is sometimes you have to cache something, that is not picklable by default.

Even though the cases are rare, we decided to support it since it doesn't hurt to have it when it's needed :)
</p>
</details>


## Introducing `enc_dec`

Usually provided encoder and decoder are supposed to work in tandem and not change the output value at all
(since the encoder does something, and then the decoder reverts it back). 
But for the sake of our demonstration, we'll break that principle.

We'll introduce the following functions:

```python

# our encoder will multiply the result by 2
def encoder(val: int) -> int:
    return val * 2


# and our decoder will do the multiplication by 3
def decoder(val: int) -> int:
    return val * 3
```

Now, as a result, the final output should be multiplied by 6.

All we have to do now is modify our `@cached()` decorator params to look like this:

```python
@cached(key='sum_two-{a}-{b}', enc_dec=(encoder, decoder))
async def sum_two(a: int, b: int) -> int:
    # Let's put print here to see what was the function called with
    print(f'Called with {a} {b}')
    return a + b
```


<details>
<summary>ℹ Full file preview </summary>
```python
import asyncio

from py_cachify import init_cachify, cached


# here we are initializing py-cachify to use an in-memory cache
init_cachify()


# our encoder will multiply the result by 2
def encoder(val: int) -> int:
    return val * 2


# and our decoder will do the multiplication by 3
def decoder(val: int) -> int:
    return val * 3


# enc_dec is provided
@cached(key='sum_two-{a}-{b}', enc_dec=(encoder, decoder))
async def sum_two(a: int, b: int) -> int:
    # Let's put print here to see what was the function called with
    print(f'Called with {a} {b}')
    return a + b


async def main() -> None:
    # Call the function first time with (5, 5), this is where the encoder will be applied before setting cache value
    print(f'First call result: {await sum_two(5, 5)}')

    # Calling the function again with the same arguments to make decoder do its job on retrieving value from cache
    print(f'Second call result: {await sum_two(5, 5)}')


if __name__ == '__main__':
    asyncio.run(main())
```

</details>


## Running the code

After running the currently crafted file, we should get the following output:

<!-- termynal -->
```bash
# Run our example
$ python main.py

# The ouput will be
Called with 5 5
First call result: 10
Second call result: 60

```

As you can see, the second call result was 60, which is 6 times bigger than the original value.


## What's next

We'll see some magic that py-cachify does on a function wrap and learn how to manually reset a cache.
