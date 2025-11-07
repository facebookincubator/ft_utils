![Image](https://github.com/user-attachments/assets/f4ef78b9-8cc0-4264-971f-d6ac76884f3a)
# concurrency Module Documentation

The concurrency module provides a set of concurrently scalable data structures and patterns for Python. This module is designed to support high-performance, scalable programming with Free Threaded Python.

## ConcurrentDict

A concurrently accessible dictionary.

### Methods

* `__init__(scaling=17)`: Initializes a new ConcurrentDict with the specified number of concurrent structures. This relates to the number of threads it supports with good scaling. For optimal performance, this value should be close to the number of cores on the machine. However, under or over estimating this value by a factor of 2 or even more does not have a huge impact on performance.
* `as_dict()`: Creates a dict from the key value pairs in this ConcurrentDict. This is not thread consistent; it is safe to call whilst the ConcurrentDict is being updated, however, which key/value pairs will be copied over is not defined.

### Operators

ConcurrentDict also supports the following access methods:

* `d[key]`: Returns the value associated with the specified key.
* `d[key] = value`: Sets the value associated with the specified key.
* `del d[key]`: Deletes the key-value pair associated with the specified key.
* `key in d`: Returns `True` if the dictionary holds the specified key, `False` otherwise..

### Notes

ConcurrentDict does not support all the API methods of a built-in dict. It is designed for basic key-value store operations in a concurrent environment.

### Example
```python
from .concurrency import ConcurrentDict

d = ConcurrentDict()
d['key'] = 'value'
print(d['key'])  # prints 'value'
print('key' in d))  # prints True
del d['key']
print('key' in d))  # prints False
```

## AtomicInt64

A 64-bit integer that can be updated atomically.

### Methods

* `__init__(value=0)`: Initializes a new AtomicInt64 with the specified value.
* `get()`: Returns the current value.
* `set(value)`: Sets the value.
* `incr()`: Increments the value and returns the new value.
* `decr()`: Decrements the value and returns the new value.

In addition the following numeric methods are implemented.

* `__sub__(self, other)`: Returns the result of subtracting `other` from `self`.
* `__mul__(self, other)`: Returns the result of multiplying `self` by `other`.
* `__floordiv__(self, other)`: Returns the largest whole number less than or equal to the result of dividing `self` by `other`.
* `__or__(self, other)`: Returns the bitwise OR of `self` and `other`.
* `__xor__(self, other)`: Returns the bitwise XOR of `self` and `other`.
* `__and__(self, other)`: Returns the bitwise AND of `self` and `other`.
* `__neg__(self)`: Returns the negative of `self`.
* `__pos__(self)`: Returns `self` unchanged.
* `__abs__(self)`: Returns the absolute value of `self`.
* `__invert__(self)`: Returns the bitwise NOT of `self`.
* `__bool__(self)`: Returns `True` if `self` is non-zero, `False` otherwise.
* `__iadd__(self, other)`: Adds `other` to `self` in-place and returns `self`.
* `__isub__(self, other)`: Subtracts `other` from `self` in-place and returns `self`.
* `__imul__(self, other)`: Multiplies `self` by `other` in-place and returns `self`.
* `__ifloordiv__(self, other)`: Divides `self` by `other` in-place using floor division and returns `self`.
* `__ior__(self, other)`: Performs a bitwise OR of `self` and `other` in-place and returns `self`.
* `__ixor__(self, other)`: Performs a bitwise XOR of `self` and `other` in-place and returns `self`.
* `__iand__(self, other)`: Performs a bitwise AND of `self` and `other` in-place and returns `self`.
* `__int__(self)`: Returns an integer representation of `self`.
* `__eq__(self, other)`: Returns `True` if `self` is equal to `other`, `False` otherwise.
* `__ne__(self, other)`: Returns `True` if `self` is not equal to `other`, `False` otherwise.
* `__lt__(self, other)`: Returns `True` if `self` is less than `other`, `False` otherwise.
* `__le__(self, other)`: Returns `True` if `self` is less than or equal to `other`, `False` otherwise.
* `__gt__(self, other)`: Returns `True` if `self` is greater than `other`, `False` otherwise.
* `__ge__(self, other)`: Returns `True` if `self` is greater than or equal to `other`, `False` otherwise.

### Example

```python
from .concurrency import AtomicInt64

i = AtomicInt64(10)
print(i.get())  # prints 10
i.incr()
print(i.get())  # prints 11
i.add(5)
print(i.get())  # prints 16
```

## AtomicReference

A reference that can be updated atomically.

### Methods

* `__init__(obj=None)`: Initializes a new AtomicReference with the specified object.
* `get()`: Returns the current object.
* `set(obj)`: Sets the object.
* `exchange(obj)`: Exchanges the current object with the specified object and returns the previous object.
* `compare_exchange(expected, obj)`: Compares the current object with the expected object and exchanges it with the specified object if they match. Returns `True` if the exchange happened, `False` otherwise.

### Using compare_exchange

The `compare_exchange` method can be used in a loop to atomically update the reference, similar to using the CAS instruction in native programming.

### Example

```python
from .concurrency import AtomicReference

r = AtomicReference(0)

def increment(r):
    while True:
        current = r.get()
        new_value = current + 1
        if r.compare_exchange(current, new_value):
            break

increment(r)
print(r.get())  # prints 1
```

In this example, the `increment` function uses a loop to atomically increment the value of the AtomicReference. The `compare_exchange` method is used to check if the current value is still the same as the expected value, and if so, updates the value to the new value. If another thread has updated the value in the meantime, the `compare_exchange` method will return `False` and the loop will retry.

Here are the documents for the new classes:

## AtomicFlag

A boolean flag that can be updated atomically.

### Methods

* `__init__(value)`: Initializes a new AtomicFlag with the specified value.
* `set(value)`: Sets the value of the flag.
* `__bool__()`: Returns the current value of the flag.

### Example
```python
from .concurrency import AtomicFlag

flag = AtomicFlag(True)
print(flag)  # prints True
flag.set(False)
print(flag)  # prints False
```

## ConcurrentGatheringIterator

A concurrent iterator that gathers values from multiple threads and yields them in order.

### Methods

* `__init__(scaling)`: Initializes a new ConcurrentGatheringIterator with the specified scaling factor.
* `insert(key, value)`: Inserts a key-value pair into the iterator.
* `iterator(max_key, clear)`: Returns an iterator that reads and deletes key-value pairs from the iterator in order.

### Notes

* The iterator uses a ConcurrentDict to store the key-value pairs.
* The `insert` method is thread-safe and can be called from multiple threads.
* The `iterator` method returns an iterator that yields the values in order, blocking if the next value is not available.
* max_key passed to iterator tells the iterator at what point to stop iteration; i.e. all expected values have been gathered..
* If an exception occurs during insertion, the iterator will fail with a RuntimeError.
* scaling passed to the __init__ function governs the number of threads the iterator supports with good scaling.

### Example

```python
from .concurrency import ConcurrentGatheringIterator

iterator = ConcurrentGatheringIterator()
iterator.insert(0, 'value0')
iterator.insert(1, 'value1')
iterator.insert(2, 'value2')

for value in iterator.iterator(2):
    print(value)  # prints 'value0', 'value1', 'value2'
```

A more complex example:

```python
from .concurrency import ConcurrentGatheringIterator, AtomicInt64
from concurrent.futures import ThreadPoolExecutor

def insert_value(iterator, atomic_index, value):
    index = atomic_index.incr()
    iterator.insert(index, value)

def test_concurrent_gathering_iterator():
    iterator = ConcurrentGatheringIterator()
    atomic_index = AtomicInt64(-1)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for i in range(100):
            futures.append(executor.submit(insert_value, iterator, atomic_index, i))

        for future in futures:
            future.result()

    results = list(iterator.iterator(99))
    assert results == list(range(100))

test_concurrent_gathering_iterator()
```

In this example, we use a ThreadPoolExecutor to insert values into the ConcurrentGatheringIterator from multiple threads. We use an AtomicInt64 to generate the indices in order. After inserting all the values, we retrieve the results from the iterator and check that they are in the correct order.

Note that the `insert_value` function is a helper function that inserts a value into the iterator at the next available index. The `test_concurrent_gathering_iterator` function is the main test function that creates the iterator, inserts values from multiple threads, and checks the results.

This example demonstrates that the ConcurrentGatheringIterator can handle concurrent inserts from multiple threads and still produce the correct results in order.

## ConcurrentQueue

A concurrent queue that allows multiple threads to push and pop values.

### Methods

*   `__init__(scaling=None, lock_free=False)`: Initializes a new ConcurrentQueue with the specified scaling factor. If `lock_free` is True, the queue will use a lock-free implementation, which can improve performance in certain scenarios.
*   `push(value)`: Pushes a value onto the queue. This method is thread-safe and can be called from multiple threads.
*   `pop(timeout=None)`: Pops a value from the queue. The method will block until a value is available. If `timeout` is specified, the method will raise an Empty exception if no value is available within the specified time.
*   `pop_local(timeout=None)`: Returns a LocalWrapper object containing the popped value. The behavior is otherwise identical to `pop(timeout)`.
*   `shutdown(immediate=False)`: Initiates shutdown of the queue. If `immediate` is True, the queue will shut down immediately, otherwise it will wait for any pending operations to complete.
*   `size()`: Returns the number of elements currently in the queue.
*   `empty()`: Returns True if the queue is empty, False otherwise.

### Exceptions
*   `ShutDown` raised to indicate the ConcurrentQueue is shutdown. In Python 3.13 and above `queue.ShutDown` is a type and this Exception will be an aliase for it. In earlier versions of Python concurrent defines its own ShutDown type to allow backward compatibility.
*   'Empty' raised to indicate a pop/get operation timed out. This is the same as queue.Empty.

### Notes

*   The queue uses a ConcurrentDict to store the values.
*   If an exception occurs during push, the queue will fail with a RuntimeError.
*   The `scaling` parameter passed to the `__init__` function governs the number of threads the queue supports with good scaling.
*   Setting `lock_free` to True can improve performance in scenarios with a large number of readers and writers, as it avoids overloading the kernel with too many locks. However, this comes at the cost of increased CPU usage.

#### Lock-Free Implementation

The lock-free implementation of the queue uses a combination of atomic operations and careful synchronization to ensure thread safety without the need for locks. This approach can provide better performance and scalability in certain scenarios, particularly those with a large number of readers and writers. It will tend to consume more CPU in lightly loaded contitions than using the lock based approach.

In general, the lock-free implementation is recommended for scenarios where:

*   There are a large number of readers and writers.
*   The queue is very large and needs to support a high throughput.
*   Low latency is critical.
*   Profiling shows poor scaling hand high load on the kernel.

On the other hand, the lock-based implementation is recommended for scenarios where:

*   There are a small number of readers and writers.
*   The queue is relatively small and does not require high throughput.

#### Example

```python
from .concurrency import ConcurrentQueue

queue = ConcurrentQueue()

queue.push('value0')
queue.push('value1')
queue.push('value2')
queue.push('value3')
queue.push('value4')

print(queue.pop())  # prints 'value0'
print(queue.pop(timeout=0.1))
print(queue.pop_local())  # returns a LocalWrapper object
queue.shutdown()
queue.pop()
# Raises ShutDown
queue.pop()
# Raises ShutDown
queue.push('value5')
```

## StdConcurrentQueue

This follows the same API as [queue.Queue](https://docs.python.org/3/library/queue.html#queue.Queue). For simple applications StdConcurrentQueue will work as a drop in replacement for queue.Queue. However, there are subtle differences:

*   StdConcurrentQueue will use a very small amount of CPU time even when not processing elements.
*   This implementation has weaker FIFO guaratees than queue.Queue, which might cause subtle issues in some applications.
*   StdConcurrentQueue will use and release memory in a different pattern than queue.Queue.
*   The maxsize is not as strictly guaranteed. If maxsize is set and a large number of threads attempt to fill the queue beyond maxsize then a small overfill might occur due to the lack of a lock to prevent this race condition.

Therefore, in complex applications it may be a better approach to mindfully replace highly contended queue.Queue instances with StdConcurrentQueue. In this case it is also better to use the simpler ConcurrentQueue where possible.
