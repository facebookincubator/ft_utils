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

  return value != NULL ? PyDict_SetItem(self->buckets[index], key, value)
                       : PyDict_DelItem(self->buckets[index], key);
}

static void ConcurrentDict_dealloc(ConcurrentDictObject* self) {
  PyObject_GC_UnTrack(self);
  ConcurrentDict_clear(self);
  PyObject_ClearWeakRefs((PyObject*)self);
  PyObject_GC_Del(self);
}

static PyObject*
ConcurrentDict_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
  Py_ssize_t initial_capacity = 0;
  PyObject* dictionary = NULL;
  static char* kwlist[] = {"initial_capacity", "dictionary", NULL};

  if (!PyArg_ParseTupleAndKeywords(
          args, kwds, "|nO", kwlist, &initial_capacity, &dictionary)) {
    return NULL;
  }

  if (dictionary != NULL && !PyDict_Check(dictionary)) {
    PyErr_SetString(PyExc_TypeError, "dictionary must be a dict type");
    return NULL;
  }

  if (dictionary != NULL) {
    Py_ssize_t dict_size = PyDict_Size(dictionary);
    if (initial_capacity == 0 && dict_size > 0) {
      initial_capacity = dict_size;
    } else {
      initial_capacity += dict_size;
    }
  }
  if (initial_capacity <= 0) {
    // Random prime number chosen to reduce collision in buckets
    initial_capacity = 17;
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

    if (dictionary != NULL) {
      PyObject* key;
      PyObject* value;
      Py_ssize_t pos = 0;
      while (PyDict_Next(dictionary, &pos, &key, &value)) {
        if (ConcurrentDict_setitem(self, key, value) < 0) {
          Py_DECREF(self);
          return NULL;
        }
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

/* Clear all entries from the ConcurrentDict without deallocating buckets. */
static PyObject* ConcurrentDict_clearmethod(
    ConcurrentDictObject* self,
    PyObject* Py_UNUSED(args)) {
  for (Py_ssize_t i = 0; i < self->size; i++) {
    if (self->buckets[i]) {
      PyDict_Clear(self->buckets[i]);
    }
  }
  Py_RETURN_NONE;
}

/* Get a value by key, returning a default if not found. */
static PyObject* ConcurrentDict_get(
    ConcurrentDictObject* self,
    PyObject* args) {
  PyObject* key;
  PyObject* default_value = Py_None;

  if (!PyArg_ParseTuple(args, "O|O", &key, &default_value)) {
    return NULL;
  }

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
    return Py_NewRef(default_value);
  }

  return value;
}

/* If key is not in the dict, insert it with default and return default.
 * If key is in the dict, return its value.
 * Thread-safe within a single shard. */
static PyObject* ConcurrentDict_setdefault(
    ConcurrentDictObject* self,
    PyObject* args) {
  PyObject* key;
  PyObject* default_value = Py_None;

  if (!PyArg_ParseTuple(args, "O|O", &key, &default_value)) {
    return NULL;
  }

  Py_hash_t hash = PyObject_Hash(key);
  if (hash == -1 && PyErr_Occurred()) {
    return NULL;
  }

  Py_ssize_t index = hash % self->size;
  if (index < 0) {
    index = -index;
  }
#ifdef Py_GIL_DISABLED
  PyObject* value = NULL;
  if (PyDict_SetDefaultRef(self->buckets[index], key, default_value, &value) <
      0) {
    return NULL;
  }
  return value;
#else
  PyObject* value = PyDict_SetDefault(self->buckets[index], key, default_value);
  if (value == NULL) {
    return NULL;
  }
  return Py_NewRef(value);
#endif
}

/* Remove and return the value for key.
 * Raises KeyError if key is not found and no default is given. */
static PyObject* ConcurrentDict_pop(
    ConcurrentDictObject* self,
    PyObject* args) {
  PyObject* key;
  PyObject* default_value = NULL;

  if (!PyArg_ParseTuple(args, "O|O", &key, &default_value)) {
    return NULL;
  }

  Py_hash_t hash = PyObject_Hash(key);
  if (hash == -1 && PyErr_Occurred()) {
    return NULL;
  }

  Py_ssize_t index = hash % self->size;
  if (index < 0) {
    index = -index;
  }

#ifdef Py_GIL_DISABLED
  PyObject* value = NULL;
  int result = PyDict_Pop(self->buckets[index], key, &value);
  if (result < 0) {
    return NULL;
  } else if (result == 0) {
    if (default_value != NULL) {
      return Py_NewRef(default_value);
    }
    PyErr_SetObject(PyExc_KeyError, key);
    return NULL;
  }
  return value;
#else
  PyObject* value = NULL;
  int result = PyDict_GetItemRef(self->buckets[index], key, &value);
  if (result < 0) {
    return NULL;
  } else if (result == 0) {
    if (default_value != NULL) {
      return Py_NewRef(default_value);
    }
    PyErr_SetObject(PyExc_KeyError, key);
    return NULL;
  }
  if (PyDict_DelItem(self->buckets[index], key) < 0) {
    Py_DECREF(value);
    return NULL;
  }
  return value;
#endif
}

/* Update from a mapping that supports keys() and __getitem__. */
static int ConcurrentDict_update_from_keys(
    ConcurrentDictObject* self,
    PyObject* source,
    PyObject* keys) {
  PyObject* iter = PyObject_GetIter(keys);
  if (iter == NULL) {
    return -1;
  }
  PyObject* key;
  while ((key = PyIter_Next(iter)) != NULL) {
    PyObject* value = PyObject_GetItem(source, key);
    if (value == NULL) {
      Py_DECREF(key);
      Py_DECREF(iter);
      return -1;
    }
    int rc = ConcurrentDict_setitem(self, key, value);
    Py_DECREF(key);
    Py_DECREF(value);
    if (rc < 0) {
      Py_DECREF(iter);
      return -1;
    }
  }
  Py_DECREF(iter);
  if (PyErr_Occurred()) {
    return -1;
  }
  return 0;
}

/* Update from an iterable of (key, value) pairs. */
static int ConcurrentDict_update_from_pairs(
    ConcurrentDictObject* self,
    PyObject* source) {
  PyObject* iter = PyObject_GetIter(source);
  if (iter == NULL) {
    return -1;
  }
  PyObject* item;
  while ((item = PyIter_Next(iter)) != NULL) {
    PyObject* key = NULL;
    PyObject* value = NULL;
    if (!PyArg_ParseTuple(item, "OO", &key, &value)) {
      Py_DECREF(item);
      Py_DECREF(iter);
      return -1;
    }
    int rc = ConcurrentDict_setitem(self, key, value);
    Py_DECREF(item);
    if (rc < 0) {
      Py_DECREF(iter);
      return -1;
    }
  }
  Py_DECREF(iter);
  if (PyErr_Occurred()) {
    return -1;
  }
  return 0;
}

/* Update this ConcurrentDict from a mapping or iterable of key-value pairs.
 *
 *   cd = ConcurrentDict()
 *   cd.update({"a": 1, "b": 2})        # from a mapping
 *   cd.update([("c", 3), ("d", 4)])     # from (key, value) pairs
 *   cd.update(e=5, f=6)                 # from keyword arguments
 *   cd.update({"g": 7}, h=8)            # positional + kwargs combined
 */
static PyObject* ConcurrentDict_update(
    ConcurrentDictObject* self,
    PyObject* args,
    PyObject* kwds) {
  /* Optional positional arg: a mapping or iterable of (key, value) pairs
   * to merge into this ConcurrentDict. */
  PyObject* source = NULL;

  if (!PyArg_ParseTuple(args, "|O", &source)) {
    return NULL;
  }

  if (source != NULL) {
    PyObject* keys = PyObject_CallMethod(source, "keys", NULL);
    if (keys != NULL) {
      int rc = ConcurrentDict_update_from_keys(self, source, keys);
      Py_DECREF(keys);
      if (rc < 0) {
        return NULL;
      }
    } else {
      PyErr_Clear();
      if (ConcurrentDict_update_from_pairs(self, source) < 0) {
        return NULL;
      }
    }
  }

  /* Handle keyword arguments */
  if (kwds != NULL && PyDict_Size(kwds) > 0) {
    PyObject* key;
    PyObject* value;
    Py_ssize_t pos = 0;
    while (PyDict_Next(kwds, &pos, &key, &value)) {
      if (ConcurrentDict_setitem(self, key, value) < 0) {
        return NULL;
      }
    }
  }

  Py_RETURN_NONE;
}

/* Return a list of all keys. Not thread consistent. */
static PyObject* ConcurrentDict_keys(
    ConcurrentDictObject* self,
    PyObject* Py_UNUSED(args)) {
  PyObject* list = PyList_New(0);
  if (!list) {
    return NULL;
  }
  for (Py_ssize_t i = 0; i < self->size; i++) {
    if (self->buckets[i]) {
      PyObject* bucket_keys = PyDict_Keys(self->buckets[i]);
      if (!bucket_keys) {
        Py_DECREF(list);
        return NULL;
      }
      Py_ssize_t n = PyList_Size(bucket_keys);
      for (Py_ssize_t j = 0; j < n; j++) {
        if (PyList_Append(list, PyList_GetItem(bucket_keys, j)) < 0) {
          Py_DECREF(bucket_keys);
          Py_DECREF(list);
          return NULL;
        }
      }
      Py_DECREF(bucket_keys);
    }
  }
  return list;
}

/* Return a list of all values. Not thread consistent. */
static PyObject* ConcurrentDict_values(
    ConcurrentDictObject* self,
    PyObject* Py_UNUSED(args)) {
  PyObject* list = PyList_New(0);
  if (!list) {
    return NULL;
  }
  for (Py_ssize_t i = 0; i < self->size; i++) {
    if (self->buckets[i]) {
      PyObject* bucket_values = PyDict_Values(self->buckets[i]);
      if (!bucket_values) {
        Py_DECREF(list);
        return NULL;
      }
      Py_ssize_t n = PyList_Size(bucket_values);
      for (Py_ssize_t j = 0; j < n; j++) {
        if (PyList_Append(list, PyList_GetItem(bucket_values, j)) < 0) {
          Py_DECREF(bucket_values);
          Py_DECREF(list);
          return NULL;
        }
      }
      Py_DECREF(bucket_values);
    }
  }
  return list;
}

/* Return a list of all (key, value) tuples. Not thread consistent. */
static PyObject* ConcurrentDict_items(
    ConcurrentDictObject* self,
    PyObject* Py_UNUSED(args)) {
  PyObject* list = PyList_New(0);
  if (!list) {
    return NULL;
  }
  for (Py_ssize_t i = 0; i < self->size; i++) {
    if (self->buckets[i]) {
      PyObject* bucket_items = PyDict_Items(self->buckets[i]);
      if (!bucket_items) {
        Py_DECREF(list);
        return NULL;
      }
      Py_ssize_t n = PyList_Size(bucket_items);
      for (Py_ssize_t j = 0; j < n; j++) {
        if (PyList_Append(list, PyList_GetItem(bucket_items, j)) < 0) {
          Py_DECREF(bucket_items);
          Py_DECREF(list);
          return NULL;
        }
      }
      Py_DECREF(bucket_items);
    }
  }
  return list;
}

/* ---- Iterator ---- */

typedef struct {
  PyObject_HEAD ConcurrentDictObject* dict;
  Py_ssize_t bucket_index;
  Py_ssize_t pos; /* position within current bucket (for PyDict_Next) */
  PyObject* weakreflist;
} ConcurrentDictIteratorObject;

static int ConcurrentDictIterator_clear(ConcurrentDictIteratorObject* self) {
  Py_CLEAR(self->dict);
  return 0;
}

static int ConcurrentDictIterator_traverse(
    ConcurrentDictIteratorObject* self,
    visitproc visit,
    void* arg) {
  Py_VISIT(self->dict);
  return 0;
}

static void ConcurrentDictIterator_dealloc(ConcurrentDictIteratorObject* self) {
  PyObject_GC_UnTrack(self);
  if (self->weakreflist != NULL) {
    PyObject_ClearWeakRefs((PyObject*)self);
  }
  (void)ConcurrentDictIterator_clear(self);
  PyObject_GC_Del(self);
}

/* Return the next key from the ConcurrentDict.
 * Walks through buckets sequentially, using PyDict_Next within each bucket.
 * Not thread consistent — concurrent modifications may cause skipped or
 * repeated keys.
 */
static PyObject* ConcurrentDictIterator_next(
    ConcurrentDictIteratorObject* self) {
  ConcurrentDictObject* dict = self->dict;
  if (dict == NULL) {
    return NULL;
  }

  PyObject* key;
  PyObject* value;
  while (self->bucket_index < dict->size) {
    PyObject* bucket = dict->buckets[self->bucket_index];
    if (bucket && PyDict_Next(bucket, &self->pos, &key, &value)) {
      return Py_NewRef(key);
    }
    /* Move to next bucket */
    self->bucket_index++;
    self->pos = 0;
  }
  /* Exhausted all buckets */
  return NULL;
}

PyTypeObject ConcurrentDictIteratorType = {
    PyVarObject_HEAD_INIT(NULL, 0).tp_name =
        "_concurrency.ConcurrentDictIterator",
    .tp_doc = "ConcurrentDictIterator",
    .tp_basicsize = sizeof(ConcurrentDictIteratorObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC,
    .tp_weaklistoffset = offsetof(ConcurrentDictIteratorObject, weakreflist),

    .tp_clear = (inquiry)ConcurrentDictIterator_clear,
    .tp_traverse = (traverseproc)ConcurrentDictIterator_traverse,
    .tp_dealloc = (destructor)ConcurrentDictIterator_dealloc,

    .tp_iter = PyObject_SelfIter,
    .tp_iternext = (iternextfunc)ConcurrentDictIterator_next,
};

static PyObject* ConcurrentDict_iter(ConcurrentDictObject* self) {
  ConcurrentDictIteratorObject* iterator = PyObject_GC_New(
      ConcurrentDictIteratorObject, &ConcurrentDictIteratorType);

  if (iterator == NULL) {
    return NULL;
  }

  iterator->dict = (ConcurrentDictObject*)Py_NewRef(self);
  iterator->bucket_index = 0;
  iterator->pos = 0;
  iterator->weakreflist = NULL;

  PyObject_GC_Track(iterator);
  return (PyObject*)iterator;
}

/* ---- GC / infrastructure ---- */

/* Compare two ConcurrentDicts for equality.
 * Two ConcurrentDicts are equal if they have the same key-value pairs.
 * Not thread consistent.
 *
 * TODO: This is inefficient — we clone the entire ConcurrentDict into a
 * plain dict on each call just to delegate to PyObject_RichCompareBool.
 * Better approach:
 *  1. Fast-reject on ConcurrentDict_len mismatch (O(buckets), not O(keys)).
 *  2. If both sides have the same bucket count, compare buckets[i] pairwise
 *     — keys hash to the same index, so no copying is needed.
 *  3. Fall back to current cloning only when bucket counts differ.
 *  4. For ConcurrentDict-vs-dict, iterate the dict and do per-key lookups. */
static PyObject*
ConcurrentDict_richcompare(PyObject* self_obj, PyObject* other_obj, int op) {
  if (op != Py_EQ && op != Py_NE) {
    Py_RETURN_NOTIMPLEMENTED;
  }

  /* Build dicts from both sides for comparison */
  PyObject* self_dict = NULL;
  PyObject* other_dict = NULL;
  int result;

  if (Py_TYPE(self_obj) == Py_TYPE(other_obj)) {
    /* Both are ConcurrentDicts */
    self_dict = ConcurrentDict_as_dict((ConcurrentDictObject*)self_obj, NULL);
    if (self_dict == NULL) {
      return NULL;
    }
    other_dict = ConcurrentDict_as_dict((ConcurrentDictObject*)other_obj, NULL);
    if (other_dict == NULL) {
      Py_DECREF(self_dict);
      return NULL;
    }
  } else if (PyDict_Check(other_obj)) {
    /* Compare ConcurrentDict with a regular dict */
    self_dict = ConcurrentDict_as_dict((ConcurrentDictObject*)self_obj, NULL);
    if (self_dict == NULL) {
      return NULL;
    }
    other_dict = Py_NewRef(other_obj);
  } else {
    Py_RETURN_NOTIMPLEMENTED;
  }

  result = PyObject_RichCompareBool(self_dict, other_dict, Py_EQ);
  Py_DECREF(self_dict);
  Py_DECREF(other_dict);

  if (result < 0) {
    return NULL;
  }

  if (op == Py_NE) {
    result = !result;
  }

  if (result) {
    Py_RETURN_TRUE;
  }
  Py_RETURN_FALSE;
}

/* Return a string representation: ConcurrentDict({...}).
 * Not thread consistent. */
static PyObject* ConcurrentDict_repr(ConcurrentDictObject* self) {
  PyObject* dict = ConcurrentDict_as_dict(self, NULL);
  if (dict == NULL) {
    return NULL;
  }
  PyObject* dict_repr = PyObject_Repr(dict);
  Py_DECREF(dict);
  if (dict_repr == NULL) {
    return NULL;
  }
  PyObject* result = PyUnicode_FromFormat("ConcurrentDict(%U)", dict_repr);
  Py_DECREF(dict_repr);
  return result;
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
    {"clear",
     (PyCFunction)ConcurrentDict_clearmethod,
     METH_NOARGS,
     PyDoc_STR(
         "Remove all items from the ConcurrentDict. Not thread consistent.")},
    {"get",
     (PyCFunction)ConcurrentDict_get,
     METH_VARARGS,
     PyDoc_STR(
         "D.get(key[, default]) -> value. Return value for key, or default if not present.")},
    {"setdefault",
     (PyCFunction)ConcurrentDict_setdefault,
     METH_VARARGS,
     PyDoc_STR(
         "D.setdefault(key[, default]) -> value. If key is not in D, insert key with default and return default. Thread-safe within a shard.")},
    {"pop",
     (PyCFunction)ConcurrentDict_pop,
     METH_VARARGS,
     PyDoc_STR(
         "D.pop(key[, default]) -> value. Remove key and return value. If key is not found, return default or raise KeyError.")},
    {"update",
     (PyCFunction)ConcurrentDict_update,
     METH_VARARGS | METH_KEYWORDS,
     PyDoc_STR(
         "D.update([other, ]**kwargs) -> None. Update from dict/iterable/kwargs. Not thread consistent.")},
    {"keys",
     (PyCFunction)ConcurrentDict_keys,
     METH_NOARGS,
     PyDoc_STR("Return a list of all keys. Not thread consistent.")},
    {"values",
     (PyCFunction)ConcurrentDict_values,
     METH_NOARGS,
     PyDoc_STR("Return a list of all values. Not thread consistent.")},
    {"items",
     (PyCFunction)ConcurrentDict_items,
     METH_NOARGS,
     PyDoc_STR(
         "Return a list of all (key, value) pairs. Not thread consistent.")},
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
    .tp_richcompare = ConcurrentDict_richcompare,
    .tp_repr = (reprfunc)ConcurrentDict_repr,
    .tp_iter = (getiterfunc)ConcurrentDict_iter,
};
