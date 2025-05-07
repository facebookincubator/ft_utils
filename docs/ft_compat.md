![Image](https://github.com/user-attachments/assets/f4ef78b9-8cc0-4264-971f-d6ac76884f3a)
# Backwards Compatibility with ft_compat.h

## Introduction

The `ft_compat.h` header file provides backwards compatibility for Free Threaded Python C API concepts to previous versions of Python. This allows developers to write native code (C, C++, Rust, etc.) that takes advantage of Free Threading where available, while still compiling and working on older versions of Python.

## What is ft_compat.h?

`ft_compat.h` is a header file that defines a set of macros and inline functions that mimic the behavior of various Free Threading-related APIs introduced in Python 3.13 and later. These include atomic operations, critical sections, and (maybe in the future) other synchronization primitives. These macros and functions provide a way for developers to use the new APIs in their native code, even when building against older versions of Python.

## Why do we need ft_compat.h?

Let's consider a real-world example. Suppose we have a production system that uses a complex CPython extension to perform scientific simulations. The system is currently running on Python 3.12, but the development team wants to start preparing the code to take advantage of Free Threading in Python 3.13.

However, the team cannot simply switch to Python 3.13 overnight. The existing system has been extensively tested and validated on Python 3.12, and there are concerns about introducing regressions or instability by switching to a new version of Python.

To address this challenge, the team decides to use `ft_compat.h` to introduce Free Threading-compatible code into the existing Python 3.12 system. By using the backwards compatibility layer provided by `ft_compat.h`, the team can start writing native code that takes advantage of the new atomic operations, critical sections, and other synchronization primitives, while still maintaining support for the existing Python 3.12 system.

As the team progressively develops and tests the new code, they can roll out the changes to the production system without disrupting the existing workflow. Once the entire system has been updated to use Free Threading, the team can switch to Python 3.13 and take full advantage of the performance and scalability benefits it offers.

Without `ft_compat.h`, the team would have to maintain two separate codebases: one for Python 3.12 and another for Python 3.13. This would be a significant maintenance burden, and would likely lead to delays and errors in the development process.
By providing a backwards compatibility layer, `ft_compat.h` enables developers to adopt Free Threading in a gradual and controlled manner, without disrupting existing systems or workflows.

## How to use ft_compat.h

To use `ft_compat.h`, simply include the header file in your native code project. The macros and inline functions defined in the header file will be used automatically when building against older versions of Python. Note that these macros, in previous versions of Python, will not be atomic. There will be no performance overhead of using these for older version of Python. This design choice is because we assume the GIL will ensure thread safety and therefore the overhead of atomic operations is pointless.

For example:
```C
#include "ft_compat.h"
// Use the _Py_atomic_store_ssize macro to store a value atomically
_Py_atomic_store_ssize(&my_var, 42);
// Use the Py_BEGIN_CRITICAL_SECTION and Py_END_CRITICAL_SECTION macros to define a critical section
Py_BEGIN_CRITICAL_SECTION
    // Critical section code here
Py_END_CRITICAL_SECTION
```

When building against Python 3.13 or later, the `_Py_atomic_store_ssize` macro will expand to the native atomic operation, and the `Py_BEGIN_CRITICAL_SECTION` and `Py_END_CRITICAL_SECTION` macros will expand to the native critical section implementation. When building against older versions of Python, the macros will fall back to compatible implementations.

## Benefits of using ft_compat.h

By using `ft_compat.h`, developers can:

*  Take advantage of the new atomic operations, critical sections, and other synchronization primitives in Free Threading, even when building against older versions of Python.
*  Write native code that is compatible with multiple versions of Python, reducing maintenance and testing efforts.
*  Update their code to use the latest features and improvements in Free Threading, while still supporting older versions of Python.

## Future of ft_compat.h

As the Free Threading ecosystem continues to evolve, the functionality provided by `ft_compat.h` may be merged into other libraries, such as pythoncapi-compat. However, the `ft_compat.h` header file will continue to provide the same functionality, ensuring that any changes will not be breaking and code can continue to rely on ft_compat.

Additionally, as new Free Threading API changes and additions occur, we will add backward compatibility to `ft_compat.h` as required. This ensures that developers can continue to use the latest features and improvements in Free Threading, while still maintaining support for older versions of Python.
