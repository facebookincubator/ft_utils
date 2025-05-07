![Image](https://github.com/user-attachments/assets/f4ef78b9-8cc0-4264-971f-d6ac76884f3a)
# local Module Documentation

## Classes

### LocalWrapper

A LocalWrapper is a class that wraps an object and provides thread-local access to it. It is designed to prevent shared references to the wrapped object from being incremented or decremented, which can improve performance in multi-threaded applications. Local code (e.g. that in a method) can make a LocalWrapper around an object which will be shared amongst many threads. If the programmer prevents the LocalWrapper instance being shared between many threads then its reference count will remain thread local and therefore avoid contention on the reference count of the more global object. Garbage collection is achieved in the normal manner with the reference count of the wrapped object only being changed on construction of the LocalWrapper, on destruction of the LocalWrapper, or in some cases if LocalWrapper is unable to access a member of the wrapped object without invoking the interpreter.

#### Methods

* `__init__(wrapped: object)`: Initializes a LocalWrapper with the given wrapped object.

Note that the rest of the methods are transparent proxies for the methods in the wrapped object.

#### Properties

* `wrapped`: The object being wrapped; read only.

### BatchExecutor

A BatchExecutor is a class that executes a callable in one thread and stores the results in a buffer, which can then be accessed efficiently from multiple threads.

It is designed to avoid the high cost of contention on a critical section and of migration of state between threads. Creation of state is done in one thread at a time and stored in an atomic list which can then efficiently be accessed by multiple threads.

#### Methods

* `__init__(source: callable, size: int)`: Initializes a BatchExecutor with the given source callable and buffer size.
* `load()`: Returns the next result from the buffer, executing the source callable if necessary to fill the buffer.
* `as_local()`: Returns a new LocalWrapper instance initialized with this BatchExecutor.

## Example Usage

```python
import ft_utils.local as local
import uuid

def generate_guid():
    return uuid.uuid4()

# Create a BatchExecutor for generating GUIDs
batch_executor = local.BatchExecutor(generate_guid, 10)

# Define a generator function that calls the LocalWrapper 10 times
def generate_guids():
    # Create a LocalWrapper around the BatchExecutor
    local_wrapper = local.LocalWrapper(batch_executor)
    for _ in range(10):
        yield local_wrapper.load()

# Use the generator function to print 10 GUIDs
for guid in generate_guids():
    print(guid)
```
