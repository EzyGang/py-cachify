# Pool - Parameters in Py-Cachify

## Parameter Overview

The `pool()` constructor accepts three key parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | Unique identifier for this pool in the cache |
| `max_size` | `int` | Maximum number of concurrent slots available |
| `slot_exp` | `Union[int, None]`, optional | TTL for individual slots in seconds. Uses `default_pool_slot_expiration` from `init_cachify()` if not specified |

## The ///max_size/// Parameter

This controls capacity. A pool with `max_size=5` allows up to 5 concurrent executions across all processes sharing the same cache backend.

Choose `max_size` based on:
- External API rate limits (requests per second, concurrent connections allowed)
- Downstream service capacity (database connection limits, worker thread pools)
- Your infrastructure constraints (memory, CPU, file descriptors)

## The ///slot_exp/// Parameter (Slot TTL)

Slots automatically expire after `slot_exp` seconds. This prevents "orphaned" slots if a process crashes or hangs while holding a slot.

The default comes from `default_pool_slot_expiration` in `init_cachify()` (600 seconds / 10 minutes). Override per pool:

```python
from py_cachify import init_cachify, pool


init_cachify(default_pool_slot_expiration=300)  # 5 minute default


# Uses the 300 second default
standard_pool = pool(key='standard', max_size=10)


# Override for a specific pool with shorter TTL
short_pool = pool(key='quick-tasks', max_size=5, slot_exp=60)  # 1 minute


# Never expires (use with caution - orphaned slots persist until manual cleanup)
infinite_pool = pool(key='long-tasks', max_size=3, slot_exp=None)
```

## How Slot Expiration Works

Important: slot expiration does not interrupt running code. It only affects the pool's internal count.

When a slot expires:
1. The slot becomes eligible for cleanup on the next acquire attempt
2. Any code still executing inside that slot continues running
3. The pool count decreases, making room for new acquires

This design prevents hung processes from permanently consuming pool capacity while not killing legitimate long-running tasks.

## Global Default Configuration

Set `default_pool_slot_expiration` in `init_cachify()` to control the default for all pools:

```python
from py_cachify import init_cachify


init_cachify(
    default_pool_slot_expiration=1200,  # 20 minutes
)
```

Explicit `slot_exp` on individual pools always overrides the global default.

## What's Next

We will cover the `size()` method for checking pool occupancy.
