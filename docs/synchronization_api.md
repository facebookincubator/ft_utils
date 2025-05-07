![Image](https://github.com/user-attachments/assets/f4ef78b9-8cc0-4264-971f-d6ac76884f3a)
# synchronization Module Documentation

## Classes

### IntervalLock

An IntervalLock is a specialized lock that allows threads to acquire the lock for a specified interval. It is designed to prevent deadlocks and ensure that threads can make progress.

The IntervalLock is designed to benefit Free Thread Python, but it will also work in GIL Python.

#### Methods

* `__init__(interval: float = 0.005)`: Initializes an IntervalLock with the given interval in seconds.
* `lock()`: Acquires the lock.
* `unlock()`: Releases the lock.
* `poll()`: Calls `cede()` if the interval has expired.
* `cede()`: Cedes the lock to any waiters and resets the interval.
* `locked()`: Returns whether the lock is locked or not.
* `__enter__()`: Enters the runtime context (lock).
* `__exit__(exc_type, exc_value, traceback)`: Exits the runtime context (unlock).

### ReaderWriterLock

A ReaderWriterLock is a lock that allows multiple readers to access a resource simultaneously, while preventing writers from accessing the resource until all readers have released the lock. This lock prioritizes writers, meaning that if a writer is waiting to acquire the lock, no more readers can acquire it. This prevents a large number of readers from starving a single or small number of writers, making it suitable for use cases where writers need to make progress without being blocked by a large number of readers.

The ReaderWriterLock is designed to benefit Free Thread Python, but it will also work in GIL Python.

#### Methods

* `__init__()`: Initializes a ReaderWriterLock.
* `lock_read()`: Acquires the read lock.
* `unlock_read()`: Releases the read lock.
* `lock_write()`: Acquires the write lock.
* `unlock_write()`: Releases the write lock.
* `readers()`: Returns the number of readers holding the lock.
* `writers_waiting()`: Returns whether there is a writer waiting to hold the lock.
* `writer_locked()`: Returns whether the writer lock is held.

### RWReadContext

An RWReadContext is a context manager that acquires the read lock for a ReaderWriterLock.

#### Methods

* `__enter__()`: Enters the read lock context.
* `__exit__(exc_type, exc_value, traceback)`: Exits the read lock context.

### RWWriteContext

An RWWriteContext is a context manager that acquires the write lock for a ReaderWriterLock.

#### Methods

* `__enter__()`: Enters the write lock context.
* `__exit__(exc_type, exc_value, traceback)`: Exits the write lock context.

## Example Usage

### Simple API Usage

```python
import ft_utils.synchronization as synchronization

# Create an IntervalLock with a 5ms interval
lock = synchronization.IntervalLock(0.005)

# Acquire the lock
lock.lock()

# Do some work
print("Doing some work")

# Cede the lock to any waiters and reset the interval
lock.cede()

# Create a ReaderWriterLock
rw_lock = synchronization.RWLock()

# Acquire the read lock
rw_lock.lock_read()

# Do some work
print("Doing some read work")

# Release the read lock
rw_lock.unlock_read()

# Acquire the write lock
rw_lock.lock_write()

# Do some work
print("Doing some write work")

# Release the write lock
rw_lock.unlock_write()

# Use an RWReadContext to acquire the read lock
with synchronization.RWReadContext(rw_lock) as read_lock:
    print("Doing some read work")

# Use an RWWriteContext to acquire the write lock
with synchronization.RWWriteContext(rw_lock) as write_lock:
    print("Doing some write work")
```

### IntervalLock with contention

```python
import threading
import time
from ft_utils.synchronization import IntervalLock

def worker(lock, name):
    print(f"{name} is waiting to acquire the lock")
    lock.lock()
    print(f"{name} has acquired the lock")
    for i in range(5):
        print(f"{name} is working...")
        time.sleep(0.1)
        lock.poll()  # Check if the interval has expired and cede the lock if necessary
    print(f"{name} has finished working")
    lock.unlock()

lock = IntervalLock(interval=0.2)  # Create an IntervalLock with a 200ms interval

# Create two threads that will contend for the lock
thread1 = threading.Thread(target=worker, args=(lock, "Thread 1"))
thread2 = threading.Thread(target=worker, args=(lock, "Thread 2"))

# Start the threads
thread1.start()
thread2.start()

# Wait for both threads to finish
thread1.join()
thread2.join()
```

In this example, we create two threads that contend for the `IntervalLock`. Each thread acquires the lock, performs some work, and then checks if the interval has expired using the `poll()` method. If the interval has expired, the lock is ceded to the other thread.

### RWLock with contention

```python
import threading
import time
from ft_utils.synchronization import ReaderWriterLock

def reader(lock, name):
    print(f"{name} is waiting to acquire the read lock")
    lock.lock_read()
    print(f"{name} has acquired the read lock")
    for i in range(5):
        print(f"{name} is reading...")
        time.sleep(0.1)
    print(f"{name} has finished reading")
    lock.unlock_read()

def writer(lock, name):
    print(f"{name} is waiting to acquire the write lock")
    lock.lock_write()
    print(f"{name} has acquired the write lock")
    for i in range(5):
        print(f"{name} is writing...")
        time.sleep(0.1)
    print(f"{name} has finished writing")
    lock.unlock_write()

lock = ReaderWriterLock()  # Create a ReaderWriterLock

# Create three threads that will contend for the lock
thread1 = threading.Thread(target=reader, args=(lock, "Reader 1"))
thread2 = threading.Thread(target=reader, args=(lock, "Reader 2"))
thread3 = threading.Thread(target=writer, args=(lock, "Writer"))

# Start the threads
thread1.start()
thread2.start()
thread3.start()

# Wait for all threads to finish
thread1.join()
thread2.join()
thread3.join()
```

In this example, we create three threads that contend for the `ReaderWriterLock`. Two threads are readers that acquire the read lock, perform some reads, and then release the lock. The third thread is a writer that acquires the write lock, performs some writes, and then releases the lock. The `ReaderWriterLock` ensures that the writer has exclusive access to the resource while it holds the write lock, and that multiple readers can access the resource simultaneously while holding the read lock.
