<p align="center">
<a href="https://py-cachify.readthedocs.io/latest/" target="_blank">
    <img src="https://i.imgur.com/kObXEhW.png" alt="header">
</a>
<a href="https://opensource.org/licenses/MIT" target="_blank">
    <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
</a>
<a href="https://badge.fury.io/py/py-cachify" target="_blank">
    <img src="https://badge.fury.io/py/py-cachify.svg" alt="PyPI version">
</a>
<a href="https://pypi.org/project/py-cachify/" target="_blank">
    <img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dm/py-cachify">
</a>
<a href="https://pypi.org/project/py-cachify/" target="_blank">
    <img src="https://img.shields.io/pypi/pyversions/py-cachify.svg?color=%2334D058" alt="supported versions">
</a>
<a href="https://coveralls.io/github/EzyGang/py-cachify?branch=main" target="_blank">
    <img src="https://coveralls.io/repos/github/EzyGang/py-cachify/badge.png?branch=main" alt="Coverage Status">
</a>
</p>
<p align="center">
<a href="https://github.com/EzyGang/py-cachify/actions/workflows/checks.yml/badge.svg" target="_blank">
    <img src="https://github.com/EzyGang/py-cachify/actions/workflows/checks.yml/badge.svg" alt="Pre-build checks and Tests">
</a>
<a href="https://py-cachify.readthedocs.io/en/latest/?badge=latest" target="_blank">
    <img src="https://readthedocs.org/projects/py-cachify/badge/?version=latest" alt="Documentation Status">
</a>
<a href="https://sonarcloud.io/summary/new_code?id=EzyGang_py-cachify" target="_blank">
    <img src="https://sonarcloud.io/api/project_badges/measure?project=EzyGang_py-cachify&metric=reliability_rating" alt="Reliability Rating">
</a>
</p>

---

**Py-Cachify** is a lightweight, backend-agnostic Python library for caching, distributed locking, and resource pool management. Works seamlessly with both sync and async code.

Out of the box, it supports **in-memory**, **Redis**, and **DragonflyDB** backends. You can also integrate **any custom backend** by implementing the `SyncClient` or `AsyncClient` protocols.

**Source Code**: <a href="https://github.com/EzyGang/py-cachify" target="_blank">https://github.com/EzyGang/py-cachify</a>

---

## Why py-cachify?

There are many caching libraries for Python—so why choose py-cachify?

**🪶 Tiny & Focused** — No bloated dependencies or complex setup. Just install and use.

**🔌 Backend Agnostic** — Switch from in-memory (development) to Redis/DragonflyDB (production) by changing one line. Or plug in any custom backend that implements simple protocols.

**✨ Minimal, Intuitive Syntax** — Stop wrestling with low-level `get/set` calls. One decorator handles caching, locking, or pool management automatically.

**🎯 Decorators That Just Work** — No manual key management, no cache client wiring in every file. Initialize once, decorate everywhere. Both sync and async functions are supported with identical APIs.

**🏭 Production Ready** — 100% test coverage, used in commercial projects, fully type-annotated for excellent IDE support.

| Feature | What it solves |
|---------|---------------|
| **@cached** | Eliminate redundant expensive computations and I/O |
| **lock / @lock** | Prevent race conditions in distributed systems |
| **@once** | Ensure background tasks don't overlap (deduplication) |
| **pool / @pooled** | Control concurrency—rate limiting, connection limits *(v3.1.0)* |
| **Backend Agnostic** | Switch between in-memory (dev) and Redis (prod) with one line |
| **Sync + Async** | Same API for both sync and async code |

---

## Installation

### pip
```bash
pip install py-cachify
```

### uv
```bash
uv add py-cachify
```

### poetry
```bash
poetry add py-cachify
```

For Redis support, you'll also need:
```bash
pip install redis
# or
uv add redis
# or
poetry add redis
```

---

## Table of Contents

- [Quick Start](#quick-start)
- [Core Features](#core-features)
  - [Caching](#caching)
  - [Distributed Locks](#distributed-locks)
  - [Run Once](#run-once)
  - [Resource Pools](#resource-pools) *(New in 3.1.0)*
- [Advanced Patterns](#advanced-patterns)
- [Backend Configuration](#backend-configuration)
- [API Quick Reference](#api-quick-reference)
- [Contributing](#contributing)
- [License](#license)

---

## Quick Start

```python
from py_cachify import init_cachify, cached

# Initialize once (uses in-memory cache by default)
init_cachify()

@cached(key='user-{user_id}', ttl=300)
async def get_user(user_id: int) -> dict:
    return await fetch_from_db(user_id)

# First call executes the function
user = await get_user(42)

# Subsequent calls return cached result instantly
user = await get_user(42)

# Manually invalidate when needed
await get_user.reset(user_id=42)
```

📖 **[Full Tutorial →](tutorial/index.md)**  
📖 **[API Reference →](reference/init.md)**

---

## Core Features

### Caching

Cache function results with dynamic keys and configurable TTL.

```python
from py_cachify import init_cachify, cached

init_cachify(default_cache_ttl=60)  # Default 60s when ttl is omitted

@cached(key='sum-{a}-{b}', ttl=300)  # Custom TTL
async def sum_two(a: int, b: int) -> int:
    return a + b

@cached(key='profile-{user_id}')  # Uses default_cache_ttl=60
async def get_profile(user_id: int) -> dict:
    return await fetch_profile(user_id)

@cached(key='flags', ttl=None)  # Never expires
def get_feature_flags() -> dict:
    return load_flags()
```

**Reset cache manually:**
```python
await sum_two.reset(a=1, b=2)  # Clear specific entry
```

**Custom encoder/decoder** for non-picklable types:
```python
def encode(obj: MyClass) -> dict:
    return {'data': obj.to_dict()}

def decode(data: dict) -> MyClass:
    return MyClass.from_dict(data['data'])

@cached(key='obj-{id}', enc_dec=(encode, decode))
def get_obj(id: int) -> MyClass:
    return MyClass(id)
```

[Full @cached reference →](reference/cached.md)

---

### Distributed Locks

Prevent concurrent execution with distributed locks.

**Context manager:**
```python
from py_cachify import lock

# Async
async with lock('resource-{id}', nowait=False, timeout=10):
    await process_resource(id)

# Sync
with lock('critical-section'):
    process_data()

# Check and force release
await lock('resource-{id}').is_alocked()
await lock('resource-{id}').arelease()
```

**Decorator:**
```python
@lock(key='process-{item_id}', nowait=True)
async def process_item(item_id: str):
    # Only one execution at a time per item_id
    await do_work(item_id)

# Check if locked for specific args
await process_item.is_locked(item_id='abc')
await process_item.release(item_id='abc')
```

[Full lock reference →](reference/lock.md)

---

### Run Once

Ensure a function runs only once at a time—useful for background tasks.

```python
from py_cachify import once

@once(key='sync-order-{order_id}', raise_on_locked=False, return_on_locked=None)
async def sync_order(order_id: str):
    # If another task is already syncing this order, this exits early
    await call_external_api(order_id)

@once(key='daily-report', raise_on_locked=True)
def generate_report():
    # Raises CachifyLockError if already running
    run_expensive_analysis()
```

Perfect for Celery, Dramatiq, Taskiq, or any task queue to prevent duplicate processing.

[Full @once reference →](reference/once.md)

---

### Resource Pools *(New in 3.1.0)*

Limit concurrent execution to N at a time—ideal for API rate limits, connection pools, or worker throttling.

**Context manager:**
```python
from py_cachify import pool, CachifyPoolFullError

async with pool(key='api-pool-{user_id}', max_size=5):
    # Max 5 concurrent API calls per user
    await call_external_api(user_id)
```

**Decorator with graceful handling:**
```python
from py_cachify import pooled

def queue_for_later(*args, **kwargs):
    # Called when pool is full instead of executing
    return {'status': 'queued', 'task_id': kwargs.get('task_id')}

@pooled(key='worker-pool', max_size=10, on_full=queue_for_later)
async def process_task(task_id: str):
    await do_work(task_id)

# Check pool occupancy
occupancy = await process_task.size()
```

**Raise on full:**
```python
@pooled(key='strict-pool', max_size=3, raise_on_full=True)
async def strict_task():
    # Raises CachifyPoolFullError when pool is full
    await work()
```

[Full pool reference →](reference/pool.md)

---

## Advanced Patterns

### Multi-Layer Caching

Stack caches for optimal performance—fast in-memory layer over persistent Redis.

```python
init_cachify(default_cache_ttl=300)  # Redis layer

# Local in-memory instance with shorter TTL
local = init_cachify(is_global=False, prefix='L1-', default_cache_ttl=5)

@local.cached(key='l1-{user_id}')      # Outer: in-memory, 5s
@cached(key='l2-{user_id}')            # Inner: Redis, 5min
async def get_user(user_id: int):
    return await fetch_user(user_id)

# Reset clears both layers
await get_user.reset(user_id=42)
```

[Multi-layer tutorial →](tutorial/cached-decorator/reset-attribute.md)

### Instance-Based Usage

Create isolated caches for different subsystems.

```python
# Global for main app
init_cachify(prefix='APP-')

# Isolated instance for metrics (different prefix, different TTL)
metrics = init_cachify(is_global=False, prefix='METRICS-', default_cache_ttl=60)

@metrics.cached(key='metric-{name}')
def compute_metric(name: str) -> float:
    return expensive_calculation(name)
```

---

## Backend Configuration

### Redis / DragonflyDB

```python
from py_cachify import init_cachify
from redis import from_url as redis_from_url
from redis.asyncio import from_url as async_redis_from_url

init_cachify(
    sync_client=redis_from_url('redis://localhost:6379/0'),
    async_client=async_redis_from_url('redis://localhost:6379/0'),
    prefix='APP-',
    default_cache_ttl=300,
    default_lock_expiration=30,
    default_pool_slot_expiration=600,  # 10 min for pool slots
    lock_poll_interval=0.1,  # Check lock every 100ms when waiting
)
```

### In-Memory (Default)

```python
from py_cachify import init_cachify

# Perfect for development and testing
init_cachify()
```

### Custom Backend

Implement `SyncClient` or `AsyncClient` protocols for Memcached, database-backed, or file-based caching.

[Custom client guide →](reference/init.md#custom-clients)

---

## API Quick Reference

| Decorator/Class | Purpose | Key Parameters |
|-----------------|---------|----------------|
| `@cached(key, ttl, enc_dec)` | Cache function results | `key`: template string, `ttl`: expiration in seconds |
| `lock(key, nowait, timeout)` | Distributed lock context manager | `nowait`: fail fast, `timeout`: max wait time |
| `@lock(key, nowait, timeout)` | Lock as decorator | Same as above |
| `@once(key, raise_on_locked, return_on_locked)` | Prevent concurrent runs | `raise_on_locked`: exception vs skip |
| `pool(key, max_size, slot_exp)` | Resource pool context manager *(v3.1.0)* | `max_size`: max concurrent, `slot_exp`: slot TTL |
| `@pooled(key, max_size, on_full, raise_on_full)` | Pool as decorator *(v3.1.0)* | `on_full`: callback when full |

[Full API reference →](reference/init.md)

---

## Contributing

If you'd like to contribute, please first discuss changes via [Issues](https://github.com/EzyGang/py-cachify/issues), then submit a PR.

---

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/EzyGang/py-cachify/blob/main/LICENSE) file for details.
