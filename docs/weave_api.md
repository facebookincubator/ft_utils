# weave Module Documentation

The weave module is for advanced, specialist thread manipulation features.

## Python API

The following two functions are intended to be called from native code (see `ft_weave.h` below). They take integer arguments where those integers are actually native pointer values which should be created via calling `PyLong_FromVoidPtr`.

* `register_native_destructor(var: int, destructor: int) -> None`: Takes a pointer to a `thread_local void *` and a pointer to a `wvls_destructor_t` function. It registers the function as the destructor for the thread_local var. **Requires `ft_utils.ENABLE_EXPERIMENTAL = True`**
* `unregister_native_destructor(var: int) -> None`: Takes a pointer to a `thread_local void *` and unregisters all thread local destructors registered against this thead_local. **Requires `ft_utils.ENABLE_EXPERIMENTAL = True`**

## Native API

`ft_weave.h` provides a header only implementation which in conjuction with having weave imported into the Python VM will permit access to weave's advanced threading features. The functions in the header will attempt to import ft_utils.weave if required.

* `weave_local`: A type modifier to mark a variable as using thread local storage. This name was chosen to avoid clashing with names such as thread_local in thread.h on Linux. However, when a compiler or header is used which correctly defines thread_local, then weave_local is redundant and you can use either with weave. For example `static weave_local void* tls_2 = NULL;`.
* `typedef void (*wvls_destructor_t)(void*)`: A function called with a value of a thread local variable which is assumed to be a pointer to some structure which needs to be freed just before thread death. This function must not call into the Python interpreter in any way because we cannot guarantee any part of Python will be valid during the call.
* `void _py_register_wvls_destructor(void** wvls_var, wvls_destructor_t wvls_destructor)`: Register a destructor function to run on thread death which will be passed the value of wvls_var so that the structure pointed to by this value can be freed or other actions taken. See the description of wvls_destructor_t for more details. Note that this can be called multiple times and if `_py_unregister_wvls_destructor` is not called in between then each destructor callback will be honoured in the order they were added. This function calls back into Python to then call the register in the native code of `ft_utils.weave` so that no native linking is required to the `ft_utils._weave` libraries. **Requires `ft_utils.ENABLE_EXPERIMENTAL = True`**
* `void _py_unregister_wvls_destructor(void** wvls_var, wvls_destructor_t wvls_destructor)`: Remove all destructor callbacks for the given thread local storage position. Returns True if a destructor was found and False if not. See `_py_register_wvls_destructor` regarding the way this works with Python and linking. **Requires `ft_utils.ENABLE_EXPERIMENTAL = True`**

### Thread-local storage

Note that automatic thread-local storage (`weave_local`) variables should not be stored within dynamic thread-local storage (`_py_register_wvls_destructor`). This is because it is not guaranteed that `weave_local` variables will maintain their value when the `wvls_destructor_t` function is called. (For example on macOS — depending on many factors — it is possible for `weave_local` variables to return to their default values before the destructor callback is called.)
