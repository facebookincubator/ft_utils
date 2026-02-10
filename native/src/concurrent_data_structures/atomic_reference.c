/* Copyright (c) Meta Platforms, Inc. and affiliates. */

#include "ft_utils.h"

#include "atomic_reference.h"

typedef struct {
  PyObject_HEAD PyObject* ref;
  PyObject* weakreflist;
} AtomicReferenceObject;

static PyObject*
atomicreference_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
  if (PyTuple_GET_SIZE(args) > 1) {
    PyErr_SetString(
        PyExc_TypeError, "AtomicReference() takes zero or one argument");
    return NULL;
  }

  AtomicReferenceObject* self = (AtomicReferenceObject*)type->tp_alloc(type, 0);
  if (self == NULL) {
    return NULL;
  }

  self->weakreflist = NULL;
  if (PyTuple_GET_SIZE(args) == 1) {
    PyObject* obj = PyTuple_GET_ITEM(args, 0);
    self->ref = obj;
  } else {
    self->ref = Py_None;
  }
  ConcurrentRegisterReference(self->ref);
  Py_INCREF(self->ref);
  return (PyObject*)self;
}

static int atomicreference_clear(AtomicReferenceObject* self) {
  Py_CLEAR(self->ref);
  return 0;
}

static void atomicreference_dealloc(AtomicReferenceObject* self) {
  PyObject_GC_UnTrack(self);
  atomicreference_clear(self);
  PyObject_ClearWeakRefs((PyObject*)self);
  PyObject_GC_Del(self);
}

static int atomicreference_traverse(
    AtomicReferenceObject* self,
    visitproc visit,
    void* arg) {
  Py_VISIT(_Py_atomic_load_ptr(&self->ref));
  return 0;
}

static PyObject* atomicreference_get(AtomicReferenceObject* self) {
  return ConcurrentGetNewReference(&self->ref);
}

static PyObject* atomicreference_exchange(
    AtomicReferenceObject* self,
    PyObject* obj) {
  ConcurrentRegisterReference(obj);
  Py_INCREF(obj);
  return _Py_atomic_exchange_ptr(&self->ref, obj);
}

static PyObject* atomicreference_set(
    AtomicReferenceObject* self,
    PyObject* obj) {
  ConcurrentRegisterReference(obj);
  Py_INCREF(obj);
  PyObject* ret = _Py_atomic_exchange_ptr(&self->ref, obj);
  Py_DECREF(ret);
  Py_RETURN_NONE;
}

static PyObject* atomicreference_compare_exchange(
    AtomicReferenceObject* self,
    PyObject* args) {
  PyObject* expected;
  PyObject* obj;
  if (!PyArg_ParseTuple(args, "OO", &expected, &obj)) {
    return NULL;
  }
  ConcurrentRegisterReference(obj);
  Py_INCREF(obj);
  if (!_Py_atomic_compare_exchange_ptr(&self->ref, &expected, obj)) {
    Py_DECREF(obj);
    Py_RETURN_FALSE;
  }
  Py_DECREF(expected);
  Py_RETURN_TRUE;
}

static PyMethodDef AtomicReference_methods[] = {
    {"set", (PyCFunction)atomicreference_set, METH_O},
    {"get", (PyCFunction)atomicreference_get, METH_NOARGS},
    {"exchange", (PyCFunction)atomicreference_exchange, METH_O},
    {"compare_exchange",
     (PyCFunction)atomicreference_compare_exchange,
     METH_VARARGS},
    {NULL}};

PyTypeObject AtomicReferenceType = {
    PyVarObject_HEAD_INIT(NULL, 0).tp_name = "_concurrency.AtomicReference",
    .tp_basicsize = sizeof(AtomicReferenceObject),
    .tp_dealloc = (destructor)atomicreference_dealloc,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC,
    .tp_doc = "AtomicReference",
    .tp_traverse = (traverseproc)atomicreference_traverse,
    .tp_clear = (inquiry)atomicreference_clear,
    .tp_methods = AtomicReference_methods,
    .tp_new = atomicreference_new,
    .tp_weaklistoffset = offsetof(AtomicReferenceObject, weakreflist),
};
