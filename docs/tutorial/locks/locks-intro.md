# Introduction to Locks (Mutex)

In simple terms, a lock, also known as a mutex, 
is like electronic door locks that allow only one person to enter a room, 
or, in terms when it comes to coding - to make sure that certain code is 
being only run once at a time. This prevents data inconsistencies and race conditions.
`py-cachify` provides tools for creating and managing these locks, so you can keep your logic safe and organized.

## py-cachify's locks

This tutorial will show you how to use locks provided by `py-cachify`, what params do they have,
and showcase some common use case scenarios.

Note: py-cachify's main focus is to provide a convenient way to use distributed locks and in no way replace built-in ones. 
This type of lock is usually utilized heavily in web development in particular when scaling comes into play
and the synchronization problems are starting to surface as well as race conditions.


## What's next

We will dive deeper and look at some examples.