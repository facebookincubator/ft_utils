/* Copyright (c) Meta Platforms, Inc. and affiliates. */

#ifndef TLS_H
#define TLS_H

#include <Python.h>

#ifdef _WIN32
#include <process.h> // @manual
#include <windows.h>
#else
#include <pthread.h>
#endif

#include <stdio.h>
#include <stdlib.h>

/* Thread, thread local storage and wvls are all heavily used (e.g. TlsGetValue
on Windows). To avoid confusions and collisions this library uses wv* as a
naming convention. For example wvls is Weave Local Storage which is equivalent
to Thead Local Storage. */

#ifdef _WIN32
typedef DWORD wvls_key_t;
#define weave_local __declspec(thread)
#else
typedef pthread_key_t wvls_key_t;
#define weave_local _Thread_local
#endif

/* A function called with a value of a thread local variable which is assumed to
   be a pointer to some structure which needs to be freed just before thread
   death. This function must not call into the Python interpreter in any way
   because we cannot guarantee any part of Python will be valid during the call.
 */
typedef void (*wvls_destructor_t)(void*);

/* A platform independent way of creating a thead local storage key which can be
   used to access thread local storage and/or to register a destructor. Note
   that we can in general assume in Python that just marking a variable
   thread_local is good enough and we do not need these low level constructs
   other than to support destructors and other more complex concepts.*/
int wvls_key_create(wvls_key_t* key, wvls_destructor_t destructor);

/* A platform independent way of deleting a tls key. */
int wvls_key_delete(wvls_key_t key);

/* A platform independent way of setting a tls value for a key. */
int wvls_set_value(wvls_key_t key, void* value);

/* A platform independent way of getting a tls value for a key. */
void* wvls_get_value(wvls_key_t key);

/* Register a destructor function to run on thread death which will be passed
   the value of wvls_variable_ptr so that the structure pointed to by this value
   can be freed or other actions taken. See the description of wvls_destructor_t
   for more details. Note that this can be called multiple times and if
   unregister_wvls_destructor is not called in between then all each destructor
   callback will be honoured in the order they were added.*/
void register_wvls_destructor(
    void** wvls_variable_ptr,
    wvls_destructor_t destructor);

/* Remove all destructor callbacks for the given thread local storage position.
Returns 1 if a destructor was found and 0 if not. */
int unregister_wvls_destructor(void** wvls_variable_ptr);

/* Below we have a number of static methods which is unusual in a header. The
   reason is to avoid linking between shared objects and/or multiple different
   definitions of the methods at link time. This approach ensures each
   translation unit has its own version of the functions and these are not
   visible outside the translation unit at link time. */

/* Shared function to check initialization of the Python interpreter */
// NOLINTNEXTLINE
static inline void _py_check_init_interpreter() {
  if (!Py_IsInitialized()) {
    fprintf(stderr, "Python Not Initialized.\n");
    abort();
  }
}

/* Shared function to import a module and get a function from it */
// NOLINTNEXTLINE
static inline PyObject* _py_get_function(
    const char* module_name,
    const char* function_name) {
  PyObject* pName = PyUnicode_FromString(module_name);
  if (!pName) {
    return NULL;
  }
  PyObject* pModule = PyImport_Import(pName);
  Py_DECREF(pName);
  if (!pModule) {
    return NULL;
  }
  PyObject* pFunc = PyObject_GetAttrString(pModule, function_name);
  Py_DECREF(pModule);
  return pFunc;
}

/* A function to call from the C ABI which will use the Python interpreter to
   register a destructor. This allow the use of this header only in other
   modules and prevents inter-extension runtime communication other than through
   Python itself.  Returns zero on success, one on failure.*/
// NOLINTNEXTLINE
static int _py_register_wvls_destructor(
    void** wvls_var,
    wvls_destructor_t wvls_destructor) {
  PyObject* p_var = NULL;
  PyObject* p_destructor = NULL;
  PyObject* p_func = NULL;
  PyObject* p_args = NULL;
  PyObject* p_result = NULL;

  _py_check_init_interpreter();

  int ret_val = 1;

  p_var = PyLong_FromVoidPtr((void*)wvls_var);
  if (!p_var) {
    goto cleanup;
  }

  p_destructor = PyLong_FromVoidPtr((void*)wvls_destructor);
  if (!p_var) {
    goto cleanup;
  }

  p_func = _py_get_function("ft_utils.weave", "register_native_destructor");
  if (!p_func) {
    goto cleanup;
  }

  p_args = PyTuple_Pack(2, p_var, p_destructor);
  if (!p_args) {
    goto cleanup;
  }

  p_result = PyObject_CallObject(p_func, p_args);
  if (!p_result) {
    goto cleanup;
  }

  ret_val = 0;

cleanup:
  Py_XDECREF(p_var);
  Py_XDECREF(p_destructor);
  Py_XDECREF(p_func);
  Py_XDECREF(p_args);
  Py_XDECREF(p_result);
  return ret_val;
}

/* The equivalent for _py_register_wvls_destructor but calls
unregister_native_destructor. It will set *unregistered to 1 if a destructor was
removed other wise this will be set to 0. Returns zero on success, one on
failure. */
// NOLINTNEXTLINE
static int _py_unregister_wvls_destructor(void** wvls_var, int* unregistered) {
  PyObject* p_var = NULL;
  PyObject* p_func = NULL;
  PyObject* p_args = NULL;
  PyObject* p_result = NULL;

  _py_check_init_interpreter();

  int ret_val = 1;

  p_var = PyLong_FromVoidPtr((void*)wvls_var);
  if (!p_var) {
    goto cleanup;
  }

  p_func = _py_get_function("ft_utils.weave", "unregister_native_destructor");
  if (!p_func) {
    goto cleanup;
  }

  p_args = PyTuple_Pack(1, p_var);
  if (!p_args) {
    goto cleanup;
  }

  p_result = PyObject_CallObject(p_func, p_args);

  if (!p_result) {
    goto cleanup;
  }

  *unregistered = PyObject_IsTrue(p_result);
  ret_val = 0;

cleanup:
  Py_XDECREF(p_var);
  Py_XDECREF(p_func);
  Py_XDECREF(p_args);
  Py_XDECREF(p_result);
  return ret_val;
}

#endif
