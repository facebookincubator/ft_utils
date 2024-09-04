/* Copyright (c) Meta Platforms, Inc. and affiliates. */
#include "ft_utils.h"

#ifndef Py_ATOMIC_H

#define _PyObject_SetMaybeWeakref(_x) // Noop

static inline PyObject* _Py_XGetRef(PyObject** obj_ptr) {
  Py_INCREF(*obj_ptr);
  return *obj_ptr;
}

static inline int _Py_TryIncrefCompare(PyObject** obj_ptr, PyObject* expected) {
  return *obj_ptr == expected ? (Py_INCREF(*obj_ptr), 1) : 0;
}
#endif

#define Py_BUILD_CORE
#include "pycore_object.h" // @manual
#undef Py_BUILD_CORE

void ConcurrentRegisterReference(PyObject* obj) {
  _PyObject_SetMaybeWeakref(obj);
}

PyObject* ConcurrentGetNewReference(PyObject** obj_ptr) {
  PyObject* ret = _Py_XGetRef(obj_ptr);
  if (ret == NULL) {
    abort();
  }
  return ret;
}

PyObject* ConcurrentXGetNewReference(PyObject** obj_ptr) {
  PyObject* ret = _Py_XGetRef(obj_ptr);
  return ret;
}

int ConcurrentTryIncReference(PyObject** obj_ptr, PyObject* expected) {
  return _Py_TryIncrefCompare(obj_ptr, expected);
}
