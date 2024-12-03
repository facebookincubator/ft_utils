/* Copyright (c) Meta Platforms, Inc. and affiliates. */

#include "ft_utils.h"

/* Begin ConcurrentDict
 ***********************
 */

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

  PyObject* value = PyDict_GetItem(self->buckets[index], key);
  if (!value) {
    PyErr_SetObject(PyExc_KeyError, key);
    return NULL;
  }

  Py_INCREF(value);
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

static PyMappingMethods ConcurrentDict_mapping = {
    (lenfunc)0, // mp_length
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

static PyTypeObject ConcurrentDictType = {
    PyVarObject_HEAD_INIT(NULL, 0).tp_name = "_concurrent.ConcurrentDict",
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

/* ******************
   End ConcurrentDict
*/

/* Begin AtomicInt64
 *******************
 */

typedef struct {
  PyObject_HEAD int64_t value;
  PyObject* weakreflist;
} AtomicInt64Object;

static PyTypeObject AtomicInt64Type;

static PyObject*
atomicint64_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
  AtomicInt64Object* self;
  int64_t value = 0;

  if (!PyArg_ParseTuple(args, "|L", &value)) {
    return NULL;
  }

  self = (AtomicInt64Object*)type->tp_alloc(type, 0);
  if (self == NULL) {
    return NULL;
  }

  self->weakreflist = NULL;
  _Py_atomic_store_int64(&self->value, value);
  return (PyObject*)self;
}

static int
atomicint64_init(AtomicInt64Object* self, PyObject* args, PyObject* kwds) {
  return 0;
}

static void atomicint64_dealloc(AtomicInt64Object* self) {
  PyObject_ClearWeakRefs((PyObject*)self);
  Py_TYPE(self)->tp_free((PyObject*)self);
}

#define GET_I64_OR_ERROR(other)                                           \
  int64_t value;                                                          \
  do {                                                                    \
    if (PyLong_CheckExact(other)) {                                       \
      value = PyLong_AsLongLong(other);                                   \
    } else if (PyObject_TypeCheck(other, &AtomicInt64Type)) {             \
      value = _Py_atomic_load_int64(&((AtomicInt64Object*)other)->value); \
    } else {                                                              \
      PyErr_SetString(PyExc_TypeError, "unsupported operand type(s)");    \
      return NULL;                                                        \
    }                                                                     \
  } while (0)

static PyObject* atomicint64_add(AtomicInt64Object* self, PyObject* other) {
  GET_I64_OR_ERROR(other);
  return PyLong_FromLongLong(_Py_atomic_load_int64(&self->value) + value);
}

static PyObject* atomicint64_sub(AtomicInt64Object* self, PyObject* other) {
  GET_I64_OR_ERROR(other);
  return PyLong_FromLongLong(_Py_atomic_load_int64(&self->value) - value);
}

static PyObject* atomicint64_mul(AtomicInt64Object* self, PyObject* other) {
  GET_I64_OR_ERROR(other);
  return PyLong_FromLongLong(_Py_atomic_load_int64(&self->value) * value);
}

static PyObject* atomicint64_div(AtomicInt64Object* self, PyObject* other) {
  GET_I64_OR_ERROR(other);
  if (value == 0) {
    PyErr_SetString(PyExc_ZeroDivisionError, "division by zero");
    return NULL;
  }
  return PyLong_FromLongLong(_Py_atomic_load_int64(&self->value) / value);
}

static PyObject* atomicint64_iadd(AtomicInt64Object* self, PyObject* other) {
  GET_I64_OR_ERROR(other);
  _Py_atomic_add_int64(&self->value, value);
  Py_INCREF(self);
  return (PyObject*)self;
}

static PyObject* atomicint64_isub(AtomicInt64Object* self, PyObject* other) {
  GET_I64_OR_ERROR(other);
  atomic_int64_sub(&self->value, value);
  Py_INCREF(self);
  return (PyObject*)self;
}

static PyObject* atomicint64_imul(AtomicInt64Object* self, PyObject* other) {
  GET_I64_OR_ERROR(other);
  atomic_int64_mul(&self->value, value);
  Py_INCREF(self);
  return (PyObject*)self;
}

static PyObject* atomicint64_idiv(AtomicInt64Object* self, PyObject* other) {
  GET_I64_OR_ERROR(other);
  if (value == 0) {
    PyErr_SetString(PyExc_ZeroDivisionError, "division by zero");
    return NULL;
  }

  atomic_int64_div(&self->value, value);
  Py_INCREF(self);
  return (PyObject*)self;
}

static int atomicint64_bool(AtomicInt64Object* self) {
  return _Py_atomic_load_int64(&self->value) != 0;
}

static PyObject* atomicint64_int(AtomicInt64Object* self) {
  return PyLong_FromLongLong(_Py_atomic_load_int64(&self->value));
}

static PyObject* atomicint64_neg(AtomicInt64Object* self) {
  return PyLong_FromLongLong(-_Py_atomic_load_int64(&self->value));
}

static PyObject* atomicint64_pos(AtomicInt64Object* self) {
  return PyLong_FromLongLong(_Py_atomic_load_int64(&self->value));
}

static PyObject* atomicint64_abs(AtomicInt64Object* self) {
  int64_t value = _Py_atomic_load_int64(&self->value);
  if (value < 0) {
    value = -value;
  }
  return PyLong_FromLongLong(value);
}

static PyObject* atomicint64_format(AtomicInt64Object* self, PyObject* args) {
  PyObject* int_obj = atomicint64_int(self);
  if (int_obj == NULL)
    return NULL;

  PyObject* format_spec;
  if (!PyArg_ParseTuple(args, "O", &format_spec))
    return NULL;
  Py_INCREF(format_spec);

  PyObject* result = PyObject_Format(int_obj, format_spec);
  Py_DECREF(int_obj);
  Py_DECREF(format_spec);

  return result;
}

static PyObject*
atomicint64_richcompare(AtomicInt64Object* self, PyObject* other, int op) {
  PyObject* int_obj = atomicint64_int(self);
  if (int_obj == NULL)
    return NULL;

  int result = PyObject_RichCompareBool(int_obj, other, op);
  Py_DECREF(int_obj);

  if (result == -1)
    return NULL;
  else
    return PyBool_FromLong(result);
}

static PyObject* atomicint64_ior(AtomicInt64Object* self, PyObject* other) {
  GET_I64_OR_ERROR(other);

  atomic_int64_or(&self->value, value);
  Py_INCREF(self);
  return (PyObject*)self;
}

static PyObject* atomicint64_ixor(AtomicInt64Object* self, PyObject* other) {
  GET_I64_OR_ERROR(other);

  atomic_int64_xor(&self->value, value);
  Py_INCREF(self);
  return (PyObject*)self;
}

static PyObject* atomicint64_iand(AtomicInt64Object* self, PyObject* other) {
  GET_I64_OR_ERROR(other);

  atomic_int64_and(&self->value, value);
  Py_INCREF(self);
  return (PyObject*)self;
}

static PyObject* atomicint64_or(AtomicInt64Object* self, PyObject* other) {
  GET_I64_OR_ERROR(other);

  return PyLong_FromLongLong(_Py_atomic_load_int64(&self->value) | value);
}

static PyObject* atomicint64_xor(AtomicInt64Object* self, PyObject* other) {
  GET_I64_OR_ERROR(other);

  return PyLong_FromLongLong(_Py_atomic_load_int64(&self->value) ^ value);
}

static PyObject* atomicint64_and(AtomicInt64Object* self, PyObject* other) {
  GET_I64_OR_ERROR(other);

  return PyLong_FromLongLong(_Py_atomic_load_int64(&self->value) & value);
}

static PyObject* atomicint64_not(AtomicInt64Object* self) {
  return PyLong_FromLongLong(~_Py_atomic_load_int64(&self->value));
}

static PyObject* atomicint64_set(AtomicInt64Object* self, PyObject* other) {
  GET_I64_OR_ERROR(other);
  _Py_atomic_store_int64(&self->value, value);
  Py_RETURN_NONE;
}

static PyObject* atomicint64_get(AtomicInt64Object* self) {
  return PyLong_FromLongLong(_Py_atomic_load_int64(&self->value));
}

static PyObject* atomicint64_incr(AtomicInt64Object* self) {
  return PyLong_FromLongLong(_Py_atomic_add_int64(&self->value, 1) + 1);
}

static PyObject* atomicint64_decr(AtomicInt64Object* self) {
  return PyLong_FromLongLong(_Py_atomic_add_int64(&self->value, -1) - 1);
}

static PyMethodDef atomicint64_methods[] = {
    {"set", (PyCFunction)atomicint64_set, METH_O, "Atomically set the value"},
    {"get",
     (PyCFunction)atomicint64_get,
     METH_NOARGS,
     "Atomically get the value"},
    {"incr",
     (PyCFunction)atomicint64_incr,
     METH_NOARGS,
     "Atomically ++ and return new value"},
    {"decr",
     (PyCFunction)atomicint64_decr,
     METH_NOARGS,
     "Atomically -- and return new value"},
    {"__format__",
     (PyCFunction)atomicint64_format,
     METH_VARARGS,
     "Format the value"},
    {NULL, NULL, 0, NULL}};

static PyNumberMethods atomicint64_as_number = {
    .nb_add = (binaryfunc)atomicint64_add,
    .nb_subtract = (binaryfunc)atomicint64_sub,
    .nb_multiply = (binaryfunc)atomicint64_mul,
    .nb_floor_divide = (binaryfunc)atomicint64_div,
    .nb_negative = (unaryfunc)atomicint64_neg,
    .nb_positive = (unaryfunc)atomicint64_pos,
    .nb_absolute = (unaryfunc)atomicint64_abs,
    .nb_bool = (inquiry)atomicint64_bool,
    .nb_or = (binaryfunc)atomicint64_or,
    .nb_xor = (binaryfunc)atomicint64_xor,
    .nb_and = (binaryfunc)atomicint64_and,
    .nb_invert = (unaryfunc)atomicint64_not,
    .nb_inplace_add = (binaryfunc)atomicint64_iadd,
    .nb_inplace_subtract = (binaryfunc)atomicint64_isub,
    .nb_inplace_multiply = (binaryfunc)atomicint64_imul,
    .nb_inplace_floor_divide = (binaryfunc)atomicint64_idiv,
    .nb_int = (unaryfunc)atomicint64_int,
    .nb_inplace_or = (binaryfunc)atomicint64_ior,
    .nb_inplace_xor = (binaryfunc)atomicint64_ixor,
    .nb_inplace_and = (binaryfunc)atomicint64_iand,
};

static PyTypeObject AtomicInt64Type = {
    PyVarObject_HEAD_INIT(NULL, 0).tp_name = "_concurrent.AtomicInt64",
    .tp_basicsize = sizeof(AtomicInt64Object),
    .tp_itemsize = 0,
    .tp_dealloc = (destructor)atomicint64_dealloc,
    .tp_as_number = &atomicint64_as_number,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_doc = "AtomicInt64 objects",
    .tp_init = (initproc)atomicint64_init,
    .tp_new = atomicint64_new,
    .tp_methods = atomicint64_methods,
    .tp_richcompare = (richcmpfunc)atomicint64_richcompare,
    .tp_weaklistoffset = offsetof(AtomicInt64Object, weakreflist),
};

/* ***************
   End AtomicInt64
*/

/* Begin AtomicReference
 ***********************
 */

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

static PyTypeObject AtomicReferenceType = {
    PyVarObject_HEAD_INIT(NULL, 0).tp_name = "_concurrent.AtomicReference",
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

/* ******************
   End AtomicReference
*/

static int exec_local_module(PyObject* module) {
  if (PyType_Ready(&ConcurrentDictType) < 0) {
    return -1;
  }
  if (PyType_Ready(&AtomicInt64Type) < 0) {
    return -1;
  }
  if (PyType_Ready(&AtomicReferenceType) < 0) {
    return -1;
  }
  if (PyModule_AddObjectRef(
          module, "ConcurrentDict", (PyObject*)&ConcurrentDictType) < 0) {
    return -1;
  }
  if (PyModule_AddObjectRef(
          module, "AtomicInt64", (PyObject*)&AtomicInt64Type) < 0) {
    return -1;
  }
  if (PyModule_AddObjectRef(
          module, "AtomicReference", (PyObject*)&AtomicReferenceType) < 0) {
    return -1;
  }
  return 0;
}

static struct PyModuleDef_Slot module_slots[] = {
    {Py_mod_exec, exec_local_module},
#if PY_VERSION_HEX >= 0x030D0000
    {Py_mod_gil, Py_MOD_GIL_NOT_USED},
#endif
    {0, NULL} /* sentinel */
};

static PyModuleDef concurrent_module = {
    PyModuleDef_HEAD_INIT,
    "_concurrent",
    "Concurrently scalable data structures and patterns.",
    0,
    NULL,
    module_slots,
    NULL,
    NULL,
    NULL};

PyMODINIT_FUNC PyInit__concurrent(void) {
  return PyModuleDef_Init(&concurrent_module);
}
