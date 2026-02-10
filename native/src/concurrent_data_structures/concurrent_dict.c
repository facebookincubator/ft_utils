/* Copyright (c) Meta Platforms, Inc. and affiliates. */

#include "ft_utils.h"

#include "concurrent_dict.h"

typedef struct {
  PyObject_HEAD PyObject** buckets;
  Py_ssize_t size;
  PyObject* weakreflist;
} ConcurrentDictObject;

static int ConcurrentDict_clear(ConcurrentDictObject* self) {
  if (self->buckets) {
    for (Py_ssize_t i = 0; i < self->size; i++) {
      Py_CLEAR(self->buckets[i]);
    }
    PyMem_Free(self->buckets);
    self->buckets = NULL;
    self->size = 0;
  }
  return 0;
}

static void ConcurrentDict_dealloc(ConcurrentDictObject* self) {
  PyObject_GC_UnTrack(self);
  ConcurrentDict_clear(self);
  PyObject_ClearWeakRefs((PyObject*)self);
  PyObject_GC_Del(self);
}

static PyObject*
ConcurrentDict_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
  Py_ssize_t initial_capacity = 17;
  static char* kwlist[] = {"initial_capacity", NULL};

  if (!PyArg_ParseTupleAndKeywords(
          args, kwds, "|n", kwlist, &initial_capacity)) {
    return NULL;
  }

  ConcurrentDictObject* self = (ConcurrentDictObject*)type->tp_alloc(type, 0);
  if (self != NULL) {
    self->buckets =
        (PyObject**)PyMem_Calloc(initial_capacity, sizeof(PyObject*));
    if (!self->buckets) {
      PyErr_NoMemory();
      Py_DECREF(self);
      return NULL;
    }

    self->size = initial_capacity;
    for (Py_ssize_t i = 0; i < initial_capacity; i++) {
      self->buckets[i] = PyDict_New();
      if (!self->buckets[i]) {
        Py_DECREF(self);
        return NULL;
      }
    }
  }
  return (PyObject*)self;
}

static PyObject* ConcurrentDict_getitem(
    ConcurrentDictObject* self,
    PyObject* key) {
  Py_hash_t hash = PyObject_Hash(key);
  if (hash == -1 && PyErr_Occurred()) {
    return NULL;
  }

  Py_ssize_t index = hash % self->size;
  if (index < 0) {
    index = -index;
  }

  PyObject* value = NULL;
  int result = PyDict_GetItemRef(self->buckets[index], key, &value);
  if (result < 0) {
    return NULL;
  } else if (result == 0) {
    PyErr_SetObject(PyExc_KeyError, key);
    return NULL;
  }

  return value;
}

static int ConcurrentDict_setitem(
    ConcurrentDictObject* self,
    PyObject* key,
    PyObject* value) {
  Py_hash_t hash = PyObject_Hash(key);
  if (hash == -1 && PyErr_Occurred()) {
    return -1;
  }

  Py_ssize_t index = hash % self->size;
  if (index < 0) {
    index = -index;
  }

  if (value == NULL) {
    if (PyDict_DelItem(self->buckets[index], key) < 0) {
      return -1;
    }
  } else {
    if (PyDict_SetItem(self->buckets[index], key, value) < 0) {
      return -1;
    }
  }
  return 0;
}

static int ConcurrentDict_contains(ConcurrentDictObject* self, PyObject* key) {
  Py_hash_t hash = PyObject_Hash(key);
  if (hash == -1 && PyErr_Occurred()) {
    return -1;
  }

  Py_ssize_t index = hash % self->size;
  if (index < 0) {
    index = -index;
  }

  return PyDict_Contains(self->buckets[index], key);
}

static PyObject* ConcurrentDict_as_dict(
    ConcurrentDictObject* self,
    PyObject* Py_UNUSED(args)) {
  PyObject* dict = PyDict_New();
  if (!dict) {
    return NULL;
  }
  for (Py_ssize_t i = 0; i < self->size; i++) {
    if (self->buckets[i]) {
      if (PyDict_Update(dict, self->buckets[i]) != 0) {
        Py_DECREF(dict);
        return NULL;
      }
    }
  }
  return dict;
}

static int ConcurrentDict_traverse(
    ConcurrentDictObject* self,
    visitproc visit,
    void* arg) {
  Py_ssize_t i;
  for (i = 0; i < self->size; i++) {
    Py_VISIT(self->buckets[i]);
  }
  return 0;
}

static Py_ssize_t ConcurrentDict_len(ConcurrentDictObject* self) {
  Py_ssize_t total = 0;
  for (Py_ssize_t i = 0; i < self->size; i++) {
    if (self->buckets[i]) {
      total += PyDict_Size(self->buckets[i]);
    }
  }
  return total;
}

static PyMappingMethods ConcurrentDict_mapping = {
    (lenfunc)ConcurrentDict_len, // mp_length
    (binaryfunc)ConcurrentDict_getitem, // mp_subscript
    (objobjargproc)ConcurrentDict_setitem, // mp_ass_subscript
};

static PySequenceMethods ConcurrentDict_sequence = {
    .sq_contains = (objobjproc)ConcurrentDict_contains,
};

static PyMethodDef ConcurrentDict_methods[] = {
    {"as_dict",
     (PyCFunction)ConcurrentDict_as_dict,
     METH_NOARGS,
     PyDoc_STR(
         "Create a dict from the key value pairs in this ConcurrentDict. Not thread consistent.")},
    {NULL, NULL, 0, NULL}};

PyTypeObject ConcurrentDictType = {
    PyVarObject_HEAD_INIT(NULL, 0).tp_name = "_concurrency.ConcurrentDict",
    .tp_doc = "Concurrent Dictionary",
    .tp_basicsize = sizeof(ConcurrentDictObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC,
    .tp_as_mapping = &ConcurrentDict_mapping,
    .tp_as_sequence = &ConcurrentDict_sequence,
    .tp_methods = ConcurrentDict_methods,
    .tp_new = ConcurrentDict_new,
    .tp_dealloc = (destructor)ConcurrentDict_dealloc,
    .tp_traverse = (traverseproc)ConcurrentDict_traverse,
    .tp_clear = (inquiry)ConcurrentDict_clear,
    .tp_weaklistoffset = offsetof(ConcurrentDictObject, weakreflist),
};
