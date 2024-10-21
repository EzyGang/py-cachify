# Release Notes

## [2.0.0](https://github.com/EzyGang/py-cachify/releases/tag/v2.0.0)

### Features & Enchancements
- **Lock improvements**: Locks are now way more versatile and support new parameters like:
    - Whether to wait for the lock to expire or not (`nowait`, boolean)
    - Timeouts for how long should it try to acquire a lock. (`timeout`, int | float | None)
    - Expiration param to prevent deadlocks (`exp`, int | None)
    - When using lock as a decorator or using `once` decorator two methods are being added to the wrapped function:
        - `is_locked(*args, **kwargs)` - to check whether the lock is acquired or not
        - `release(*args, **kwargs)` - to forcefully release a lock.
    
    - More info could be found [here](./reference/lock.md).
  
- **File layout improved**: All internal files have been made private helping LSP's and IDE's 
provide better import locations for the features py-cachify provides.

- **Type annotations now feature TypeIs & Protocols**: Updated type annotations now provide even better IDE support, 
making it easier to write better code. They expose all methods attached to decorated functions and help you inline.

- **Additional tests were added**

- **`cached` decorator improvements**: There is now a new method attached to the wrapped functions called
`reset(*args, **kwargs)` to allow for a quick cache resets.
    - More info can be found [here](./reference/cached.md).
    
- **Bump dependencies**

### Breaking Changes
- **async_lock**: Async lock has been removed, you should replace it with `lock` since it now can work in both contexts.
- **import locations**: since files were renamed and moved around quite a bit, 
some import locations may not work after the 2.0.0 release, so I recommend reimporting used functions to ensure they work in your project.
### Deprecations
- **async_once, sync_once, async_cached, sync_cached**: These are now deprecated and scheduled for removal in 3.0.0
(all of those methods are just aliases for `cached` and `once`). 

### Miscellaneous
- **Documentation**: Documentation was refactored and greatly improved.

I recommend checking out **[full API reference](reference/init.md)** to get familiar with changes and new features.

## [1.1.2](https://github.com/EzyGang/py-cachify/releases/tag/v1.1.2)

### Features & Enchancements
- **Bump dependencies**
- **Docs update to include info on `init_cachify` `prefix` parameter**


## [1.1.0](https://github.com/EzyGang/py-cachify/releases/tag/v1.1.2)
### Features & Enchancements
- **Custom encoders/decoders for the `cached` decorator**: `enc_dec` parameter introduced on a `cached` decorator.

### Miscellaneous
- **Documentation update**
