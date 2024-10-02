# Once - Decorator for background tasks

## Description

This does not deserve a separate tutorial, since this `@once` decorator is just a wrapper around the `lock`, but it's too cool to not show 🙂

`once` can come handy when you have a lot of background tasks, which usually are powered by `celery`, `darq`, `taskiq` or `dramatiq`.

## Theoretical example

Let's say we have some sort of a spawner task, which spawns a lot of small ones. 
Like, for example, the spawner get's all the orders in progress and submits a task for each one to check the status on it.

It could look like that:

```python
from celery import shared_task

# This is scheduled to run every 5 minutes
@shared_task()
def check_in_progress_orders() -> None:
    orders = ...  # hit the database and get all orders
    [check_order.s(order_id=order.id).delay() for order in orders]
    

# This is being spawn from the previous one
@shared_task()
def check_order(order_id: UUID) -> None
    # check the order progress, update state, save

```

So in this scenario, we don't really care about the results of each task, but we DO care that we are not running the second task for the same order twice
since it could break things.

This is where `@once` could come in handy, it will make sure that only one task is being run at the same time,
all subsequent tasks on the same order will exit while at least one task is running.

The full code will look like that:

```python
from py_cachify import once
from celery import shared_task

# This is scheduled to run every 5 minutes
@shared_task()
def check_in_progress_orders() -> None:
    orders = ...  # hit the database and get all orders
    [check_order.s(order_id=order.id).delay() for order in orders]
    

# This is being spawn from the previous one
@shared_task()
@once(key='check_order-{order_id}', raise_on_locked=False, return_on_locked=None)  # raise_on_locked and return_on_locked can be omitted (those values are defaults)
def check_order(order_id: UUID) -> None
    # check the order progress, update state, save
    pass

```

This will make sure you won't run into multiple update tasks running at the same time for one order.

## What's next

You can always check the full reference for once here.

## Conslusion

This concludes the tutorial for the py-cachify.

We have covered the basics of the package and glanced over common cases, 
the topics of caching and locking are pretty common yet they are always unique to the specifics of app and tasks that programmer wants to solve.

Py-Cachify tries to help you cover your specific cases giving you the tools that you can adapt to your needs without bloating your codebase.

For full API reference go here.