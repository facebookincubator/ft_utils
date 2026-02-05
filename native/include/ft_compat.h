/* Copyright (c) Meta Platforms, Inc. and affiliates. */

#ifndef FT_COMPAT_H
#define FT_COMPAT_H
#include <Python.h>

#if PY_VERSION_HEX >= 0x030D0000
#define _PY_NOGIL_MODULE_SLOT {Py_mod_gil, Py_MOD_GIL_NOT_USED},
#else
#define _PY_NOGIL_MODULE_SLOT

// NOLINTNEXTLINE
static inline int
PyDict_GetItemRef(PyObject* p, PyObject* key, PyObject** result) {
  PyObject* value = PyDict_GetItem(p, key);
  if (PyErr_Occurred()) {
    *result = NULL;
    return -1;
  }

  if (value == NULL) {
    *result = NULL;
    return 0;
  }
  *result = Py_NewRef(value);
  return 1;
}
#endif /* PY_VERSION_HEX */

#ifndef Py_ATOMIC_H
#define Py_BEGIN_CRITICAL_SECTION(self) {
#define Py_END_CRITICAL_SECTION() }

#define CREATE_PY_ATOMIC_STORE(name, type, suffix)                            \
  static inline void _Py_atomic_store_##name##suffix(type* obj, type value) { \
    *obj = value;                                                             \
  }
CREATE_PY_ATOMIC_STORE(ssize, Py_ssize_t, )
CREATE_PY_ATOMIC_STORE(intptr, intptr_t, )
CREATE_PY_ATOMIC_STORE(uintptr, uintptr_t, )
CREATE_PY_ATOMIC_STORE(uint, unsigned int, )
CREATE_PY_ATOMIC_STORE(ptr, void*, )
CREATE_PY_ATOMIC_STORE(int, int, _relaxed)
CREATE_PY_ATOMIC_STORE(int8, int8_t, _relaxed)
CREATE_PY_ATOMIC_STORE(uint8, uint8_t, _relaxed)
CREATE_PY_ATOMIC_STORE(int16, int16_t, _relaxed)
CREATE_PY_ATOMIC_STORE(uint16, uint16_t, _relaxed)
CREATE_PY_ATOMIC_STORE(int32, int32_t, _relaxed)
CREATE_PY_ATOMIC_STORE(uint32, uint32_t, _relaxed)
CREATE_PY_ATOMIC_STORE(int64, int64_t, _relaxed)
CREATE_PY_ATOMIC_STORE(uint64, uint64_t, _relaxed)
CREATE_PY_ATOMIC_STORE(intptr, intptr_t, _relaxed)
CREATE_PY_ATOMIC_STORE(uintptr, uintptr_t, _relaxed)
CREATE_PY_ATOMIC_STORE(uint, unsigned int, _relaxed)
CREATE_PY_ATOMIC_STORE(ptr, void*, _relaxed)
CREATE_PY_ATOMIC_STORE(ssize, Py_ssize_t, _relaxed)
CREATE_PY_ATOMIC_STORE(ullong, unsigned long long, _relaxed)
CREATE_PY_ATOMIC_STORE(ptr, void*, _release)
CREATE_PY_ATOMIC_STORE(uintptr, uintptr_t, _release)
CREATE_PY_ATOMIC_STORE(ssize, Py_ssize_t, _release)
CREATE_PY_ATOMIC_STORE(int, int, _release)
CREATE_PY_ATOMIC_STORE(uint32, uint32_t, _release)
CREATE_PY_ATOMIC_STORE(uint64, uint64_t, _release)
CREATE_PY_ATOMIC_STORE(int64, int64_t, )
CREATE_PY_ATOMIC_STORE(int, int, )
CREATE_PY_ATOMIC_STORE(int8, int8_t, )
CREATE_PY_ATOMIC_STORE(uint8, uint8_t, )
CREATE_PY_ATOMIC_STORE(int16, int16_t, )
CREATE_PY_ATOMIC_STORE(uint16, uint16_t, )
CREATE_PY_ATOMIC_STORE(int32, int32_t, )
CREATE_PY_ATOMIC_STORE(uint32, uint32_t, )
CREATE_PY_ATOMIC_STORE(uint64, uint64_t, )
#undef CREATE_PY_ATOMIC_STORE

#define CREATE_PY_ATOMIC_EXCHANGE(name, type)                            \
  static inline type _Py_atomic_exchange_##name(type* obj, type value) { \
    type old = *obj;                                                     \
    *obj = value;                                                        \
    return old;                                                          \
  }
CREATE_PY_ATOMIC_EXCHANGE(int8, int8_t)
CREATE_PY_ATOMIC_EXCHANGE(uint8, uint8_t)
CREATE_PY_ATOMIC_EXCHANGE(int16, int16_t)
CREATE_PY_ATOMIC_EXCHANGE(uint16, uint16_t)
CREATE_PY_ATOMIC_EXCHANGE(int32, int32_t)
CREATE_PY_ATOMIC_EXCHANGE(uint32, uint32_t)
CREATE_PY_ATOMIC_EXCHANGE(int64, int64_t)
CREATE_PY_ATOMIC_EXCHANGE(uint64, uint64_t)
CREATE_PY_ATOMIC_EXCHANGE(intptr, intptr_t)
CREATE_PY_ATOMIC_EXCHANGE(uintptr, uintptr_t)
CREATE_PY_ATOMIC_EXCHANGE(uint, unsigned int)
CREATE_PY_ATOMIC_EXCHANGE(ssize, Py_ssize_t)
#undef CREATE_PY_ATOMIC_EXCHANGE

// NOLINTNEXTLINE
static inline void* _Py_atomic_exchange_ptr(void* to, void* from) {
  void** ref = (void**)to;
  void* old = *ref;
  *ref = from;
  return old;
}

#define CREATE_PY_ATOMIC_COMPARE_EXCHANGE(name, type)   \
  static inline int _Py_atomic_compare_exchange_##name( \
      type* obj, type* expected, type desired) {        \
    if (*expected == *obj) {                            \
      *obj = desired;                                   \
      return 1;                                         \
    }                                                   \
    return 0;                                           \
  }
CREATE_PY_ATOMIC_COMPARE_EXCHANGE(int, int)
CREATE_PY_ATOMIC_COMPARE_EXCHANGE(int8, int8_t)
CREATE_PY_ATOMIC_COMPARE_EXCHANGE(uint8, uint8_t)
CREATE_PY_ATOMIC_COMPARE_EXCHANGE(int16, int16_t)
CREATE_PY_ATOMIC_COMPARE_EXCHANGE(uint16, uint16_t)
CREATE_PY_ATOMIC_COMPARE_EXCHANGE(int32, int32_t)
CREATE_PY_ATOMIC_COMPARE_EXCHANGE(uint32, uint32_t)
CREATE_PY_ATOMIC_COMPARE_EXCHANGE(int64, int64_t)
CREATE_PY_ATOMIC_COMPARE_EXCHANGE(uint64, uint64_t)
CREATE_PY_ATOMIC_COMPARE_EXCHANGE(intptr, intptr_t)
CREATE_PY_ATOMIC_COMPARE_EXCHANGE(uintptr, uintptr_t)
CREATE_PY_ATOMIC_COMPARE_EXCHANGE(uint, unsigned int)
CREATE_PY_ATOMIC_COMPARE_EXCHANGE(ssize, Py_ssize_t)
#undef CREATE_PY_ATOMIC_COMPARE_EXCHANGE

// NOLINTNEXTLINE
static inline int
_Py_atomic_compare_exchange_ptr(void* obj, void* expected, void* desired) {
  void** vobj = (void**)obj;
  void** vexpected = (void**)expected;
  if (*vexpected == *vobj) {
    *vobj = desired;
    return 1;
  }
  return 0;
}

// NOLINTNEXTLINE
static inline void _Py_atomic_fence_release(void) {
  // NOLINTNEXTLINE
  /* noop; */
}

// NOLINTNEXTLINE
static inline void _Py_atomic_fence_seq_cst(void) {
  /* noop; */
}

// NOLINTNEXTLINE
static inline void _Py_atomic_fence_acquire(void) {
  /* noop; */
}

#define CREATE_PY_ATOMIC_LOAD(name, type, suffix)                      \
  static inline type _Py_atomic_load_##name##suffix(const type* obj) { \
    return *obj;                                                       \
  }

#define CREATE_PY_ATOMIC_LOAD_PTR(name, type, suffix)                   \
  static inline void* _Py_atomic_load_##name##suffix(const type* obj) { \
    return *(void**)obj;                                                \
  }

CREATE_PY_ATOMIC_LOAD(int, int, )
CREATE_PY_ATOMIC_LOAD(int8, int8_t, )
CREATE_PY_ATOMIC_LOAD(uint8, uint8_t, )
CREATE_PY_ATOMIC_LOAD(int16, int16_t, )
CREATE_PY_ATOMIC_LOAD(uint16, uint16_t, )
CREATE_PY_ATOMIC_LOAD(int32, int32_t, )
CREATE_PY_ATOMIC_LOAD(uint32, uint32_t, )
CREATE_PY_ATOMIC_LOAD(int64, int64_t, )
CREATE_PY_ATOMIC_LOAD(uint64, uint64_t, )
CREATE_PY_ATOMIC_LOAD(intptr, intptr_t, )
CREATE_PY_ATOMIC_LOAD(uintptr, uintptr_t, )
CREATE_PY_ATOMIC_LOAD(uint, unsigned int, )
CREATE_PY_ATOMIC_LOAD(ssize, Py_ssize_t, )

CREATE_PY_ATOMIC_LOAD_PTR(ptr, void, )
CREATE_PY_ATOMIC_LOAD_PTR(ptr, void, _relaxed)
CREATE_PY_ATOMIC_LOAD_PTR(ptr, void, _acquire)

CREATE_PY_ATOMIC_LOAD(int, int, _relaxed)
CREATE_PY_ATOMIC_LOAD(int8, int8_t, _relaxed)
CREATE_PY_ATOMIC_LOAD(uint8, uint8_t, _relaxed)
CREATE_PY_ATOMIC_LOAD(int16, int16_t, _relaxed)
CREATE_PY_ATOMIC_LOAD(uint16, uint16_t, _relaxed)
CREATE_PY_ATOMIC_LOAD(int32, int32_t, _relaxed)
CREATE_PY_ATOMIC_LOAD(uint32, uint32_t, _relaxed)
CREATE_PY_ATOMIC_LOAD(int64, int64_t, _relaxed)
CREATE_PY_ATOMIC_LOAD(uint64, uint64_t, _relaxed)
CREATE_PY_ATOMIC_LOAD(intptr, intptr_t, _relaxed)
CREATE_PY_ATOMIC_LOAD(uintptr, uintptr_t, _relaxed)
CREATE_PY_ATOMIC_LOAD(uint, unsigned int, _relaxed)
CREATE_PY_ATOMIC_LOAD(ssize, Py_ssize_t, _relaxed)
CREATE_PY_ATOMIC_LOAD(ullong, unsigned long long, _relaxed)

CREATE_PY_ATOMIC_LOAD(int, int, _acquire)
CREATE_PY_ATOMIC_LOAD(int8, int8_t, _acquire)
CREATE_PY_ATOMIC_LOAD(uint8, uint8_t, _acquire)
CREATE_PY_ATOMIC_LOAD(int16, int16_t, _acquire)
CREATE_PY_ATOMIC_LOAD(uint16, uint16_t, _acquire)
CREATE_PY_ATOMIC_LOAD(int32, int32_t, _acquire)
CREATE_PY_ATOMIC_LOAD(uint32, uint32_t, _acquire)
CREATE_PY_ATOMIC_LOAD(int64, int64_t, _acquire)
CREATE_PY_ATOMIC_LOAD(uint64, uint64_t, _acquire)
CREATE_PY_ATOMIC_LOAD(intptr, intptr_t, _acquire)
CREATE_PY_ATOMIC_LOAD(uintptr, uintptr_t, _acquire)
CREATE_PY_ATOMIC_LOAD(uint, unsigned int, _acquire)
CREATE_PY_ATOMIC_LOAD(ssize, Py_ssize_t, _acquire)
#undef CREATE_PY_ATOMIC_LOAD
#undef CREATE_PY_ATOMIC_LOAD_PTR

#define CREATE_PY_ATOMIC_ADD(name, type)                            \
  static inline type _Py_atomic_add_##name(type* obj, type value) { \
    type old = *obj;                                                \
    *obj += value;                                                  \
    return old;                                                     \
  }
CREATE_PY_ATOMIC_ADD(int, int)
CREATE_PY_ATOMIC_ADD(int8, int8_t)
CREATE_PY_ATOMIC_ADD(int16, int16_t)
CREATE_PY_ATOMIC_ADD(int32, int32_t)
CREATE_PY_ATOMIC_ADD(int64, int64_t)
CREATE_PY_ATOMIC_ADD(intptr, intptr_t)
CREATE_PY_ATOMIC_ADD(uint, unsigned int)
CREATE_PY_ATOMIC_ADD(uint8, uint8_t)
CREATE_PY_ATOMIC_ADD(uint16, uint16_t)
CREATE_PY_ATOMIC_ADD(uint32, uint32_t)
CREATE_PY_ATOMIC_ADD(uint64, uint64_t)
CREATE_PY_ATOMIC_ADD(uintptr, uintptr_t)
CREATE_PY_ATOMIC_ADD(ssize, Py_ssize_t)
#undef CREATE_PY_ATOMIC_ADD

// New
#define CREATE_PY_ATOMIC_AND(name, type)                            \
  static inline type _Py_atomic_and_##name(type* obj, type value) { \
    type old = *obj;                                                \
    *obj &= value;                                                  \
    return old;                                                     \
  }

CREATE_PY_ATOMIC_AND(uint8, uint8_t)
CREATE_PY_ATOMIC_AND(uint16, uint16_t)
CREATE_PY_ATOMIC_AND(uint32, uint32_t)
CREATE_PY_ATOMIC_AND(uint64, uint64_t)
CREATE_PY_ATOMIC_AND(uintptr, uintptr_t)

#undef CREATE_PY_ATOMIC_AND

#define CREATE_PY_ATOMIC_OR(name, type)                            \
  static inline type _Py_atomic_or_##name(type* obj, type value) { \
    type old = *obj;                                               \
    *obj |= value;                                                 \
    return old;                                                    \
  }

CREATE_PY_ATOMIC_OR(uint8, uint8_t)
CREATE_PY_ATOMIC_OR(uint16, uint16_t)
CREATE_PY_ATOMIC_OR(uint32, uint32_t)
CREATE_PY_ATOMIC_OR(uint64, uint64_t)
CREATE_PY_ATOMIC_OR(uintptr, uintptr_t)

#undef CREATE_PY_ATOMIC_OR

#endif /* Py_ATOMIC_H */
#endif /* FT_COMPAT_H */
