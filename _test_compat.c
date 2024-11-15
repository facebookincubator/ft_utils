/* Copyright (c) Meta Platforms, Inc. and affiliates. */

#include "ft_compat.h"

typedef struct {
  PyObject_HEAD
} TestCompatObject;

#define ATOMIC_OPS(X)                                        \
  X(load_ptr, void*, , LOAD)                                 \
  X(store_ptr, void*, , STORE)                               \
  X(exchange_ptr, void*, , EXCHANGE)                         \
  X(compare_exchange_ptr, void*, , COMPARE_EXCHANGE)         \
  X(load_int16, int16_t, , LOAD)                             \
  X(store_int16, int16_t, , STORE)                           \
  X(exchange_int16, int16_t, , EXCHANGE)                     \
  X(compare_exchange_int16, int16_t, , COMPARE_EXCHANGE)     \
  X(load_int32, int32_t, , LOAD)                             \
  X(store_int32, int32_t, , STORE)                           \
  X(exchange_int32, int32_t, , EXCHANGE)                     \
  X(compare_exchange_int32, int32_t, , COMPARE_EXCHANGE)     \
  X(load_int64, int64_t, , LOAD)                             \
  X(store_int64, int64_t, , STORE)                           \
  X(exchange_int64, int64_t, , EXCHANGE)                     \
  X(compare_exchange_int64, int64_t, , COMPARE_EXCHANGE)     \
  X(load_uint8, uint8_t, , LOAD)                             \
  X(store_uint8, uint8_t, , STORE)                           \
  X(exchange_uint8, uint8_t, , EXCHANGE)                     \
  X(compare_exchange_uint8, uint8_t, , COMPARE_EXCHANGE)     \
  X(load_uint16, uint16_t, , LOAD)                           \
  X(store_uint16, uint16_t, , STORE)                         \
  X(exchange_uint16, uint16_t, , EXCHANGE)                   \
  X(compare_exchange_uint16, uint16_t, , COMPARE_EXCHANGE)   \
  X(load_uint32, uint32_t, , LOAD)                           \
  X(store_uint32, uint32_t, , STORE)                         \
  X(exchange_uint32, uint32_t, , EXCHANGE)                   \
  X(compare_exchange_uint32, uint32_t, , COMPARE_EXCHANGE)   \
  X(load_uint64, uint64_t, , LOAD)                           \
  X(store_uint64, uint64_t, , STORE)                         \
  X(exchange_uint64, uint64_t, , EXCHANGE)                   \
  X(compare_exchange_uint64, uint64_t, , COMPARE_EXCHANGE)   \
  X(load_ssize, Py_ssize_t, , LOAD)                          \
  X(store_ssize, Py_ssize_t, , STORE)                        \
  X(exchange_ssize, Py_ssize_t, , EXCHANGE)                  \
  X(compare_exchange_ssize, Py_ssize_t, , COMPARE_EXCHANGE)  \
  X(load_uint, unsigned int, _relaxed, LOAD)                 \
  X(store_uint, unsigned int, _relaxed, STORE)               \
  X(load_ptr, void*, _relaxed, LOAD)                         \
  X(store_ptr, void*, _relaxed, STORE)                       \
  X(load_int, int, _relaxed, LOAD)                           \
  X(load_int, int, _acquire, LOAD)                           \
  X(store_int, int, , STORE)                                 \
  X(store_int, int, _release, STORE)                         \
  X(load_ptr, void*, _acquire, LOAD)                         \
  X(store_ptr, void*, _release, STORE)                       \
  X(fence_seq_cst, void, , FENCE)                            \
  X(fence_release, void, , FENCE)                            \
  X(store_intptr, intptr_t, , STORE)                         \
  X(store_uintptr, uintptr_t, , STORE)                       \
  X(store_uint, unsigned int, , STORE)                       \
  X(store_int8, int8_t, _relaxed, STORE)                     \
  X(store_uint8, uint8_t, _relaxed, STORE)                   \
  X(store_int16, int16_t, _relaxed, STORE)                   \
  X(store_uint16, uint16_t, _relaxed, STORE)                 \
  X(store_int32, int32_t, _relaxed, STORE)                   \
  X(store_uint32, uint32_t, _relaxed, STORE)                 \
  X(store_int64, int64_t, _relaxed, STORE)                   \
  X(store_uint64, uint64_t, _relaxed, STORE)                 \
  X(store_intptr, intptr_t, _relaxed, STORE)                 \
  X(store_uintptr, uintptr_t, _relaxed, STORE)               \
  X(store_ssize, Py_ssize_t, _relaxed, STORE)                \
  X(store_ullong, unsigned long long, _relaxed, STORE)       \
  X(exchange_int8, int8_t, , EXCHANGE)                       \
  X(exchange_intptr, intptr_t, , EXCHANGE)                   \
  X(exchange_uintptr, uintptr_t, , EXCHANGE)                 \
  X(exchange_uint, unsigned int, , EXCHANGE)                 \
  X(compare_exchange_int, int, , COMPARE_EXCHANGE)           \
  X(compare_exchange_int8, int8_t, , COMPARE_EXCHANGE)       \
  X(compare_exchange_uint, unsigned int, , COMPARE_EXCHANGE) \
  X(compare_exchange_intptr, intptr_t, , COMPARE_EXCHANGE)   \
  X(compare_exchange_uintptr, uintptr_t, , COMPARE_EXCHANGE) \
  X(load_uintptr, uintptr_t, _acquire, LOAD)                 \
  X(store_uintptr, uintptr_t, _release, STORE)               \
  X(store_ssize, Py_ssize_t, _release, STORE)                \
  X(store_uint32, uint32_t, _release, STORE)                 \
  X(store_uint64, uint64_t, _release, STORE)                 \
  X(load_uint64, uint64_t, _acquire, LOAD)                   \
  X(load_uint32, uint32_t, _acquire, LOAD)                   \
  X(load_ssize, Py_ssize_t, _acquire, LOAD)                  \
  X(load_int32, int32_t, _relaxed, LOAD)                     \
  X(load_int8, int8_t, , LOAD)                               \
  X(load_intptr, intptr_t, , LOAD)                           \
  X(load_uintptr, uintptr_t, , LOAD)                         \
  X(load_uint, unsigned int, , LOAD)                         \
  X(load_int8, int8_t, _relaxed, LOAD)                       \
  X(load_int16, int16_t, _relaxed, LOAD)                     \
  X(load_uint16, uint16_t, _relaxed, LOAD)                   \
  X(load_uint32, uint32_t, _relaxed, LOAD)                   \
  X(load_intptr, intptr_t, _relaxed, LOAD)                   \
  X(load_uintptr, uintptr_t, _relaxed, LOAD)                 \
  X(load_ssize, Py_ssize_t, _relaxed, LOAD)                  \
  X(load_ullong, unsigned long long, _relaxed, LOAD)         \
  X(store_int8, int8_t, , STORE)                             \
  X(load_int, int, , LOAD)                                   \
  X(add_int, int, , ADD)                                     \
  X(add_int8, int8_t, , ADD)                                 \
  X(add_int16, int16_t, , ADD)                               \
  X(add_int32, int32_t, , ADD)                               \
  X(add_int64, int64_t, , ADD)                               \
  X(add_intptr, intptr_t, , ADD)                             \
  X(add_uint, unsigned int, , ADD)                           \
  X(add_uint8, uint8_t, , ADD)                               \
  X(add_uint16, uint16_t, , ADD)                             \
  X(add_uint32, uint32_t, , ADD)                             \
  X(add_uint64, uint64_t, , ADD)                             \
  X(add_uintptr, uintptr_t, , ADD)                           \
  X(add_ssize, Py_ssize_t, , ADD)                            \
  X(and_uint8, uint8_t, , AND)                               \
  X(and_uint16, uint16_t, , AND)                             \
  X(and_uint32, uint32_t, , AND)                             \
  X(and_uint64, uint64_t, , AND)                             \
  X(and_uintptr, uintptr_t, , AND)                           \
  X(or_uint8, uint8_t, , OR)                                 \
  X(or_uint16, uint16_t, , OR)                               \
  X(or_uint32, uint32_t, , OR)                               \
  X(or_uint64, uint64_t, , OR)                               \
  X(or_uintptr, uintptr_t, , OR)

#define DEFINE_ATOMIC_LOAD_FUNC(name, type, suffix)                     \
  static PyObject* test_atomic_##name##suffix(                          \
      PyObject* self, PyObject* args) {                                 \
    type value = (type)123;                                             \
    type result = _Py_atomic_##name##suffix(&value);                    \
    if (result != value) {                                              \
      PyErr_SetString(                                                  \
          PyExc_AssertionError, "_Py_atomic_" #name #suffix " failed"); \
      return NULL;                                                      \
    }                                                                   \
    Py_RETURN_NONE;                                                     \
  }

#define DEFINE_ATOMIC_STORE_FUNC(name, type, suffix)                    \
  static PyObject* test_atomic_##name##suffix(                          \
      PyObject* self, PyObject* args) {                                 \
    type value = (type)123;                                             \
    type new_value = (type)456;                                         \
    _Py_atomic_##name##suffix(&value, new_value);                       \
    if (value != new_value) {                                           \
      PyErr_SetString(                                                  \
          PyExc_AssertionError, "_Py_atomic_" #name #suffix " failed"); \
      return NULL;                                                      \
    }                                                                   \
    Py_RETURN_NONE;                                                     \
  }

#define DEFINE_ATOMIC_EXCHANGE_FUNC(name, type, suffix)                        \
  static PyObject* test_atomic_##name##suffix(                                 \
      PyObject* self, PyObject* args) {                                        \
    type value = (type)123;                                                    \
    type old_value = (type)123;                                                \
    type new_value = (type)456;                                                \
    type ret = _Py_atomic_##name##suffix(&value, new_value);                   \
    if (value != new_value) {                                                  \
      PyErr_SetString(                                                         \
          PyExc_AssertionError,                                                \
          "_Py_atomic_" #name #suffix " failed exchange");                     \
      return NULL;                                                             \
    }                                                                          \
    if (ret != old_value) {                                                    \
      PyErr_SetString(                                                         \
          PyExc_AssertionError, "_Py_atomic_" #name #suffix " failed return"); \
      return NULL;                                                             \
    }                                                                          \
    Py_RETURN_NONE;                                                            \
  }

#define DEFINE_ATOMIC_AND_FUNC(name, type, suffix)                             \
  static PyObject* test_atomic_##name##suffix(                                 \
      PyObject* self, PyObject* args) {                                        \
    type value = (type)123;                                                    \
    type old_value = (type)123;                                                \
    type to_and = (type)456;                                                   \
    type got = _Py_atomic_##name##suffix(&value, to_and);                      \
    if (got != old_value) {                                                    \
      PyErr_SetString(                                                         \
          PyExc_AssertionError, "_Py_atomic_" #name #suffix " failed return"); \
      return NULL;                                                             \
    }                                                                          \
    old_value &= to_and;                                                       \
    if (value != old_value) {                                                  \
      PyErr_SetString(                                                         \
          PyExc_AssertionError, "_Py_atomic_" #name #suffix " failed and");    \
      return NULL;                                                             \
    }                                                                          \
    Py_RETURN_NONE;                                                            \
  }

#define DEFINE_ATOMIC_OR_FUNC(name, type, suffix)                              \
  static PyObject* test_atomic_##name##suffix(                                 \
      PyObject* self, PyObject* args) {                                        \
    type value = (type)123;                                                    \
    type old_value = (type)123;                                                \
    type to_or = (type)456;                                                    \
    type got = _Py_atomic_##name##suffix(&value, to_or);                       \
    if (got != old_value) {                                                    \
      PyErr_SetString(                                                         \
          PyExc_AssertionError, "_Py_atomic_" #name #suffix " failed return"); \
      return NULL;                                                             \
    }                                                                          \
    old_value |= to_or;                                                        \
    if (value != old_value) {                                                  \
      PyErr_SetString(                                                         \
          PyExc_AssertionError, "_Py_atomic_" #name #suffix " failed or");     \
      return NULL;                                                             \
    }                                                                          \
    Py_RETURN_NONE;                                                            \
  }

#define DEFINE_ATOMIC_ADD_FUNC(name, type, suffix)                             \
  static PyObject* test_atomic_##name##suffix(                                 \
      PyObject* self, PyObject* args) {                                        \
    type value = (type)123;                                                    \
    type old_value = (type)123;                                                \
    type to_add = (type)456;                                                   \
    type got = _Py_atomic_##name##suffix(&value, to_add);                      \
    if (got != old_value) {                                                    \
      PyErr_SetString(                                                         \
          PyExc_AssertionError, "_Py_atomic_" #name #suffix " failed return"); \
      return NULL;                                                             \
    }                                                                          \
    old_value += to_add;                                                       \
    if (value != old_value) {                                                  \
      PyErr_SetString(                                                         \
          PyExc_AssertionError,                                                \
          "_Py_atomic_" #name #suffix " failed addition");                     \
      return NULL;                                                             \
    }                                                                          \
    Py_RETURN_NONE;                                                            \
  }

#define DEFINE_ATOMIC_COMPARE_EXCHANGE_FUNC(name, type, suffix)           \
  static PyObject* test_atomic_##name##suffix(                            \
      PyObject* self, PyObject* args) {                                   \
    type value = (type)123;                                               \
    type new_value = (type)456;                                           \
    type expected = (type)123;                                            \
    int result = _Py_atomic_##name##suffix(&value, &expected, new_value); \
    if (!result || value != new_value) {                                  \
      PyErr_SetString(                                                    \
          PyExc_AssertionError,                                           \
          "_Py_atomic_" #name #suffix " failed succeed");                 \
      return NULL;                                                        \
    }                                                                     \
    value = (type)123;                                                    \
    new_value = (type)456;                                                \
    expected = (type)124;                                                 \
    result = _Py_atomic_##name##suffix(&value, &expected, new_value);     \
    if (result || value == new_value) {                                   \
      PyErr_SetString(                                                    \
          PyExc_AssertionError,                                           \
          "_Py_atomic_" #name #suffix " failed mismatch");                \
      return NULL;                                                        \
    }                                                                     \
    Py_RETURN_NONE;                                                       \
    Py_RETURN_NONE;                                                       \
  }

#define DEFINE_ATOMIC_FENCE_FUNC(name, type, suffix) \
  static PyObject* test_atomic_##name##suffix(       \
      PyObject* self, PyObject* args) {              \
    _Py_atomic_##name##suffix();                     \
    Py_RETURN_NONE;                                  \
  }

#define DEFINE_ATOMIC_TEST_FUNC(name, type, suffix, op) \
  DEFINE_ATOMIC_##op##_FUNC(name, type, suffix)

ATOMIC_OPS(DEFINE_ATOMIC_TEST_FUNC);

/* One of the fence methods is missing from the beta version of ftpython
 * in 3.13. */
#if defined(PY_MAJOR_VERSION) && PY_MAJOR_VERSION == 3 &&  \
    defined(PY_MINOR_VERSION) && PY_MINOR_VERSION == 13 && \
    defined(PY_RELEASE_LEVEL) && PY_RELEASE_LEVEL != PY_RELEASE_LEVEL_FINAL
static PyObject* test_atomic_fence_acquire(PyObject* self, PyObject* args) {
  if (PY_MAJOR_VERSION != 3 || PY_MINOR_VERSION != 13 ||
      PY_RELEASE_LEVEL == PY_RELEASE_LEVEL_FINAL) {
    PyErr_SetString(PyExc_AssertionError, "Version work around failed");
    return NULL;
  }
  Py_RETURN_NONE;
}
#else
static PyObject* test_atomic_fence_acquire(PyObject* self, PyObject* args) {
  _Py_atomic_fence_acquire();
  Py_RETURN_NONE;
}
#endif

#define DEFINE_ATOMIC_METHOD_ENTRY(name, type, suffix, ignore) \
  {"test_atomic_" #name #suffix,                               \
   test_atomic_##name##suffix,                                 \
   METH_NOARGS,                                                \
   "Test _Py_atomic_" #name #suffix},

static PyMethodDef test_compat_methods[] = {
    ATOMIC_OPS(DEFINE_ATOMIC_METHOD_ENTRY){
        "test_atomic_fence_acquire",
        test_atomic_fence_acquire,
        METH_NOARGS,
        "Test _Py_atomic_fence_acquire"},
    {NULL, NULL, 0, NULL} /* sentinel */
};

#undef DEFINE_ATOMIC_METHOD_ENTRY
#undef DEFINE_ATOMIC_TEST_FUNC

static PyTypeObject TestCompat_Type = {
    PyVarObject_HEAD_INIT(NULL, 0).tp_name = "ft_utils.test.TestCompat",
    .tp_basicsize = sizeof(TestCompatObject),
    .tp_new = PyType_GenericNew,
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_alloc = PyType_GenericAlloc,
    .tp_doc = "TestCompat objects",
    .tp_init = NULL,
    .tp_methods = test_compat_methods,
};

static int exec_test_compat_module(PyObject* module) {
  if (PyType_Ready(&TestCompat_Type) < 0) {
    return -1;
  }

  if (PyModule_AddObjectRef(module, "TestCompat", (PyObject*)&TestCompat_Type) <
      0) {
    return -1;
  }

  return 0;
}

static struct PyModuleDef_Slot test_compat_module_slots[] = {
    {Py_mod_exec, exec_test_compat_module},

#if PY_VERSION_HEX >= 0x030D0000
    {Py_mod_gil, Py_MOD_GIL_NOT_USED},
#endif

    {0, NULL} /* sentinel */
};

static PyModuleDef test_compat_module_def = {
    PyModuleDef_HEAD_INIT,
    "test_compat",
    "Test the native compatibility system",
    0,
    NULL,
    test_compat_module_slots,
    NULL,
    NULL,
    NULL};

PyMODINIT_FUNC PyInit__test_compat(void) {
  return PyModuleDef_Init(&test_compat_module_def);
}
