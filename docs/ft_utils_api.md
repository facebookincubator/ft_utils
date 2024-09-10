# ft_utils API Documentation

## Modules

The ft_utils API is organized into several modules, each providing a specific set of functionalities.

### concurrent

The [concurrent module](concurrent_api.md) provides a set of foundational structures to implement scalable and efficient Free Threaded code. Using these structures can help avoid bottlenecks and enhance thread-consistency in FTPython code.

### synchronization

The [synchronization module](synchronization_api.md) provides specialized lock types that work in GIL-based Python and offer significant benefits for Free Threaded programming. These locks can help improve the performance and reliability of concurrent code.

### local

The [local module](local_api.md) provides helper classes to move certain forms of processing from being cross-thread to being local to a thread. These classes are necessary to avoid key bottlenecks that can occur due to cache contention, critical sections, and reference counting in Free Threaded Python.

