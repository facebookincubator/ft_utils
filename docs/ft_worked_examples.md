# Understanding the Global Interpreter Lock (GIL) and its Impact on Multithreaded Python Programs

## GIL vs Torn Reads
The Global Interpreter Lock (GIL) is a mechanism used in CPython, the default Python implementation, to synchronize access to internal data structures. It prevents multiple threads from executing Python bytecodes at the same time, ensuring that only one thread can execute Python code at any given moment. This lock is necessary because Python's memory management is not thread-safe.

In this document, we will explore how the GIL interacts with bytecodes and discuss the implications of removing the GIL, as proposed in PEP 703, on multithreaded Python programs. We will use the following program as an example:

```python
import threading

power = 10
base = 3.14
result = 1.0

def single_multiply():
    global result
    result *= base

threads = []
for _ in range(power):
    thread = threading.Thread(target=single_multiply)
    thread.start()
    threads.append(thread)

for thread in threads:
    thread.join()

ref_result = 1.0
for _ in range(power):
    ref_result *= base

print("Result = " + str(result))
print("Ref Result = " + str(ref_result))
```

This program creates `power` number of threads, each of which multiplies the global variable `result` by `base`. The main thread then waits for all threads to finish using the `join()` method. Finally, it calculates the reference result by multiplying `base` by itself `power` times and prints both results.

## GIL and Bytecode Execution

The GIL schedules threads based on counting retired bytecodes (and other factors). In Python, each bytecode instruction has a specific "weight" associated with it, which represents the estimated time it takes to execute that instruction. When a thread executes a bytecode instruction, it increments a counter by the weight of that instruction. When the counter reaches a certain threshold, called the "switch interval", the GIL switches to the next thread.

The switch interval is controlled by the `sys.setswitchinterval()` function, which sets the threshold value. By default, the switch interval is set to 5 milliseconds. You can also get the current switch interval using the `sys.getswitchinterval()` function.

Here's an example of how you can modify the switch interval:
```python
import sys

# Get the current switch interval
print(sys.getswitchinterval())

# Set the switch interval to 10 milliseconds
sys.setswitchinterval(0.01)
```
By adjusting the switch interval, you can control how often the GIL switches between threads. A shorter switch interval means more frequent switching, while a longer switch interval means less frequent switching.

**NoGIL and Free Threaded Python**

Now we can remove the GIL, as proposed in PEP 703, the results would always be less consistent, but never use torn reads or writes. Torn reads or writes occur when a variable is stored at a cache line boundary, split between two cache lines. However, since object pointers are never torn, this is not an issue in our example. Note that object pointers are never torn because they are carefully allocated to fit with the current hardware's atomic operation specification which normally means them being cache line aligned.

**Achieving Consistency in Multithreaded Programs**

To achieve consistency in multithreaded programs, developers can use locks or atomic operations, such as `AtomicReference.compare_exchange`. These mechanisms ensure that only one thread can access and modify shared variables at a time, preventing inconsistencies and crashes.

Note that the original program may produce inconsistent results due to the way the GIL schedules threads. To achieve consistent results, you can use locks or atomic operations to synchronize access to shared variables. For example:

## Fake Consistency

Sometimes we can see code with many threads produce exactly the same results as it would if there was only one thread - by accident. We call this 'same results as single threaded' thread consistency. In this section we will look at an example of how both with or without the GIL we can get 'fake consistency' were we thing code is producing consistent results but this is not reliable.

### Inspection At A ByteCode Level
Let's deep dive into the previous example and show how it looks like the GIL makes the code consistent and atomic but it does not.

```python
def single_multiply():
    global result
    result *= base
```

The Python runtime compiles this code into bytecode so let's look at the bytecode for the above function:

```
 0 LOAD_GLOBAL              0 (result)
 2 LOAD_DEREF               0 (base)
 4 INPLACE_MULTIPLY
 6 STORE_GLOBAL             0 (result)
 8 LOAD_CONST               0 (None)
10 RETURN_VALUE
```

In theory the GIL can switch threads at any point between these bytecodes. Most of the time it will not because this is a very short piece of code and because in the example code it is run at the start of a thread. However, in a production system issues like interupt handing or having the program swapped out or stopped (SIGSTOP) could easly cause a thread swap between bytecodes. Consider what happens if we get a thread swap between 4 and 6? This could result in a different thread updating `result` only to have its update overwritten.

**Be warned that programs which appear consistent and atomic due to the GIL often become unstable in complex production systems.**

### Force Inconsistency Then Fix It!

Let's look at a more complex example program. This is visible at [consistent_counter.py](https://github.com/facebookincubator/ft_utils/blob/main/examples/consistent_counter.py). To follow along now please open that file as well as read this document.

The program when run with the GIL turned on gives the following results:

```
Results from a simple example
    Threaded  Result = 93174.3733866435
    Reference Result = 93174.3733866435

Results from a threads tracked example
    Threaded  Result = 93174.3733866435
    Reference Result = 93174.3733866435
Peak theads is 1

Results from a very long load example
    Threaded  Result = 93174.37338664389
    Reference Result = 93174.37338664355
Peak theads is 10

Results from a fully consistent example
    Threaded  Result = 93174.37338664355
    Reference Result = 93174.37338664355
Peak theads is 1
```

'simple example' is just the same logic as in the introduction example above. 'tracked example' shows us the real reason the multi-threaded code gives consistent results: there is only ever one thread running through the function.

When we significantly increase the complexity of the function being called in each thread we see that the threads running in the function go up to 10 in 'long load' example. Even with the GIL the results are no longer consistent. We see most of the time they are near but not quite the same as the order of operations is mixed up across multiple threads. If one runs this program many times then occasionally even more inconsistent results are seen.

The ft_utils.synchronization.IntervalLock fixes this issue whilst still not fully locking the code as a threading.lock would do. This is an example of the usefulness of this lock even in GIL Python. However, let's look at Free Threaded Python.


The program when run with the GIL turned off gives the following results:

```
Results from a simple example
    Threaded  Result = 93174.3733866435
    Reference Result = 93174.3733866435

Results from a threads tracked example
    Threaded  Result = 93174.3733866435
    Reference Result = 93174.3733866435
Peak theads is 1

Results from a very long load example
    Threaded  Result = inf
    Reference Result = 93174.37338664355
Peak theads is 10

Results from a fully consistent example
    Threaded  Result = 93174.37338664355
    Reference Result = 93174.37338664355
Peak theads is 1
```

We can see that even with NoGIL the simple threaded approach still only has one thread at a time running through our function at once. This shows just how easy it is to make code which looks thread consistent but is not!

Next we can look at the code which is unlocked but truly multi-threaded and we can see how we have, as expected, inconsistent results.

Finally, we can see how the interval lock fixes this issue.
