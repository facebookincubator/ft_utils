/* Copyright (c) Meta Platforms, Inc. and affiliates. */

#include "ft_utils.h"

/* Begin LocalWrapper
   ******************

   The aim is to let the wrapper instances be thread local references only
   and then the wrapped objects do not end up with their shared references
   being incr/decr each time we access their methods.
*/

typedef struct {
  PyObject_HEAD PyObject* wrapped;
  PyObject* weakreflist;
} LocalWrapperObject;

static PyTypeObject LocalWrapperType;

static inline PyObject* _LW_Unwrap(PyObject* obj) {
  return PyObject_TypeCheck(obj, &LocalWrapperType)
      ? ((LocalWrapperObject*)obj)->wrapped
      : obj;
}

PyObject* _LW_Inplace_Return(LocalWrapperObject* self, PyObject* result) {
  if (result == NULL) {
    return result;
  }
  /* If result is selft->wrapped this just balances out the new ref returned
     from Python inplace functions. */
  Py_DECREF(self->wrapped);
  Py_INCREF(self);
  self->wrapped = result;
  return (PyObject*)self;
}

#define LW_INPLACE_RETURN return _LW_Inplace_Return(self, result)

static PyObject* LocalWrapper_getitem(
    LocalWrapperObject* self,
    PyObject* index) {
  return PyObject_GetItem(self->wrapped, index);
}

static int LocalWrapper_delitem(LocalWrapperObject* self, PyObject* index) {
  return PyObject_DelItem(self->wrapped, index);
}

static PyObject* LocalWrapper_getwrapped(
    LocalWrapperObject* self,
    void* closure) {
  Py_INCREF(self->wrapped);
  return self->wrapped;
}

static PyGetSetDef LocalWrapper_getsetters[] = {
    {"wrapped", (getter)LocalWrapper_getwrapped, NULL, "wrapped object", NULL},
    {NULL}};

static int LocalWrapper_setitem(
    LocalWrapperObject* self,
    PyObject* index,
    PyObject* value) {
  if (value == NULL) {
    return LocalWrapper_delitem(self, index);
  } else {
    return PyObject_SetItem(self->wrapped, index, value);
  }
}
static Py_ssize_t LocalWrapper_length(LocalWrapperObject* self) {
  /* Delegate length calculation to the wrapped object */
  return PyObject_Size(self->wrapped);
}

static PyMappingMethods LocalWrapper_as_mapping = {
    (lenfunc)LocalWrapper_length, /* mp_length */
    (binaryfunc)LocalWrapper_getitem, /* mp_subscript */
    (objobjargproc)LocalWrapper_setitem, /* mp_ass_subscript */
};

static Py_ssize_t LocalWrapper_sq_length(LocalWrapperObject* self) {
  if (PySequence_Check(self->wrapped)) {
    return PySequence_Size(self->wrapped);
  }
  PyErr_SetString(
      PyExc_TypeError, "object of type 'LocalWrapper' has no len()");
  return -1;
}

static PyObject* LocalWrapper_concat(
    LocalWrapperObject* self,
    PyObject* other) {
  if (PySequence_Check(self->wrapped)) {
    other = _LW_Unwrap(other);
    return PySequence_Concat(self->wrapped, other);
  }
  PyErr_SetString(PyExc_TypeError, "object does not support concatenation");
  return NULL;
}

static PyObject* LocalWrapper_repeat(
    LocalWrapperObject* self,
    Py_ssize_t count) {
  if (PySequence_Check(self->wrapped)) {
    return PySequence_Repeat(self->wrapped, count);
  }
  PyErr_SetString(PyExc_TypeError, "object does not support repetition");
  return NULL;
}

static PyObject* LocalWrapper_item(LocalWrapperObject* self, Py_ssize_t index) {
  if (PySequence_Check(self->wrapped)) {
    return PySequence_GetItem(self->wrapped, index);
  }
  PyErr_SetString(PyExc_TypeError, "object does not support indexing");
  return NULL;
}

static int LocalWrapper_contains(LocalWrapperObject* self, PyObject* value) {
  if (PySequence_Check(self->wrapped)) {
    return PySequence_Contains(self->wrapped, value);
  } else if (PyMapping_Check(self->wrapped)) {
    return PyMapping_HasKey(self->wrapped, value);
  }
  PyErr_SetString(PyExc_TypeError, "object does not support containment check");
  return -1;
}

static PyObject* LocalWrapper_slice(
    LocalWrapperObject* self,
    Py_ssize_t start,
    Py_ssize_t stop) {
  if (PySequence_Check(self->wrapped)) {
    return PySequence_GetSlice(self->wrapped, start, stop);
  }
  PyErr_SetString(PyExc_TypeError, "object does not support slicing");
  return NULL;
}

static int LocalWrapper_ass_item(
    LocalWrapperObject* self,
    Py_ssize_t index,
    PyObject* value) {
  if (PySequence_Check(self->wrapped)) {
    return PySequence_SetItem(self->wrapped, index, value);
  }
  PyErr_SetString(PyExc_TypeError, "object does not support item assignment");
  return -1;
}

static int LocalWrapper_ass_slice(
    LocalWrapperObject* self,
    Py_ssize_t start,
    Py_ssize_t stop,
    PyObject* value) {
  if (PySequence_Check(self->wrapped)) {
    return PySequence_SetSlice(self->wrapped, start, stop, value);
  }
  PyErr_SetString(PyExc_TypeError, "object does not support slice assignment");
  return -1;
}

static PyObject* LocalWrapper_inplace_concat(
    LocalWrapperObject* self,
    PyObject* other) {
  PyObject* result;
  if (PySequence_Check(self->wrapped)) {
    other = _LW_Unwrap(other);
    result = PySequence_InPlaceConcat(self->wrapped, other);
  } else {
    PyErr_SetString(
        PyExc_TypeError, "object does not support in-place concatenation");
    result = NULL;
  }
  LW_INPLACE_RETURN;
}

static PyObject* LocalWrapper_inplace_repeat(
    LocalWrapperObject* self,
    Py_ssize_t count) {
  PyObject* result;
  if (PySequence_Check(self->wrapped)) {
    result = PySequence_InPlaceRepeat(self->wrapped, count);
  } else {
    PyErr_SetString(
        PyExc_TypeError, "object does not support in-place repetition");
    return NULL;
  }
  LW_INPLACE_RETURN;
}

static PySequenceMethods LocalWrapper_as_sequence = {
    (lenfunc)LocalWrapper_sq_length, /* sq_length */
    (binaryfunc)LocalWrapper_concat, /* sq_concat */
    (ssizeargfunc)LocalWrapper_repeat, /* sq_repeat */
    (ssizeargfunc)LocalWrapper_item, /* sq_item */
    (ssizessizeargfunc)LocalWrapper_slice, /* sq_slice */
    (ssizeobjargproc)LocalWrapper_ass_item, /* sq_ass_item */
    (ssizessizeobjargproc)LocalWrapper_ass_slice, /* sq_ass_slice */
    (objobjproc)LocalWrapper_contains, /* sq_contains */
    (binaryfunc)LocalWrapper_inplace_concat, /* sq_inplace_concat */
    (ssizeargfunc)LocalWrapper_inplace_repeat, /* sq_inplace_repeat */
};

static PyObject* LocalWrapper_iter(LocalWrapperObject* self) {
  return PyObject_GetIter(self->wrapped);
}

static PyObject*
LocalWrapper_richcompare(LocalWrapperObject* self, PyObject* other, int op) {
  other = _LW_Unwrap(other);
  return PyObject_RichCompare(self->wrapped, other, op);
}

/* The PyNumber_* methods in abstract.c handle the difference between true
   number types and sequences using slot checking. There is no need to do that
   here and the way it is done in abstract.c is efficient. We do need a work
   around in _add because under some situations it gets called with self not
   being a LocalWraperObject. Hopefully we can get that figured out and fixed at
   some point.
*/

static PyObject* LocalWrapper_add(PyObject* self, PyObject* other) {
  other = _LW_Unwrap(other);
  self = _LW_Unwrap(self);
  return PyNumber_Add(self, other);
}

static PyObject* LocalWrapper_subtract(
    LocalWrapperObject* self,
    PyObject* other) {
  other = _LW_Unwrap(other);
  return PyNumber_Subtract(self->wrapped, other);
}

static PyObject* LocalWrapper_multiply(
    LocalWrapperObject* self,
    PyObject* other) {
  other = _LW_Unwrap(other);
  return PyNumber_Multiply(self->wrapped, other);
}

static PyObject* LocalWrapper_remainder(
    LocalWrapperObject* self,
    PyObject* other) {
  other = _LW_Unwrap(other);
  return PyNumber_Remainder(self->wrapped, other);
}

static PyObject* LocalWrapper_divmod(
    LocalWrapperObject* self,
    PyObject* other) {
  other = _LW_Unwrap(other);
  return PyNumber_Divmod(self->wrapped, other);
}

static PyObject* LocalWrapper_power(
    LocalWrapperObject* self,
    PyObject* other,
    PyObject* modulus) {
  return PyNumber_Power(self->wrapped, other, modulus);
}

static PyObject* LocalWrapper_negative(LocalWrapperObject* self) {
  return PyNumber_Negative(self->wrapped);
}

static PyObject* LocalWrapper_positive(LocalWrapperObject* self) {
  return PyNumber_Positive(self->wrapped);
}

static PyObject* LocalWrapper_absolute(LocalWrapperObject* self) {
  return PyNumber_Absolute(self->wrapped);
}

static int LocalWrapper_bool(LocalWrapperObject* self) {
  return PyObject_IsTrue(self->wrapped);
}

static PyObject* LocalWrapper_invert(LocalWrapperObject* self) {
  return PyNumber_Invert(self->wrapped);
}

static PyObject* LocalWrapper_lshift(
    LocalWrapperObject* self,
    PyObject* other) {
  other = _LW_Unwrap(other);
  return PyNumber_Lshift(self->wrapped, other);
}

static PyObject* LocalWrapper_rshift(
    LocalWrapperObject* self,
    PyObject* other) {
  other = _LW_Unwrap(other);
  return PyNumber_Rshift(self->wrapped, other);
}

static PyObject* LocalWrapper_and(LocalWrapperObject* self, PyObject* other) {
  other = _LW_Unwrap(other);
  return PyNumber_And(self->wrapped, other);
}

static PyObject* LocalWrapper_xor(LocalWrapperObject* self, PyObject* other) {
  other = _LW_Unwrap(other);
  return PyNumber_Xor(self->wrapped, other);
}

static PyObject* LocalWrapper_or(LocalWrapperObject* self, PyObject* other) {
  other = _LW_Unwrap(other);
  return PyNumber_Or(self->wrapped, other);
}

static PyObject* LocalWrapper_int(LocalWrapperObject* self) {
  return PyNumber_Long(self->wrapped);
}

static PyObject* LocalWrapper_float(LocalWrapperObject* self) {
  return PyNumber_Float(self->wrapped);
}

static PyObject* LocalWrapper_inplace_add(
    LocalWrapperObject* self,
    PyObject* other) {
  other = _LW_Unwrap(other);
  PyObject* result = PyNumber_InPlaceAdd(self->wrapped, other);
  LW_INPLACE_RETURN;
}

static PyObject* LocalWrapper_inplace_subtract(
    LocalWrapperObject* self,
    PyObject* other) {
  other = _LW_Unwrap(other);
  PyObject* result = PyNumber_InPlaceSubtract(self->wrapped, other);
  LW_INPLACE_RETURN;
}

static PyObject* LocalWrapper_inplace_multiply(
    LocalWrapperObject* self,
    PyObject* other) {
  other = _LW_Unwrap(other);
  PyObject* result = PyNumber_InPlaceMultiply(self->wrapped, other);
  LW_INPLACE_RETURN;
}

static PyObject* LocalWrapper_inplace_remainder(
    LocalWrapperObject* self,
    PyObject* other) {
  other = _LW_Unwrap(other);
  PyObject* result = PyNumber_InPlaceRemainder(self->wrapped, other);
  LW_INPLACE_RETURN;
}

static PyObject* LocalWrapper_inplace_power(
    LocalWrapperObject* self,
    PyObject* other,
    PyObject* modulus) {
  other = _LW_Unwrap(other);
  PyObject* result = PyNumber_InPlacePower(self->wrapped, other, modulus);
  LW_INPLACE_RETURN;
}

static PyObject* LocalWrapper_inplace_lshift(
    LocalWrapperObject* self,
    PyObject* other) {
  other = _LW_Unwrap(other);
  PyObject* result = PyNumber_InPlaceLshift(self->wrapped, other);
  LW_INPLACE_RETURN;
}

static PyObject* LocalWrapper_inplace_rshift(
    LocalWrapperObject* self,
    PyObject* other) {
  other = _LW_Unwrap(other);
  PyObject* result = PyNumber_InPlaceRshift(self->wrapped, other);
  LW_INPLACE_RETURN;
}

static PyObject* LocalWrapper_inplace_and(
    LocalWrapperObject* self,
    PyObject* other) {
  other = _LW_Unwrap(other);
  PyObject* result = PyNumber_InPlaceAnd(self->wrapped, other);
  LW_INPLACE_RETURN;
}

static PyObject* LocalWrapper_inplace_xor(
    LocalWrapperObject* self,
    PyObject* other) {
  other = _LW_Unwrap(other);
  PyObject* result = PyNumber_InPlaceXor(self->wrapped, other);
  LW_INPLACE_RETURN;
}

static PyObject* LocalWrapper_inplace_or(
    LocalWrapperObject* self,
    PyObject* other) {
  other = _LW_Unwrap(other);
  PyObject* result = PyNumber_InPlaceOr(self->wrapped, other);
  LW_INPLACE_RETURN;
}

static PyObject* LocalWrapper_floor_divide(
    LocalWrapperObject* self,
    PyObject* other) {
  other = _LW_Unwrap(other);
  PyObject* result = PyNumber_FloorDivide(self->wrapped, other);
  LW_INPLACE_RETURN;
}

static PyObject* LocalWrapper_true_divide(
    LocalWrapperObject* self,
    PyObject* other) {
  other = _LW_Unwrap(other);
  PyObject* result = PyNumber_TrueDivide(self->wrapped, other);
  LW_INPLACE_RETURN;
}

static PyObject* LocalWrapper_inplace_floor_divide(
    LocalWrapperObject* self,
    PyObject* other) {
  other = _LW_Unwrap(other);
  PyObject* result = PyNumber_InPlaceFloorDivide(self->wrapped, other);
  LW_INPLACE_RETURN;
}

static PyObject* LocalWrapper_inplace_true_divide(
    LocalWrapperObject* self,
    PyObject* other) {
  other = _LW_Unwrap(other);
  PyObject* result = PyNumber_InPlaceTrueDivide(self->wrapped, other);
  LW_INPLACE_RETURN;
}

static PyObject* LocalWrapper_index(LocalWrapperObject* self) {
  return PyNumber_Index(self->wrapped);
}

/* Matrix multplication is rare and complex so just let the
   interpreter handle it. This will cause ref counting on the
   stack so we can address this if we see issues. */
static PyObject* LocalWrapper_matrix_multiply(
    LocalWrapperObject* self,
    PyObject* other) {
  other = _LW_Unwrap(other);
  return PyObject_CallMethod(self->wrapped, "__matmul__", "O", other);
}

static PyObject* LocalWrapper_inplace_matrix_multiply(
    LocalWrapperObject* self,
    PyObject* other) {
  other = _LW_Unwrap(other);
  return PyObject_CallMethod(self->wrapped, "__imatmul__", "O", other);
}

static PyNumberMethods LocalWrapper_as_number = {
    (binaryfunc)LocalWrapper_add, /* nb_add */
    (binaryfunc)LocalWrapper_subtract, /* nb_subtract */
    (binaryfunc)LocalWrapper_multiply, /* nb_multiply */
    (binaryfunc)LocalWrapper_remainder, /* nb_remainder */
    (binaryfunc)LocalWrapper_divmod, /*nb_divmdo */
    (ternaryfunc)LocalWrapper_power, /* nb_power */
    (unaryfunc)LocalWrapper_negative, /* nb_negative */
    (unaryfunc)LocalWrapper_positive, /* nb_positive */
    (unaryfunc)LocalWrapper_absolute, /* nb_absolute */
    (inquiry)LocalWrapper_bool, /* nb_bool */
    (unaryfunc)LocalWrapper_invert, /* nb_invert */
    (binaryfunc)LocalWrapper_lshift, /* nb_lshift */
    (binaryfunc)LocalWrapper_rshift, /* nb_rshift */
    (binaryfunc)LocalWrapper_and, /* nb_and */
    (binaryfunc)LocalWrapper_xor, /* nb_xor */
    (binaryfunc)LocalWrapper_or, /* nb_or */
    (unaryfunc)LocalWrapper_int, /* nb_int */
    0, /* nb_reserved */
    (unaryfunc)LocalWrapper_float, /* nb_float */
    (binaryfunc)LocalWrapper_inplace_add, /* nb_inplace_add */
    (binaryfunc)LocalWrapper_inplace_subtract, /* nb_inplace_subtract */
    (binaryfunc)LocalWrapper_inplace_multiply, /* nb_inplace_multiply */
    (binaryfunc)LocalWrapper_inplace_remainder, /* nb_inplace_remainder */
    (ternaryfunc)LocalWrapper_inplace_power, /* nb_inplace_power */
    (binaryfunc)LocalWrapper_inplace_lshift, /* nb_inplace_lshift */
    (binaryfunc)LocalWrapper_inplace_rshift, /* nb_inplace_rshift */
    (binaryfunc)LocalWrapper_inplace_and, /* nb_inplace_and */
    (binaryfunc)LocalWrapper_inplace_xor, /* nb_inplace_xor */
    (binaryfunc)LocalWrapper_inplace_or, /* nb_inplace_or */
    (binaryfunc)LocalWrapper_floor_divide, /* nb_floor_divide */
    (binaryfunc)LocalWrapper_true_divide, /* nb_true_divide */
    (binaryfunc)LocalWrapper_inplace_floor_divide, /* nb_inplace_floor_divide */
    (binaryfunc)LocalWrapper_inplace_true_divide, /* nb_inplace_true_divide */
    (unaryfunc)LocalWrapper_index, /* nb_index */
    (binaryfunc)LocalWrapper_matrix_multiply, /* nb_matrix_multiply */
    (binaryfunc)
        LocalWrapper_inplace_matrix_multiply, /* nb_inplace_matrix_multiply */
};

static Py_hash_t LocalWrapper_hash(LocalWrapperObject* self) {
  return PyObject_Hash(self->wrapped);
}

static PyObject*
LocalWrapper_call(LocalWrapperObject* self, PyObject* args, PyObject* kwds) {
  return PyObject_Call(self->wrapped, args, kwds);
}

static PyObject* LocalWrapper_str(LocalWrapperObject* self) {
  return PyObject_Str(self->wrapped);
}

static PyObject* LocalWrapper_getattro(
    LocalWrapperObject* self,
    PyObject* attr_name) {
  PyObject* result = PyObject_GenericGetAttr((PyObject*)self, attr_name);
  if (result)
    return result;
  PyErr_Clear();
  return PyObject_GenericGetAttr(self->wrapped, attr_name);
}

static int LocalWrapper_setattro(
    LocalWrapperObject* self,
    PyObject* attr_name,
    PyObject* value) {
  return PyObject_GenericSetAttr((PyObject*)self->wrapped, attr_name, value);
}

static int
LocalWrapper_getbuffer(LocalWrapperObject* self, Py_buffer* view, int flags) {
  return PyObject_GetBuffer(self->wrapped, view, flags);
}

static void LocalWrapper_releasebuffer(
    LocalWrapperObject* self,
    Py_buffer* view) {
  if (view->obj) {
    if (view->obj == self->wrapped) {
      PyBufferProcs* pb = Py_TYPE(self->wrapped)->tp_as_buffer;
      if (pb && pb->bf_releasebuffer) {
        pb->bf_releasebuffer(self->wrapped, view);
      }
    }
    Py_CLEAR(view->obj);
  }
}

static PyBufferProcs LocalWrapper_as_buffer = {
    (getbufferproc)LocalWrapper_getbuffer,
    (releasebufferproc)LocalWrapper_releasebuffer};

static int
LocalWrapper_traverse(LocalWrapperObject* self, visitproc visit, void* arg) {
  Py_VISIT(self->wrapped);
  return 0;
}

static PyObject* LocalWrapper_iternext(LocalWrapperObject* self) {
  return PyIter_Next(self->wrapped);
}

static PyObject* LocalWrapper_repr(LocalWrapperObject* self) {
  PyObject* wrapped_repr = PyObject_Repr(self->wrapped);
  if (wrapped_repr == NULL) {
    return NULL;
  }
  PyObject* result = PyUnicode_FromFormat("<LocalWrapper: %U>", wrapped_repr);
  Py_DECREF(wrapped_repr);
  return result;
}

static int LocalWrapper_clear(LocalWrapperObject* self) {
  Py_CLEAR(self->wrapped);
  return 0;
}

static void LocalWrapper_dealloc(LocalWrapperObject* self) {
  PyObject_GC_UnTrack(self);
  LocalWrapper_clear(self);
  PyObject_ClearWeakRefs((PyObject*)self);
  PyObject_GC_Del(self);
}

static PyObject*
LocalWrapper_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
  PyObject* wrapped;
  if (!PyArg_ParseTuple(args, "O", &wrapped))
    return NULL;

  LocalWrapperObject* self = (LocalWrapperObject*)type->tp_alloc(type, 0);
  if (self != NULL) {
    Py_INCREF(wrapped);
    self->wrapped = wrapped;
    self->weakreflist = NULL;
  }
  return (PyObject*)self;
}

static PyObject* LocalWrapper_enter(LocalWrapperObject* self, PyObject* args) {
  PyObject* enter_method = PyObject_GetAttrString(self->wrapped, "__enter__");
  if (enter_method == NULL) {
    if (!PyErr_Occurred()) {
      PyErr_SetString(
          PyExc_AttributeError, "Wrapped __enter__ method not found");
    }
    return NULL;
  }
  PyObject* result = PyObject_CallObject(enter_method, args);
  Py_DECREF(enter_method);
  return result;
}

static PyObject* LocalWrapper_exit(LocalWrapperObject* self, PyObject* args) {
  PyObject* exit_method = PyObject_GetAttrString(self->wrapped, "__exit__");
  if (exit_method == NULL) {
    if (!PyErr_Occurred()) {
      PyErr_SetString(
          PyExc_AttributeError, "Wrapped __exit__ method not found");
    }
    return NULL;
  }
  PyObject* result = PyObject_CallObject(exit_method, args);
  Py_DECREF(exit_method);
  return result;
}

static PyMethodDef LocalWrapper_methods[] = {
    {"__enter__",
     (PyCFunction)LocalWrapper_enter,
     METH_NOARGS,
     "Enter the runtime context of wrapped if it has one."},
    {"__exit__",
     (PyCFunction)LocalWrapper_exit,
     METH_VARARGS,
     "Exit the runtime contextof wrapped if it has one."},
    {NULL} /* Sentinel */
};

static PyTypeObject LocalWrapperType = {
    PyVarObject_HEAD_INIT(NULL, 0) "local.LocalWrapper", /* tp_name */
    sizeof(LocalWrapperObject), /* tp_basicsize */
    0, /* tp_itemsize */
    (destructor)LocalWrapper_dealloc, /* tp_dealloc */
    0, /* tp_print */
    0,
    0,
    0, /* tp_reserved */
    (reprfunc)LocalWrapper_repr, /* tp_repr */
    &LocalWrapper_as_number, /* tp_as_number */
    &LocalWrapper_as_sequence, /* tp_as_sequence */
    &LocalWrapper_as_mapping, /* tp_as_mapping */
    (hashfunc)LocalWrapper_hash, /* tp_hash */
    (ternaryfunc)LocalWrapper_call, /* tp_call */
    (reprfunc)LocalWrapper_str, /* tp_str */
    (getattrofunc)LocalWrapper_getattro, /* tp_getattro */
    (setattrofunc)LocalWrapper_setattro, /* tp_setattro */
    &LocalWrapper_as_buffer, /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC, /* tp_flags */
    "LocalWrapper objects", /* tp_doc */
    (traverseproc)LocalWrapper_traverse, /* tp_traverse */
    (inquiry)LocalWrapper_clear, /* tp_clear */
    (richcmpfunc)LocalWrapper_richcompare, /* tp_richcompare */
    offsetof(LocalWrapperObject, weakreflist), /* tp_weaklistoffset */
    (getiterfunc)LocalWrapper_iter, /* tp_iter */
    (iternextfunc)LocalWrapper_iternext, /* tp_iternext */
    LocalWrapper_methods, /* tp_methods */
    0, /* tp_members */
    LocalWrapper_getsetters, /* tp_getset */
    0, /* tp_base */
    0, /* tp_dict */
    0, /* tp_descr_get */
    0, /* tp_descr_set */
    0, /* tp_dictoffset */
    0, /* tp_init */
    PyType_GenericAlloc, /* tp_alloc */
    (newfunc)LocalWrapper_new, /* tp_new */
    PyObject_GC_Del, /* tp_free */
};

/* ****************
   End LocalWrapper
*/

/* Utility method to add to any object which want to be accessed locally. */
static PyObject* create_local_wrapper(PyObject* self) {
  PyObject* args;
  PyObject* localWrapper;
  args = PyTuple_Pack(1, self);
  if (!args) {
    return NULL;
  }
  localWrapper = PyObject_CallObject((PyObject*)&LocalWrapperType, args);
  Py_DECREF(args);
  if (!localWrapper) {
    return NULL;
  }
  return localWrapper;
}

/* Begin BatchExecutor
   *******************

   Batch execute a callable in one thread and store the results in a buffer
   which we can then access efficiently from multiple threads. Once the buffer
   is exhausted we fill it up again. This avoid lock contention on the execution
   and maximised memory locallity as well.
*/

typedef struct {
  PyObject_HEAD PyObject* source;
  PyObject* weakreflist;
  Py_ssize_t size;
  Py_ssize_t index;
  PyObject** buffer;
} BatchExecutorObject;

static PyObject*
BatchExecutorObject_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
  BatchExecutorObject* self;
  PyObject* source = NULL;
  PyObject* py_size;
  Py_ssize_t size;

  self = (BatchExecutorObject*)type->tp_alloc(type, 0);
  if (self == NULL) {
    return NULL;
  }

  self->weakreflist = NULL;
  self->source = NULL;
  self->buffer = NULL;
  self->size = -1;
  self->index = 0;

  if (!PyArg_ParseTuple(args, "OO", &source, &py_size)) {
    Py_DECREF(self);
    return NULL;
  }

  if (!PyCallable_Check(source)) {
    PyErr_SetString(PyExc_TypeError, "source must be callable");
    Py_DECREF(self);
    return NULL;
  }

  if (!PyLong_Check(py_size)) {
    PyErr_SetString(PyExc_TypeError, "size must be an integer");
    Py_DECREF(self);
    return NULL;
  }

  size = PyLong_AsSsize_t(py_size);
  if (PyErr_Occurred()) {
    Py_DECREF(self);
    return NULL;
  }

  if (size < 1) {
    PyErr_SetString(PyExc_ValueError, "size must be positive");
    Py_DECREF(self);
    return NULL;
  }

  self->buffer = (PyObject**)PyMem_Calloc(size, sizeof(PyObject*));
  if (!self->buffer) {
    PyErr_NoMemory();
    Py_DECREF(self);
    return NULL;
  }

  Py_INCREF(source);
  self->source = source;
  self->size = size;
  self->index =
      size; /* Critically mark this as needing filling on first call. */

  return (PyObject*)self;
}

static void BatchExecutorObject_clear_buffer(BatchExecutorObject* self) {
  if (self->buffer != NULL) {
    for (Py_ssize_t i = 0; i < self->size; i++) {
      Py_CLEAR(self->buffer[i]);
    }
  }
}

static void BatchExecutorObject_clear_all(BatchExecutorObject* self) {
  if (self->buffer != NULL) {
    BatchExecutorObject_clear_buffer(self);
    PyMem_Free(self->buffer);
    self->buffer = NULL;
  }

  Py_CLEAR(self->source);
  self->index = 0;
  self->size = -1;
}

static int BatchExecutorObject_fill_buffer(BatchExecutorObject* self) {
  PyObject* result;
  for (Py_ssize_t i = 0; i < self->size; i++) {
    result = PyObject_CallObject(self->source, NULL);
    if (result == NULL) {
      /* If anything goes wrong set the object into an unrecoverable error
       * state. */
      BatchExecutorObject_clear_all(self);
      _Py_atomic_fence_release();
      return -1;
    }
    Py_INCREF(result);
    self->buffer[i] = result;
  }
  /* First make sure everything is set up on all threads then signal other
     threads can move forward by setting index to zero atomically. In theory
     the critical section should make this OK (or the GIL) but we are being
     super careful here.
  */
  _Py_atomic_fence_release();
  _Py_atomic_store_ssize(&(self->index), 0);
  return 0;
}

static PyObject* BatchExecutorObject_load(BatchExecutorObject* self) {
  Py_ssize_t index;
  Py_ssize_t size = self->size;
  PyObject* ret;
  PyObject* source = _Py_atomic_load_ptr(&(self->source));
  PyObject* buffer = _Py_atomic_load_ptr(&(self->buffer));
  int err;

  if (source == NULL || buffer == NULL) {
    PyErr_SetString(
        PyExc_RuntimeError,
        "BatchExecutor is shuttdown. Was there a previous exception?");
    return NULL;
  }

  /* Note there is nothing fair here, in theory a thread could get
     starved by bad luck. If we ever see that in a 'wild' we need to
     consider some ordering system.
  */
  while (1) {
    index = _Py_atomic_add_ssize(&(self->index), 1);
    if (index < size) {
      ret = _Py_atomic_load_ptr((void**)&(self->buffer[index]));
      Py_INCREF(ret);
      return ret;
    }
    Py_BEGIN_CRITICAL_SECTION(self);
    index = _Py_atomic_load_ssize(&(self->index));
    if (index < size) {
      err = 0;
    } else {
      err = BatchExecutorObject_fill_buffer(self);
    }
    Py_END_CRITICAL_SECTION();
    if (err) {
      return NULL;
    }
  }
}

static PyMethodDef BatchExecutorObject_methods[] = {
    {"load",
     (PyCFunction)BatchExecutorObject_load,
     METH_NOARGS,
     "Load data using the source callable."},
    {"as_local",
     (PyCFunction)create_local_wrapper,
     METH_NOARGS,
     "Create and return a new LocalWrapper instance initialized with this BatchExecutorObject."},
    {NULL, NULL, 0, NULL} /* Sentinel */
};

static int BatchExecutorObject_traverse(
    BatchExecutorObject* self,
    visitproc visit,
    void* arg) {
  Py_VISIT(self->source);
  if (self->buffer) {
    for (Py_ssize_t i = 0; i < self->size; i++) {
      Py_VISIT(self->buffer[i]);
    }
  }
  return 0;
}

static int BatchExecutorObject_clear(BatchExecutorObject* self) {
  Py_CLEAR(self->source);
  if (self->buffer) {
    for (Py_ssize_t i = 0; i < self->size; i++) {
      Py_CLEAR(self->buffer[i]);
    }
    PyMem_Free(self->buffer);
    self->buffer = NULL;
    self->size = 0;
  }
  return 0;
}

static void BatchExecutorObject_dealloc(BatchExecutorObject* self) {
  PyObject_GC_UnTrack(self);
  BatchExecutorObject_clear(self);
  PyObject_ClearWeakRefs((PyObject*)self);
  PyObject_GC_Del(self);
}

static PyTypeObject BatchExecutorObjectType = {
    PyVarObject_HEAD_INIT(NULL, 0).tp_name = "local.BatchExecutorObject",
    .tp_doc = "BatchExecutorObject objects",
    .tp_basicsize = sizeof(BatchExecutorObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC,
    .tp_new = BatchExecutorObject_new,
    .tp_init = NULL,
    .tp_dealloc = (destructor)BatchExecutorObject_dealloc,
    .tp_alloc = PyType_GenericAlloc,
    .tp_traverse = (traverseproc)BatchExecutorObject_traverse,
    .tp_clear = (inquiry)BatchExecutorObject_clear,
    .tp_methods = BatchExecutorObject_methods,
    .tp_weaklistoffset = offsetof(BatchExecutorObject, weakreflist),
    .tp_free = PyObject_GC_Del,
};

/* *****************
   End BatchExecutor
*/

static int exec_local_module(PyObject* module) {
  if (PyType_Ready(&LocalWrapperType) < 0) {
    return -1;
  }
  if (PyType_Ready(&BatchExecutorObjectType) < 0) {
    return -1;
  }
  if (PyModule_AddObjectRef(
          module, "LocalWrapper", (PyObject*)&LocalWrapperType) < 0) {
    return -1;
  }
  if (PyModule_AddObjectRef(
          module, "BatchExecutor", (PyObject*)&BatchExecutorObjectType) < 0) {
    return -1;
  }
  return 0; /* Return 0 on success */
}

static struct PyModuleDef_Slot module_slots[] = {
    {Py_mod_exec, exec_local_module},
    _PY_NOGIL_MODULE_SLOT // NOLINT
    {0, NULL} /* sentinel */
};

static PyModuleDef local_module = {
    PyModuleDef_HEAD_INIT,
    "local",
    "Utilies to thread localize load and store of shared data.",
    0,
    NULL,
    module_slots,
    NULL,
    NULL,
    NULL};

PyMODINIT_FUNC PyInit_local(void) {
  return PyModuleDef_Init(&local_module);
}
