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

/* Begin ConcurrentDeque
 ***********************
 */

/* A node represents a single datum in the deque. It is a doubly-linked list
 * node that contains a pointer to the datum.
 */
typedef struct ConcurrentDequeNode {
  struct ConcurrentDequeNode* prev;
  struct ConcurrentDequeNode* next;
  PyObject* datum;
} ConcurrentDequeNode;

/* A list represents the bounds of the deque. We allocate it in a separate
 * object to allow it to be replaced atomically from within the deque, allowing
 * these objects to be used concurrently.
 */
typedef struct {
  ConcurrentDequeNode* head;
  ConcurrentDequeNode* tail;
} ConcurrentDequeList;

/* A deque is a doubly-sided queue that is optimized for adding and removing
 * items at the ends. It maintains a list object that contains a pointer to its
 * head and tail nodes.
 */
typedef struct {
  PyObject_HEAD;
  /* The list field in this struct is a tagged pointer. If the least-significant
   * bit is set, then list is considered "locked". This happens when the list
   * has just been replaced and one of the operations needs to fix internal
   * links within the linked-list. Because this is a tagged pointer, it is not
   * safe for reading without considering the lock state. Note that we can do
   * this tagging because of the alignment of the list field.
   */
  ConcurrentDequeList* list;
  PyObject* weakreflist;
} ConcurrentDequeObject;

/* Allocate a new node for the deque and return a pointer to it.
 */
static ConcurrentDequeNode* ConcurrentDequeNode_alloc(
    PyObject* datum,
    ConcurrentDequeNode* prev,
    ConcurrentDequeNode* next) {
  ConcurrentDequeNode* node = PyMem_Malloc(sizeof(ConcurrentDequeNode));
  if (node == NULL) {
    PyErr_NoMemory();
    return NULL;
  }

  node->prev = prev;
  node->next = next;

  Py_INCREF(datum);
  node->datum = datum;

  return node;
}

/* Deallocate a node object, using Python's memory management. We have this here
 * to signify to the reader that we know we're only freeing the node and
 * purposefully not decrementing the reference count of the datum.
 */
#define ConcurrentDequeNode_dealloc_shallow PyMem_Free

/* Deallocate a node and remove its reference to the datum.
 */
static void ConcurrentDequeNode_dealloc(ConcurrentDequeNode* node) {
  Py_DECREF(node->datum);
  ConcurrentDequeNode_dealloc_shallow(node);
}

/* Deallocate a chain of nodes, starting at the given node.
 */
static void ConcurrentDequeNode_dealloc_chain(ConcurrentDequeNode* node) {
  while (node != NULL) {
    ConcurrentDequeNode* next = node->next;
    ConcurrentDequeNode_dealloc(node);
    node = next;
  }
}

/* Allocate the internal list object that is used by the deque to hold its
 * contents.
 */
static ConcurrentDequeList* ConcurrentDequeList_alloc(
    ConcurrentDequeNode* head,
    ConcurrentDequeNode* tail) {
  ConcurrentDequeList* list = PyMem_Malloc(sizeof(ConcurrentDequeList));
  if (list == NULL) {
    PyErr_NoMemory();
    return NULL;
  }

  list->head = head;
  list->tail = tail;
  return list;
}

/* Deallocate a list object, using Python's memory management. We have this here
 * to signify to the reader that we know we're only freeing the list and not the
 * nodes in the list.
 */
#define ConcurrentDequeList_dealloc_shallow PyMem_Free

/* Deallocate and remove references to the given list by visiting each node in
 * the doubly-linked list.
 */
static void ConcurrentDequeList_dealloc(ConcurrentDequeList* list) {
  ConcurrentDequeNode_dealloc_chain(list->head);
  ConcurrentDequeList_dealloc_shallow(list);
}

/* Atomically replace the list pointer on the given deque. This purposefully
 * does not take into account the locking bit, and therefore should only be
 * called when the list is known to be locked.
 */
#define ConcurrentDeque_replace(deque_, list_) \
  _Py_atomic_store_ptr((void**)&deque_->list, list_)

/* Attempt to atomically replace the list pointer on the given deque with the
 * given list.
 */
#define ConcurrentDeque_try_replace(deque_, list_, next_list_) \
  _Py_atomic_compare_exchange_ptr(&deque_->list, list_, next_list_)

/* Lock the given list by turning on its least significant bit.
 */
#define ConcurrentDequeList_locked(list_) \
  ((ConcurrentDequeList*)((uintptr_t)(list_) | (uintptr_t)1))

/* Attempt to atomically replace the list pointer on the given deque with the
 * given list, and additionally set the locking bit.
 */
#define ConcurrentDeque_try_replace_locked(deque_, list_, next_list_) \
  ConcurrentDeque_try_replace(                                        \
      deque_, list_, ConcurrentDequeList_locked(next_list_))

/* A platform-specific way of pausing execution, used to provide backoff while
 * spinning when waiting for a lock.
 */
#ifndef WV_PAUSE
#if defined(_MSC_VER) // Microsoft compilers
#if defined(_M_X64) || defined(_M_IX86) // Intel/AMD
#include <immintrin.h>
#define WV_PAUSE() _mm_pause()
#elif defined(_M_ARM) || defined(_M_ARM64) // ARM
#define WV_PAUSE() __yield()
#else
#define WV_PAUSE() // Fallback: no-op
#endif
#elif defined(__GNUC__) || defined(__clang__) // GCC/Clang
#if defined(__x86_64__) || defined(__i386__) // Intel/AMD

#define WV_PAUSE() __builtin_ia32_pause()
#elif defined(__aarch64__) || defined(__arm__) // ARM
#define WV_PAUSE() asm volatile("yield" ::: "memory")
#else
#define WV_PAUSE() // Fallback: no-op
#endif
#else // Unknown compiler
#define WV_PAUSE() // Fallback: no-op
#endif
#endif // WV_PAUSE

/* Pause for the given number of iterations, using the WV_PAUSE macro.
 */
static inline void ConcurrentDeque_backoff_pause(unsigned int backoff) {
  for (unsigned int pause = 0; pause < backoff; pause++)
    WV_PAUSE();
}

/* An infinite for-loop that performs exponential backoff.
 */
#define ConcurrentDeque_backoff_loop \
  for (unsigned int backoff = 1;; ConcurrentDeque_backoff_pause(backoff *= 2))

/* Return a pointer to the list on the given deque with the lock bit cleared.
 */
static inline ConcurrentDequeList* ConcurrentDeque_list(
    ConcurrentDequeObject* self) {
  ConcurrentDequeList* ptr = _Py_atomic_load_ptr(&self->list);
  return (ConcurrentDequeList*)((uintptr_t)ptr & ~(uintptr_t)1);
}

/* Atomically replace the deque's list with a NULL list and then go about
 * clearing references and freeing the list.
 */
static int ConcurrentDeque_clear(ConcurrentDequeObject* self) {
  ConcurrentDeque_backoff_loop {
    ConcurrentDequeList* list = ConcurrentDeque_list(self);
    if (list == NULL) {
      return 0;
    }

    if (ConcurrentDeque_try_replace(self, &list, NULL)) {
      ConcurrentDequeList_dealloc(list);
      return 0;
    }
  }
}

/* Provide the traverse implementation for the GC. Visit each node in the linked
 * list if a list has been allocated.
 */
static int ConcurrentDeque_traverse(
    ConcurrentDequeObject* self,
    visitproc visit,
    void* arg) {
  ConcurrentDequeList* list = ConcurrentDeque_list(self);
  if (list == NULL) {
    return 0;
  }

  for (ConcurrentDequeNode* node = list->head; node != NULL;
       node = node->next) {
    Py_VISIT(node->datum);
  }
  return 0;
}

/* Allocate a new ConcurrentDeque and set all of its fields to their default
 * values.
 */
static PyObject*
ConcurrentDeque_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
  ConcurrentDequeObject* deque =
      (ConcurrentDequeObject*)type->tp_alloc(type, 0);

  if (deque == NULL) {
    return NULL;
  }

  deque->list = NULL;
  deque->weakreflist = NULL;

  return (PyObject*)deque;
}

PyDoc_STRVAR(
    ConcurrentDeque_init__doc__,
    "ConcurrentDeque([iterable])\n"
    "--\n"
    "\n"
    "A list-like sequence optimized for data accesses near its endpoints.");

static PyObject* ConcurrentDeque_extend(
    ConcurrentDequeObject* self,
    PyObject* iterable);

/* Initialize a new ConcurrentDeque.
 */
static int
ConcurrentDeque_init(PyObject* self, PyObject* args, PyObject* kwds) {
  if (PyTuple_GET_SIZE(args) > 1) {
    PyErr_SetString(
        PyExc_TypeError, "ConcurrentDeque() takes zero or one argument");
    return -1;
  }

  if (PyTuple_GET_SIZE(args) == 1) {
    PyObject* arg = PyTuple_GET_ITEM(args, 0);
    PyObject* result =
        ConcurrentDeque_extend((ConcurrentDequeObject*)self, arg);

    if (result == NULL) {
      return -1;
    }

    Py_DECREF(result);
  }

  return 0;
}

/* Deallocate a ConcurrentDeque and remove any references.
 */
static void ConcurrentDeque_dealloc(ConcurrentDequeObject* self) {
  PyTypeObject* tp = Py_TYPE(self);

  PyObject_GC_UnTrack(self);
  if (self->weakreflist != NULL) {
    PyObject_ClearWeakRefs((PyObject*)self);
  }

  ConcurrentDeque_clear(self);
  tp->tp_free(self);
}

PyDoc_STRVAR(
    ConcurrentDeque_append__doc__,
    "append($self, item, /)\n"
    "--\n"
    "\n"
    "Add an element to the right side of the deque.");

/* Append an item to the right side of the deque.
 */
static PyObject* ConcurrentDeque_append(
    ConcurrentDequeObject* self,
    PyObject* datum) {
  ConcurrentDequeNode* next_node = ConcurrentDequeNode_alloc(datum, NULL, NULL);

  if (next_node == NULL) {
    return NULL;
  }

  ConcurrentDequeList* next_list =
      ConcurrentDequeList_alloc(next_node, next_node);

  if (next_list == NULL) {
    ConcurrentDequeNode_dealloc(next_node);
    return NULL;
  }

  ConcurrentDequeList* next_list_locked = ConcurrentDequeList_locked(next_list);

  ConcurrentDeque_backoff_loop {
    ConcurrentDequeList* list = ConcurrentDeque_list(self);

    if (list == NULL) {
      /* If the list is currently NULL, then we will attempt to replace it with
       * a new list.
       */
      if (ConcurrentDeque_try_replace(self, &list, next_list)) {
        Py_RETURN_NONE;
      }
    } else if (ConcurrentDeque_try_replace(self, &list, next_list_locked)) {
      /* Otherwise, we will attempt to append the item to the end of the current
       * list by replacing the tail of the current list.
       */
      next_list->head = list->head;
      next_node->prev = list->tail;
      next_node->prev->next = next_node;

      ConcurrentDeque_replace(self, next_list);

      ConcurrentDequeList_dealloc_shallow(list);
      Py_RETURN_NONE;
    }
  }
}

PyDoc_STRVAR(
    ConcurrentDeque_appendleft__doc__,
    "appendleft($self, item, /)\n"
    "--\n"
    "\n"
    "Add an element to the left side of the deque.");

/* Append an item to the left side of the deque.
 */
static PyObject* ConcurrentDeque_appendleft(
    ConcurrentDequeObject* self,
    PyObject* datum) {
  ConcurrentDequeNode* next_node = ConcurrentDequeNode_alloc(datum, NULL, NULL);

  if (next_node == NULL) {
    return NULL;
  }

  ConcurrentDequeList* next_list =
      ConcurrentDequeList_alloc(next_node, next_node);

  if (next_list == NULL) {
    ConcurrentDequeNode_dealloc(next_node);
    return NULL;
  }

  ConcurrentDequeList* next_list_locked = ConcurrentDequeList_locked(next_list);

  ConcurrentDeque_backoff_loop {
    ConcurrentDequeList* list = ConcurrentDeque_list(self);

    if (list == NULL) {
      /* If the list is currently NULL, then we will attempt to replace it with
       * a new list.
       */
      if (ConcurrentDeque_try_replace(self, &list, next_list)) {
        Py_RETURN_NONE;
      }
    } else if (ConcurrentDeque_try_replace(self, &list, next_list_locked)) {
      /* Otherwise, we will attempt to append the item to the start of the
       * current list by replacing the head of the current list.
       */
      next_list->tail = list->tail;
      next_node->next = list->head;
      next_node->next->prev = next_node;

      ConcurrentDeque_replace(self, next_list);

      ConcurrentDequeList_dealloc_shallow(list);
      Py_RETURN_NONE;
    }
  }
}

PyDoc_STRVAR(
    ConcurrentDeque_clearmethod__doc__,
    "clear($self, /)\n"
    "--\n"
    "\n"
    "Remove all elements from the deque.");

/* Remove all elements from the deque.
 */
static PyObject* ConcurrentDeque_clearmethod(ConcurrentDequeObject* self) {
  ConcurrentDeque_clear(self);
  Py_RETURN_NONE;
}

#define _ConcurrentDequeList_fromiter_FORWARD 0
#define _ConcurrentDequeList_fromiter_BACKWARD 1

/* A helper for extend and extendleft that creates a new list from an iterable
 * python object.
 */
static ConcurrentDequeList* _ConcurrentDequeList_fromiter(
    PyObject* iter,
    int ordering) {
  PyObject* datum;
  PyObject* (*iternext)(PyObject*) = *Py_TYPE(iter)->tp_iternext;

  ConcurrentDequeNode* head = NULL;
  ConcurrentDequeNode* tail = NULL;

  while ((datum = iternext(iter)) != NULL) {
    ConcurrentDequeNode* next = ConcurrentDequeNode_alloc(datum, NULL, NULL);

    if (next == NULL) {
      ConcurrentDequeNode_dealloc_chain(head);
      Py_DECREF(datum);
      Py_DECREF(iter);
      return NULL;
    }

    if (ordering == _ConcurrentDequeList_fromiter_FORWARD) {
      next->prev = tail;

      if (head == NULL) {
        head = next;
      } else {
        tail->next = next;
      }

      tail = next;
    } else {
      next->next = head;

      if (tail == NULL) {
        tail = next;
      } else {
        head->prev = next;
      }

      head = next;
    }

    Py_DECREF(datum);
  }

  if (PyErr_Occurred()) {
    if (PyErr_ExceptionMatches(PyExc_StopIteration)) {
      PyErr_Clear();
    } else {
      Py_DECREF(iter);
      return NULL;
    }
  }

  ConcurrentDequeList* list = NULL;

  if (head != NULL) {
    list = ConcurrentDequeList_alloc(head, tail);

    if (list == NULL) {
      ConcurrentDequeNode_dealloc_chain(head);
      Py_DECREF(iter);
      return NULL;
    }

    list->head = head;
    list->tail = tail;
  }

  Py_DECREF(iter);
  return list;
}

PyDoc_STRVAR(
    ConcurrentDeque_extend__doc__,
    "extend($self, iterable, /)\n"
    "--\n"
    "\n"
    "Extend the right side of the deque with elements from the iterable.");

/* Extend the right side of the deque with elements from the iterable.
 */
static PyObject* ConcurrentDeque_extend(
    ConcurrentDequeObject* self,
    PyObject* iterable) {
  if ((PyObject*)self == iterable) {
    PyObject* sequence = PySequence_List(iterable);
    if (sequence == NULL) {
      return NULL;
    }

    PyObject* result = ConcurrentDeque_extend(self, sequence);
    Py_DECREF(sequence);
    return result;
  }

  PyObject* iter = PyObject_GetIter(iterable);
  if (iter == NULL) {
    return NULL;
  }

  ConcurrentDequeList* next_list = _ConcurrentDequeList_fromiter(
      iter, _ConcurrentDequeList_fromiter_FORWARD);

  if (PyErr_Occurred()) {
    return NULL;
  } else if (next_list == NULL) {
    Py_RETURN_NONE;
  }

  ConcurrentDequeNode* head = next_list->head;
  ConcurrentDequeList* next_list_locked = ConcurrentDequeList_locked(next_list);

  ConcurrentDeque_backoff_loop {
    ConcurrentDequeList* list = ConcurrentDeque_list(self);

    if (list == NULL) {
      if (ConcurrentDeque_try_replace(self, &list, next_list)) {
        Py_RETURN_NONE;
      }
    } else if (ConcurrentDeque_try_replace(self, &list, next_list_locked)) {
      next_list->head = list->head;
      head->prev = list->tail;
      head->prev->next = head;

      ConcurrentDeque_replace(self, next_list);

      ConcurrentDequeList_dealloc_shallow(list);
      Py_RETURN_NONE;
    }
  }
}

PyDoc_STRVAR(
    ConcurrentDeque_extendleft__doc__,
    "extendleft($self, iterable, /)\n"
    "--\n"
    "\n"
    "Extend the left side of the deque with elements from the iterable.");

/* Extend the left side of the deque with elements from the iterable.
 */
static PyObject* ConcurrentDeque_extendleft(
    ConcurrentDequeObject* self,
    PyObject* iterable) {
  if ((PyObject*)self == iterable) {
    PyObject* sequence = PySequence_List(iterable);
    if (sequence == NULL) {
      return NULL;
    }

    PyObject* result = ConcurrentDeque_extendleft(self, sequence);
    Py_DECREF(sequence);
    return result;
  }

  PyObject* iter = PyObject_GetIter(iterable);
  if (iter == NULL) {
    return NULL;
  }

  ConcurrentDequeList* next_list = _ConcurrentDequeList_fromiter(
      iter, _ConcurrentDequeList_fromiter_BACKWARD);

  if (PyErr_Occurred()) {
    return NULL;
  } else if (next_list == NULL) {
    Py_RETURN_NONE;
  }

  ConcurrentDequeNode* tail = next_list->tail;
  ConcurrentDequeList* next_list_locked = ConcurrentDequeList_locked(next_list);

  ConcurrentDeque_backoff_loop {
    ConcurrentDequeList* list = ConcurrentDeque_list(self);

    if (list == NULL) {
      if (ConcurrentDeque_try_replace(self, &list, next_list)) {
        Py_RETURN_NONE;
      }
    } else if (ConcurrentDeque_try_replace(self, &list, next_list_locked)) {
      next_list->tail = list->tail;
      tail->next = list->head;
      tail->next->prev = tail;

      ConcurrentDeque_replace(self, next_list);

      ConcurrentDequeList_dealloc_shallow(list);
      Py_RETURN_NONE;
    }
  }
}

PyDoc_STRVAR(
    ConcurrentDeque_pop__doc__,
    "pop($self, /)\n"
    "--\n"
    "\n"
    "Remove and return the rightmost element.");

/* Remove and return the rightmost element.
 */
static PyObject* ConcurrentDeque_pop(ConcurrentDequeObject* self) {
  ConcurrentDequeList* next_list = ConcurrentDequeList_alloc(NULL, NULL);

  if (next_list == NULL) {
    return NULL;
  }

  ConcurrentDequeList* next_list_locked = ConcurrentDequeList_locked(next_list);

  ConcurrentDeque_backoff_loop {
    ConcurrentDequeList* list = ConcurrentDeque_list(self);

    if (list == NULL) {
      PyErr_SetString(PyExc_RuntimeError, "pop from an empty ConcurrentDeque");
      ConcurrentDequeList_dealloc_shallow(next_list);
      return NULL;
    }

    if (ConcurrentDeque_try_replace(self, &list, next_list_locked)) {
      ConcurrentDequeNode* tail = list->tail;
      ConcurrentDequeNode* prev = tail->prev;
      PyObject* datum = tail->datum;

      if (prev == NULL) {
        ConcurrentDeque_replace(self, NULL);

        ConcurrentDequeNode_dealloc_shallow(tail);
        ConcurrentDequeList_dealloc_shallow(list);
        ConcurrentDequeList_dealloc_shallow(next_list);

        return datum;
      } else {
        next_list->head = list->head;
        next_list->tail = prev;
        prev->next = NULL;

        ConcurrentDeque_replace(self, next_list);

        ConcurrentDequeNode_dealloc_shallow(tail);
        ConcurrentDequeList_dealloc_shallow(list);

        return datum;
      }
    }
  }
}

PyDoc_STRVAR(
    ConcurrentDeque_popleft__doc__,
    "popleft($self, /)\n"
    "--\n"
    "\n"
    "Remove and return the leftmost element.");

/* Remove and return the leftmost element.
 */
static PyObject* ConcurrentDeque_popleft(ConcurrentDequeObject* self) {
  ConcurrentDequeList* next_list = ConcurrentDequeList_alloc(NULL, NULL);

  if (next_list == NULL) {
    return NULL;
  }

  ConcurrentDequeList* next_list_locked = ConcurrentDequeList_locked(next_list);

  ConcurrentDeque_backoff_loop {
    ConcurrentDequeList* list = ConcurrentDeque_list(self);

    if (list == NULL) {
      PyErr_SetString(PyExc_RuntimeError, "pop from an empty ConcurrentDeque");
      ConcurrentDequeList_dealloc_shallow(next_list);
      return NULL;
    }

    if (ConcurrentDeque_try_replace(self, &list, next_list_locked)) {
      ConcurrentDequeNode* head = list->head;
      ConcurrentDequeNode* next = head->next;
      PyObject* datum = head->datum;

      if (next == NULL) {
        ConcurrentDeque_replace(self, NULL);

        ConcurrentDequeNode_dealloc_shallow(head);
        ConcurrentDequeList_dealloc_shallow(list);
        ConcurrentDequeList_dealloc_shallow(next_list);

        return datum;
      } else {
        next_list->head = next;
        next_list->tail = list->tail;
        next->prev = NULL;

        ConcurrentDeque_replace(self, next_list);

        ConcurrentDequeNode_dealloc_shallow(head);
        ConcurrentDequeList_dealloc_shallow(list);

        return datum;
      }
    }
  }
}

PyDoc_STRVAR(
    ConcurrentDeque_remove__doc__,
    "remove($self, value, /)\n"
    "--\n"
    "\n"
    "Remove first occurrence of value.\n"
    "\n"
    "Note that this function is not atomic and will not lock the "
    "ConcurrentDeque, meaning it may not be safe in a multi-threaded "
    "environment. If you need consistency, consider using a readers-writer "
    "lock.");

/* Remove first occurrence of value.
 */
static PyObject* ConcurrentDeque_remove(
    ConcurrentDequeObject* self,
    PyObject* value) {
  ConcurrentDequeList* list = ConcurrentDeque_list(self);

  if (list == NULL) {
    PyErr_SetString(
        PyExc_ValueError,
        "ConcurrentDeque.remove(x): x not in ConcurrentDeque");

    return NULL;
  }

  ConcurrentDequeNode* current = list->head;
  ConcurrentDequeNode* prev = NULL;
  ConcurrentDequeNode* next = NULL;

  while (current != NULL) {
    next = current->next;

    PyObject* datum = Py_NewRef(current->datum);
    int cmp = PyObject_RichCompareBool(datum, value, Py_EQ);

    Py_DECREF(datum);
    if (PyErr_Occurred()) {
      return NULL;
    }

    if (cmp != 0) {
      /* Here we have found the value. We need to remove it from the list.
       * The mannier in which we remove the value depends on its position in
       * the list.
       */
      if (current == list->head && current == list->tail) {
        /* Replacing the entire list. */
        ConcurrentDeque_replace(self, NULL);

        ConcurrentDequeList_dealloc_shallow(list);
        ConcurrentDequeNode_dealloc(current);
        Py_RETURN_NONE;
      } else if (current == list->head) {
        /* Replacing the head of the list. */
        ConcurrentDequeList* next_list =
            ConcurrentDequeList_alloc(next, list->tail);

        if (next_list == NULL) {
          return NULL;
        }

        next->prev = NULL;
        ConcurrentDeque_replace(self, next_list);

        ConcurrentDequeList_dealloc_shallow(list);
        ConcurrentDequeNode_dealloc(current);
        Py_RETURN_NONE;
      } else if (current == list->tail) {
        /* Replacing the tail of the list. */
        ConcurrentDequeList* next_list =
            ConcurrentDequeList_alloc(list->head, prev);

        if (next_list == NULL) {
          return NULL;
        }

        prev->next = NULL;
        ConcurrentDeque_replace(self, next_list);

        ConcurrentDequeList_dealloc_shallow(list);
        ConcurrentDequeNode_dealloc(current);
        Py_RETURN_NONE;
      } else {
        /* Replacing a node in the middle of the list. */
        prev->next = next;
        next->prev = prev;

        ConcurrentDequeNode_dealloc(current);
        Py_RETURN_NONE;
      }
    }

    prev = current;
    current = next;
  }

  if (current == NULL) {
    PyErr_SetString(
        PyExc_ValueError,
        "ConcurrentDeque.remove(x): x not in ConcurrentDeque");

    return NULL;
  }

  Py_RETURN_NONE;
}

PyDoc_STRVAR(
    ConcurrentDeque_rotate__doc__,
    "rotate($self, n=1, /)\n"
    "--\n"
    "\n"
    "Rotate the deque n steps to the right. If n is negative, rotates left.");

/* Rotate the deque n steps to the right. If n is negative, rotates left.
 */
static PyObject* ConcurrentDeque_rotate(
    ConcurrentDequeObject* self,
    PyObject* value) {
  Py_ssize_t n = -1;

  PyObject* number = PyNumber_Index(value);
  if (number != NULL) {
    n = PyLong_AsSsize_t(number);
    Py_DECREF(number);
  }

  if (n == -1 && PyErr_Occurred()) {
    return NULL;
  }

  Py_ssize_t i;
  if (n > 0) {
    for (i = 0; i < n; i++) {
      PyObject* datum = ConcurrentDeque_pop(self);
      if (datum == NULL) {
        return NULL;
      }

      if (ConcurrentDeque_appendleft(self, datum) == NULL) {
        Py_DECREF(datum);
        return NULL;
      }

      Py_DECREF(datum);
    }
  } else if (n < 0) {
    for (i = 0; i < -n; i++) {
      PyObject* datum = ConcurrentDeque_popleft(self);
      if (datum == NULL) {
        return NULL;
      }

      if (ConcurrentDeque_append(self, datum) == NULL) {
        Py_DECREF(datum);
        return NULL;
      }

      Py_DECREF(datum);
    }
  }

  Py_RETURN_NONE;
}

/* Implement __repr__ for ConcurrentDeque, taking into account cycles.
 */
static PyObject* ConcurrentDeque_repr(ConcurrentDequeObject* self) {
  int state = Py_ReprEnter((PyObject*)self);
  if (state != 0) {
    if (state < 0) {
      return NULL;
    }
    return PyUnicode_FromString("[...]");
  }

  PyObject* aslist = PySequence_List((PyObject*)self);
  if (aslist == NULL) {
    Py_ReprLeave((PyObject*)self);
    return NULL;
  }

  PyObject* result =
      PyUnicode_FromFormat("%s(%R)", _PyType_Name(Py_TYPE(self)), aslist);

  Py_ReprLeave((PyObject*)self);
  Py_DECREF(aslist);

  return result;
}

/* Return the length of the given ConcurrentDeque, which is stored as part of
 * the var object struct.
 */
static Py_ssize_t ConcurrentDeque_len(ConcurrentDequeObject* self) {
  ConcurrentDequeList* list = ConcurrentDeque_list(self);
  if (list == NULL) {
    return 0;
  }

  ConcurrentDequeNode* node;
  Py_ssize_t length = 0;

  for (node = list->head; node != NULL; node = node->next) {
    ++length;
  }

  return length;
}

/* Returns the item at the specified index (counted from the left).
 */
static PyObject* ConcurrentDeque_item(
    ConcurrentDequeObject* self,
    Py_ssize_t index) {
  if (index < (Py_ssize_t)0) {
    // Negative indices are invalid. This shouldn't ever occur because we have
    // filled the sq_length slot, but it's here for completeness.
    goto invalid;
  }

  ConcurrentDequeList* list = ConcurrentDeque_list(self);
  if (list == NULL) {
    // If the list is empty, any index is invalid.
    goto invalid;
  }

  ConcurrentDequeNode* node = list->head;
  for (Py_ssize_t i = 0; i < index && node != NULL; i++) {
    node = node->next;
  }

  if (node == NULL) {
    // If we didn't get to a node at the given index, then it is invalid.
    goto invalid;
  }

  return Py_NewRef(node->datum);

invalid:
  PyErr_SetString(PyExc_IndexError, "ConcurrentDeque index out of range");
  return NULL;
}

/* Determines if the given value is contained within the given deque.
 */
static int ConcurrentDeque_contains(
    ConcurrentDequeObject* self,
    PyObject* value) {
  ConcurrentDequeList* list = ConcurrentDeque_list(self);
  if (list == NULL) {
    return 0;
  }

  for (ConcurrentDequeNode* node = list->head; node != NULL;
       node = node->next) {
    PyObject* datum = Py_NewRef(node->datum);
    int cmp = PyObject_RichCompareBool(datum, value, Py_EQ);

    Py_DECREF(datum);
    if (PyErr_Occurred()) {
      return -1;
    }

    if (cmp != 0) {
      return cmp;
    }
  }

  return 0;
}

static PyObject* ConcurrentDeque_richcompare(PyObject* v, PyObject* w, int op);

/* An iterator that knows how to iterate through a concurrent deque. Note that
 * this is inherently racy, since it is iterating through a snapshot of the
 * deque.
 */
typedef struct {
  PyObject_HEAD PyObject* deque;
  ConcurrentDequeNode* current;
  PyObject* weakreflist;
} ConcurrentDequeIteratorObject;

static PyTypeObject ConcurrentDequeIteratorType;

/* Implement __iter__ for ConcurrentDeque.
 */
static PyObject* ConcurrentDeque_iter(ConcurrentDequeObject* self) {
  ConcurrentDequeIteratorObject* iterator = PyObject_GC_New(
      ConcurrentDequeIteratorObject, &ConcurrentDequeIteratorType);

  if (iterator == NULL) {
    return NULL;
  }

  iterator->deque = Py_NewRef(self);
  iterator->weakreflist = NULL;

  ConcurrentDequeList* list = ConcurrentDeque_list(self);
  iterator->current = list == NULL ? NULL : list->head;

  PyObject_GC_Track(iterator);
  return (PyObject*)iterator;
}

/* Provide the clear implementation for the GC.
 */
static int ConcurrentDequeIterator_clear(ConcurrentDequeIteratorObject* self) {
  Py_DECREF(self->deque);
  return 0;
}

/* Provide the traverse implementation for the GC.
 */
static int ConcurrentDequeIterator_traverse(
    ConcurrentDequeIteratorObject* self,
    visitproc visit,
    void* arg) {
  Py_VISIT(self->deque);
  return 0;
}

/* Provide the dealloc implementation for the GC.
 */
static void ConcurrentDequeIterator_dealloc(
    ConcurrentDequeIteratorObject* self) {
  PyTypeObject* tp = Py_TYPE(self);
  PyObject_GC_UnTrack(self);

  if (self->weakreflist != NULL) {
    PyObject_ClearWeakRefs((PyObject*)self);
  }

  (void)ConcurrentDequeIterator_clear(self);
  tp->tp_free(self);
}

/* Provide the next implementation for the iterator.
 */
static PyObject* ConcurrentDequeIterator_next(
    ConcurrentDequeIteratorObject* self) {
  if (self->current == NULL) {
    return NULL;
  }

  PyObject* datum = Py_NewRef(self->current->datum);
  self->current = self->current->next;

  return datum;
}

static PyTypeObject ConcurrentDequeIteratorType = {
    PyVarObject_HEAD_INIT(NULL, 0).tp_name =
        "_concurrent.ConcurrentDequeIterator",
    .tp_doc = "ConcurrentDequeIterator",
    .tp_basicsize = sizeof(ConcurrentDequeIteratorObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_weaklistoffset = offsetof(ConcurrentDequeIteratorObject, weakreflist),

    .tp_clear = (inquiry)ConcurrentDequeIterator_clear,
    .tp_traverse = (traverseproc)ConcurrentDequeIterator_traverse,
    .tp_dealloc = (destructor)ConcurrentDequeIterator_dealloc,

    .tp_iter = PyObject_SelfIter,
    .tp_iternext = (iternextfunc)ConcurrentDequeIterator_next,
};

static PyMethodDef ConcurrentDeque_methods[] = {
    {"append",
     (PyCFunction)ConcurrentDeque_append,
     METH_O,
     ConcurrentDeque_append__doc__},
    {"appendleft",
     (PyCFunction)ConcurrentDeque_appendleft,
     METH_O,
     ConcurrentDeque_appendleft__doc__},
    {"clear",
     (PyCFunction)ConcurrentDeque_clearmethod,
     METH_NOARGS,
     ConcurrentDeque_clearmethod__doc__},
    {"extend",
     (PyCFunction)ConcurrentDeque_extend,
     METH_O,
     ConcurrentDeque_extend__doc__},
    {"extendleft",
     (PyCFunction)ConcurrentDeque_extendleft,
     METH_O,
     ConcurrentDeque_extendleft__doc__},
    {"pop",
     (PyCFunction)ConcurrentDeque_pop,
     METH_NOARGS,
     ConcurrentDeque_pop__doc__},
    {"popleft",
     (PyCFunction)ConcurrentDeque_popleft,
     METH_NOARGS,
     ConcurrentDeque_popleft__doc__},
    {"remove",
     (PyCFunction)ConcurrentDeque_remove,
     METH_O,
     ConcurrentDeque_remove__doc__},
    {"rotate",
     (PyCFunction)ConcurrentDeque_rotate,
     METH_O,
     ConcurrentDeque_rotate__doc__},
    {"__class_getitem__",
     Py_GenericAlias,
     METH_O | METH_CLASS,
     PyDoc_STR("See PEP 585")},
    {NULL, NULL, 0, NULL},
};

static PySequenceMethods ConcurrentDequeType_as_sequence = {
    .sq_length = (lenfunc)ConcurrentDeque_len,
    .sq_item = (ssizeargfunc)ConcurrentDeque_item,
    .sq_contains = (objobjproc)ConcurrentDeque_contains,
};

static PyTypeObject ConcurrentDequeType = {
    PyVarObject_HEAD_INIT(NULL, 0).tp_name = "_concurrent.ConcurrentDeque",
    .tp_doc = (void*)ConcurrentDeque_init__doc__,
    .tp_basicsize = sizeof(ConcurrentDequeObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC |
        Py_TPFLAGS_SEQUENCE | Py_TPFLAGS_IMMUTABLETYPE,
    .tp_weaklistoffset = offsetof(ConcurrentDequeObject, weakreflist),

    .tp_clear = (inquiry)ConcurrentDeque_clear,
    .tp_traverse = (traverseproc)ConcurrentDeque_traverse,
    .tp_new = ConcurrentDeque_new,
    .tp_init = ConcurrentDeque_init,
    .tp_dealloc = (destructor)ConcurrentDeque_dealloc,

    .tp_methods = ConcurrentDeque_methods,
    .tp_repr = (reprfunc)ConcurrentDeque_repr,
    .tp_iter = (getiterfunc)ConcurrentDeque_iter,
    .tp_richcompare = (richcmpfunc)ConcurrentDeque_richcompare,
    .tp_as_sequence = &ConcurrentDequeType_as_sequence,
};

/* Implement rich comparison methods for ConcurrentDeque
 */
static PyObject*
ConcurrentDeque_richcompare(PyObject* left, PyObject* right, int op) {
  if (!PyObject_TypeCheck(left, &ConcurrentDequeType) ||
      !PyObject_TypeCheck(right, &ConcurrentDequeType)) {
    Py_RETURN_NOTIMPLEMENTED;
  }

  PyObject* left_iter = NULL;
  PyObject* right_iter = NULL;
  int cmp = -1;

  left_iter = PyObject_GetIter(left);
  if (left_iter == NULL) {
    goto done;
  }

  right_iter = PyObject_GetIter(right);
  if (right_iter == NULL) {
    goto done;
  }

  PyObject* left_elem = NULL;
  PyObject* right_elem = NULL;

  for (;;) {
    left_elem = PyIter_Next(left_iter);
    if (left_elem == NULL && PyErr_Occurred()) {
      goto done;
    }

    right_elem = PyIter_Next(right_iter);
    if (right_elem == NULL && PyErr_Occurred()) {
      goto done;
    }

    /* If we have reached the end of one of the lists, break out of our loop. */
    if (left_elem == NULL || right_elem == NULL) {
      Py_XDECREF(left_elem);
      Py_XDECREF(right_elem);
      break;
    }

    int b = PyObject_RichCompareBool(left_elem, right_elem, Py_EQ);
    if (b == 0) {
      cmp = PyObject_RichCompareBool(left_elem, right_elem, op);
      Py_DECREF(left_elem);
      Py_DECREF(right_elem);
      goto done;
    }

    Py_DECREF(left_elem);
    Py_DECREF(right_elem);
    if (b < 0) {
      goto done;
    }
  }

  switch (op) {
    case Py_LT:
      cmp = right_elem != NULL;
      break; /* if right was longer */
    case Py_LE:
      cmp = left_elem == NULL;
      break; /* if left was not longer */
    case Py_EQ:
      cmp = left_elem == right_elem;
      break; /* if we reached the end of both */
    case Py_NE:
      cmp = left_elem != right_elem;
      break; /* if one ConcurrentDeque continues */
    case Py_GT:
      cmp = left_elem != NULL;
      break; /* if left was longer */
    case Py_GE:
      cmp = right_elem == NULL;
      break; /* if right was not longer */
  }

done:
  Py_XDECREF(left_iter);
  Py_XDECREF(right_iter);

  if (cmp == 1) {
    Py_RETURN_TRUE;
  } else if (cmp == 0) {
    Py_RETURN_FALSE;
  } else {
    return NULL;
  }
}

/* *******************
   End ConcurrentDeque
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
  if (PyType_Ready(&ConcurrentDequeType) < 0) {
    return -1;
  }
  if (PyType_Ready(&ConcurrentDequeIteratorType) < 0) {
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
  if (PyModule_AddObjectRef(
          module, "ConcurrentDeque", (PyObject*)&ConcurrentDequeType) < 0) {
    return -1;
  }
  if (PyModule_AddObjectRef(
          module,
          "ConcurrentDequeIterator",
          (PyObject*)&ConcurrentDequeIteratorType) < 0) {
    return -1;
  }

  return 0;
}

static struct PyModuleDef_Slot module_slots[] = {
    {Py_mod_exec, exec_local_module},
    _PY_NOGIL_MODULE_SLOT // NOLINT
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
