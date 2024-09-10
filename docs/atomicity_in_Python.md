# Solving Atomicity/Consistency Issues in Free Threaded Python

## Introduction

### Atomicity/Consistency

These are similar concepts in multi-threaded programming. A change to data (setting a variable, updating a dictionary etc.) is atomic if it is either completely done or not done at all. Consistency here is really thread-consistency where all threads in a program see exactly the same data at the same time.

In traditional Python, the Global Interpreter Lock (GIL) ensures that memory operations are implicitly atomic and consistent. For example, if we update a variable from 1 to 2 it is either done or not done and all threads will see the update.

```python
x = 1
x = 2
# x will be 2 in all threads

y = {"a": "b"}
y["a"] = "c"
# y["a"] will be "c" in all threads everywhere.
```

However, with the introduction of Free Threaded Python (PEP 703), we no longer have the GIL to enforce atomicity so changes have been made to the way key parts of the Python runtime work to keep the consistent, atomic behavior.

## Atomic Variables and Data Structures

Most inter-thread communication in Python occurs through variables, which are either slots or dictionary key-value pairs under the covers. To keep Python behaving as expected, these variables have been made atomic. Additionally, data structures like lists are atomic for read/write operations that do not change their size.

## Critical Sections

To prevent native code from experiencing race conditions, Critical Sections are used to protect sensitive areas of code. The native code module of objects has been enhanced to all objects have a 'monitor' which controls its state of locking for that object. A Critical Section takes a lock based on an object's monitor, ensuring that only one thread can execute the protected code at a time. This mechanism provides atomicity and consistency where required, without exposing any locking mechanisms to Python programmers. To the programmer everything works just like it always did except more than one thread can run at once outside of the critical section.

## ft_utils Library

The ft_utils library provides specialized structures and utilities to support fast and scalable free threaded algorithms. Some of the key features of ft_utils include:

*   **ConcurrentDict:** A thread-safe dictionary implementation that scales well with the number of threads accessing it.
*   **AtomicInt64:** A true atomic integer that does not require locks and supports all pure integer operations with atomic updates.
*   **BatchExecutor:** A utility that executes tasks in batches, allowing for efficient and thread-safe execution of code that cannot be made free threaded.
*   **LocalWrapper:** A wrapper that helps manage reference counts between threads by creating a local copy of an object.
*   **IntervalLock:** A lock that mimics the behavior of the GIL, allowing a program to schedule execution of different threads.
*   **RWLock:** A readers/writer lock that allows efficient management of a resource read frequently by many threads but updated infrequently.
*   **ConcurrentGatheringIterator:** An iterator that allows sequenced collection of objects from many threads and reading from one.
*   **ConcurrentQueue:** A highly scalable queue that does not require locks around push or pop operations.
*   **AtomicFlag:** A boolean settable flag based on AtomicInt64.
*   **AtomicReference:** A reference that can be set, get, exchanged, and compared atomically without requiring locks.

## Atomicity in Python

Python is a language which is implemented on a runtime. Python as a language does not say much about atomicity consistency; however, CPython, which is the reference implementation, does have strong guarantees (see the introduction at the start of this document). In this section we will dig into the subject a little more.

While the removal of the GIL in Free Threaded Python introduces new challenges for ensuring atomicity, it's essential to recognize that many Python programming constructs are not inherently atomic or thread-safe.

For instance, even simple operations like `x += 1` can be problematic when dealing with immutable objects like integers. In this case, the operation is not performed in-place; instead, a new value is allocated to `x`, which can lead to unexpected behavior in multi-threaded environments.

In traditional GIL-based Python, some code may appear to work correctly due to the GIL's scheduling mechanism, which prevents threads from running concurrently. However, this does not necessarily mean that the code is thread-safe or atomic.

The GIL itself is not a traditional lock; it uses a combination of opcode counting and explicit release mechanisms to switch between threads. This approach results in locks being acquired and released relatively infrequently in GIL-based Python.

In contrast, Free Threaded Python allows locks to be acquired and released much more rapidly, which can introduce performance issues related to operating system overhead rather than contention. To mitigate these concerns, developers should focus on using high-level concurrency abstractions and data structures designed specifically for parallel execution.

One effective way to achieve robust and scalable concurrent programming in Free Threaded Python is by leveraging Thread Pool Executors and concurrent data types such as ConcurrentDict, AtomicInteger, AtomicReference, and others. By combining these tools with well-established programming patterns, developers can create efficient, reliable, and maintainable concurrent code.

## Conclusion

Solving atomicity issues in Free Threaded Python requires a combination of atomic variables and data structures, Critical Sections to protect native code, and specialized libraries like ft_utils. By using these tools and techniques, developers can write efficient and thread-safe code that takes advantage of the benefits of Free Threaded Python.

## Next Steps

In the next section, [FTPython Programming A Worked Example](ft_worked_example.md), we will demonstrate how to apply these concepts in real-world code, showcasing the benefits of using Free Threaded Python and its associated libraries for concurrent programming.
