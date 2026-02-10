/* Copyright (c) Meta Platforms, Inc. and affiliates. */

#include "ft_utils.h"

#include "atomic_int64.h"

typedef struct {
  PyObject_HEAD int64_t value;
  PyObject* weakreflist;
} AtomicInt64Object;

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
  if (int_obj == NULL) {
    return NULL;
  }

  PyObject* format_spec;
  if (!PyArg_ParseTuple(args, "O", &format_spec)) {
    return NULL;
  }
  Py_INCREF(format_spec);

  PyObject* result = PyObject_Format(int_obj, format_spec);
  Py_DECREF(int_obj);
  Py_DECREF(format_spec);

  return result;
}

static PyObject*
atomicint64_richcompare(AtomicInt64Object* self, PyObject* other, int op) {
  PyObject* int_obj = atomicint64_int(self);
  if (int_obj == NULL) {
    return NULL;
  }

  int result = PyObject_RichCompareBool(int_obj, other, op);
  Py_DECREF(int_obj);

  if (result == -1) {
    return NULL;
  } else {
    return PyBool_FromLong(result);
  }
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

PyTypeObject AtomicInt64Type = {
    PyVarObject_HEAD_INIT(NULL, 0).tp_name = "_concurrency.AtomicInt64",
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
