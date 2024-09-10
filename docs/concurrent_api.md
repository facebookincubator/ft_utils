# concurrent Module Documentation

The concurrent module provides a set of concurrently scalable data structures and patterns for Python. This module is designed to support high-performance, scalable programming with Free Threaded Python.

## ConcurrentDict

A concurrently accessible dictionary.

### Methods

* `__init__(scaling=17)`: Initializes a new ConcurrentDict with the specified number of concurrent structures. This relates to the number of threads it supports with good scaling. For optimal performance, this value should be close to the number of cores on the machine. However, under or over estimating this value by a factor of 2 or even more does not have a huge impact on performance.
* `get(key)`: Returns the value associated with the specified key.
* `set(key, value)`: Sets the value associated with the specified key.
* `has(key)`: Returns True if the key is present in the dictionary, False otherwise.

### Operators

ConcurrentDict also supports the following access methods:

* `d[key]`: Returns the value associated with the specified key.
* `d[key] = value`: Sets the value associated with the specified key.
* `del d[key]`: Deletes the key-value pair associated with the specified key.

Note that the `in` operator is not supported because of implementation details in the CPython runtime. Please use `has` instead.

### Notes

ConcurrentDict does not support all the API methods of a built-in dict. It is designed for basic key-value store operations in a concurrent environment.

### Example
```python
from ft_utils.concurrent import ConcurrentDict

d = ConcurrentDict()
d['key'] = 'value'
print(d['key'])  # prints 'value'
print(d.has('key'))  # prints True
del d['key']
print(d.has('key'))  # prints False
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

### Example

```python
from ft_utils.concurrent import AtomicInt64

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
from ft_utils.concurrent import AtomicReference

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
from ft_utils.concurrent import AtomicFlag

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
from ft_utils.concurrent import ConcurrentGatheringIterator

iterator = ConcurrentGatheringIterator()
iterator.insert(0, 'value0')
iterator.insert(1, 'value1')
iterator.insert(2, 'value2')

for value in iterator.iterator(2):
    print(value)  # prints 'value0', 'value1', 'value2'
```

A more complex example:

```python
from ft_utils.concurrent import ConcurrentGatheringIterator, AtomicInt64
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

* `__init__(scaling)`: Initializes a new ConcurrentQueue with the specified scaling factor.
* `push(value)`: Pushes a value onto the queue.
* `pop()`: Pops a value from the queue.

### Notes

* The queue uses a ConcurrentDict to store the values.
* The `push` method is thread-safe and can be called from multiple threads.
* The `pop` method returns the next value in the queue, blocking if the queue is empty.
* If an exception occurs during push, the queue will fail with a RuntimeError.
* scaling passed to the __init__ function governs the relates to the number of threads it supports with good scaling.

### Example

```python
from ft_utils.concurrent import ConcurrentQueue

queue = ConcurrentQueue()
queue.push('value0')
queue.push('value1')
queue.push('value2')

print(queue.pop())  # prints 'value0'
print(queue.pop())  # prints 'value1'
print(queue.pop())  # prints 'value2'
```
