# ft_utils API Documentation

## Modules

The ft_utils API is organized into several modules, each providing a specific set of functionalities.

### concurrency

The [concurrency module](concurrency_api.md) provides a set of foundational structures to implement scalable and efficient Free Threaded code. Using these structures can help avoid bottlenecks and enhance thread-consistency in FTPython code.

### synchronization

The [synchronization module](synchronization_api.md) provides specialized lock types that work in GIL-based Python and offer significant benefits for Free Threaded programming. These locks can help improve the performance and reliability of concurrent code.

### local

The [local module](local_api.md) provides helper classes to move certain forms of processing from being cross-thread to being local to a thread. These classes are necessary to avoid key bottlenecks that can occur due to cache contention, critical sections, and reference counting in Free Threaded Python.

## Native Code

The [ft_compat](ft_compat.md) header provides backward compatibility for native code.

For developers writing native code (C, C++, Rust, etc.) that interacts with the Python C API, `ft_compat.h` provides a backwards compatibility layer for Free Threading-related APIs. This allows you to write code that takes advantage of Free Threading features, such as atomic operations and critical sections, while still maintaining support for older versions of Python. By using `ft_compat.h`, you can ensure that your native code is compatible with multiple versions of Python, reducing maintenance and testing efforts.

The [ft_weave](weave_api.md) header provides native access to advanced thread based features which are useful for scaling to high thread counts or controlling how threads behave on particular hardware and/or operating systems.
