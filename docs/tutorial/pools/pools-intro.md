# Introduction to Pools

A pool is a mechanism for limiting concurrent access to a resource. Unlike a lock which allows only one execution at a time, a pool allows up to N simultaneous executions. Think of it as a parking lot with a fixed number of spaces: when all spaces are occupied, new cars must wait or go elsewhere.

## Use Cases

Pools solve problems where you need to control resource consumption:

**Connection Limits**: APIs often enforce rate limits or maximum concurrent connections. A pool ensures you never exceed those limits.

**Worker Management**: Background task workers (Celery, Taskiq) can use pools to prevent overwhelming downstream services. Only N workers process tasks for a given resource at once.

**Resource Pools**: Database connections, file handles, or external service clients often have practical limits. Pools help manage these shared resources across your application.

## How Pools Work in py-cachify

The `pool()` class manages a set of slots distributed via your cache backend:

1. When entering the pool (via context manager or decorator), the library attempts to acquire a slot
2. If slots are available, the code executes immediately
3. If the pool is full (all `max_size` slots occupied), behavior depends on configuration: raise an error, call a callback, or skip execution
4. When exiting, the slot is released for the next caller

Slots have a TTL (`slot_exp`) that automatically cleans up orphaned slots if a process crashes or hangs without releasing properly.

## Pools vs Locks

Locks enforce "only one at a time". Pools enforce "no more than N at a time". Use locks for mutual exclusion. Use pools for capacity management.

## What's Next

We will start with basic pool usage as a context manager.
