/* Copyright (c) Meta Platforms, Inc. and affiliates. */
#include "ft_utils.h"

/* Begin IntervalLock
 ********************
 */

typedef struct {
  PyObject_HEAD MUTEX_TYPE mutex;
  COND_TYPE cond;
  THREAD_TYPE owner;
  THREAD_TYPE previous_owner;
  ustimestamp_t lock_acquire_time;
  ustimestamp_t interval;
  /* We need this to avoid a race where the lock is unowed and signalled but
     the blocked 'waiter' threads have not worken up yet. In this case when we
     cede the previous thread gets the lock and does not cede to other threads.
  */
  int32_t waiters;
  int32_t locked;
} IntervalLock;

static PyObject*
IntervalLock_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
  IntervalLock* self;
  self = (IntervalLock*)type->tp_alloc(type, 0);
  if (self != NULL) {
    if (MUTEX_INIT(self->mutex) || COND_INIT(self->cond)) {
      PyErr_SetString(PyExc_RuntimeError, "Failed to initialize locks.");
      Py_DECREF((PyObject*)self);
      return NULL;
    }
    self->locked = 0;
    self->lock_acquire_time = 0;
    self->waiters = 0;
    self->owner = 0;
    self->previous_owner = 0;
  }
  return (PyObject*)self;
}

static int
IntervalLock_init(IntervalLock* self, PyObject* args, PyObject* kwds) {
  static char* kwlist[] = {"interval", NULL};
  double interval = 0.005; /* Default value for the interval */
  if (!PyArg_ParseTupleAndKeywords(args, kwds, "|d", kwlist, &interval)) {
    return -1;
  }
  /* Convert to microseconds. */
  self->interval = (uint64_t)(1000000 * interval);
  return 0;
}

static PyObject* IntervalLock_lock(IntervalLock* self) {
  THREAD_TYPE current_thread = THREAD_ID;
  if (self->owner != 0 && current_thread == self->owner) {
    PyErr_SetString(PyExc_RuntimeError, "Locking from owner would deadlock.");
    return NULL;
  }
  int result = 0;

  Py_BEGIN_ALLOW_THREADS;
  MUTEX_LOCK(self->mutex);

  /* We are locked here so safe. If we have waiters and the previous thread is
     the current thread we do not take the lock but instead we wait if the lock
     is unlocked. This hands over the lock to one of the other waiters. */
  while (self->locked ||
         (self->waiters && self->previous_owner == current_thread)) {
    self->previous_owner = 0;
    self->waiters++;
    result = COND_WAIT(self->cond, self->mutex);
    self->waiters--;
    if (result != 0) {
      MUTEX_UNLOCK(self->mutex);
      Py_BLOCK_THREADS;
      PyErr_Format(
          PyExc_RuntimeError, "IntervalLock wait failed with error %d", result);
      return NULL; /* Interrupted, return. */
    }
  }

  _Py_atomic_store_int32_relaxed(&self->locked, 1);
  self->owner = current_thread;
  self->lock_acquire_time = us_time();

  MUTEX_UNLOCK(self->mutex);
  Py_END_ALLOW_THREADS;
  Py_RETURN_NONE;
}

static PyObject* IntervalLock_unlock(IntervalLock* self) {
  MUTEX_LOCK(self->mutex);
  THREAD_TYPE current_thread = THREAD_ID;
  if (current_thread != self->owner) {
    PyErr_SetString(
        PyExc_RuntimeError,
        "Lock cannot be released from a thread which does not own it.");
    MUTEX_UNLOCK(self->mutex);
    return NULL;
  }

  if (self->locked) {
    _Py_atomic_store_int32_relaxed(&self->locked, 0);
    self->owner = 0;
    self->previous_owner = current_thread;
    COND_SIGNAL(self->cond);
  }

  MUTEX_UNLOCK(self->mutex);

  Py_RETURN_NONE;
}

static PyObject* IntervalLock_cede(IntervalLock* self) {
  PyObject* result = IntervalLock_unlock(self);
  if (result == NULL) {
    return NULL;
  }
  Py_DECREF(result);
  return IntervalLock_lock(self);
}

static PyObject* IntervalLock_poll(IntervalLock* self) {
  int64_t elapsed_time = us_difftime(us_time(), self->lock_acquire_time);
  /* Some form of clock reset event could make elapsed < 0 it which case we
     cede anyway as holding might be more dangerous than cedeing early. */
  if (elapsed_time > (int64_t)self->interval || elapsed_time < 0) {
    return IntervalLock_cede(self);
  }
  Py_RETURN_NONE;
}

static PyObject* IntervalLock_enter(IntervalLock* self) {
  PyObject* result = IntervalLock_lock(self);
  if (!result) {
    return NULL;
  }
  Py_DECREF(result);
  Py_INCREF(self);
  return (PyObject*)self;
}

static PyObject* IntervalLock_exit(IntervalLock* self, PyObject* args) {
  PyObject* result = IntervalLock_unlock(self);
  if (!result) {
    return NULL;
  }
  Py_DECREF(result);
  Py_RETURN_NONE;
}

static PyObject* IntervalLock_locked(IntervalLock* self) {
  if (_Py_atomic_load_int32_relaxed(&self->locked) == 0) {
    Py_RETURN_FALSE;
  } else {
    Py_RETURN_TRUE;
  }
}

static void IntervalLock_dealloc(IntervalLock* self) {
  if (MUTEX_DESTROY(self->mutex) || COND_DESTROY(self->cond)) {
    Py_FatalError("Failed to destroy locking primitive.");
  }
  Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyMethodDef IntervalLock_methods[] = {
    {"lock", (PyCFunction)IntervalLock_lock, METH_NOARGS, "Acquire the lock."},
    {"unlock",
     (PyCFunction)IntervalLock_unlock,
     METH_NOARGS,
     "Release the lock."},
    {"poll",
     (PyCFunction)IntervalLock_poll,
     METH_NOARGS,
     "Call cede() if the interval has expired."},
    {"cede",
     (PyCFunction)IntervalLock_poll,
     METH_NOARGS,
     "Cede the lock to any waiters and resets interval."},
    {"locked",
     (PyCFunction)IntervalLock_locked,
     METH_NOARGS,
     "Return the lock is locked or not."},
    {"__enter__",
     (PyCFunction)IntervalLock_enter,
     METH_NOARGS,
     "Enter the runtime context (lock)."},
    {"__exit__",
     (PyCFunction)IntervalLock_exit,
     METH_VARARGS,
     "Exit the runtime context (unlock)."},
    {NULL} /* Sentinel */
};

static PyTypeObject IntervalLockType = {
    PyVarObject_HEAD_INIT(NULL, 0).tp_name = "IntervalLock",
    .tp_doc =
        "IntervalLock(interval: float = 0.005): Creates an IntervalLock with the given interval in seconds.",
    .tp_basicsize = sizeof(IntervalLock),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_new = IntervalLock_new,
    .tp_init = (initproc)IntervalLock_init,
    .tp_dealloc = (destructor)IntervalLock_dealloc,
    .tp_methods = IntervalLock_methods,
};

/* ****************
   End IntervalLock
*/

/* Begin RWLock
 ****************
 */

typedef struct {
  PyObject_HEAD MUTEX_TYPE rw_lock;
  COND_TYPE rw_condition;
  int32_t writers_waiting;
  int32_t writer_locked;
  int32_t readers;
} ReaderWriterLock;

static PyObject*
ReaderWriterLock_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
  ReaderWriterLock* self = (ReaderWriterLock*)type->tp_alloc(type, 0);
  if (self == NULL) {
    return NULL;
  }

  self->readers = 0;
  self->writers_waiting = 0;
  self->writer_locked = 0;

  if (MUTEX_INIT(self->rw_lock) || COND_INIT(self->rw_condition)) {
    PyErr_SetString(PyExc_RuntimeError, "Failed to initialize locks.");
    Py_DECREF(self);
    return NULL;
  }

  return (PyObject*)self;
}

static void ReaderWriterLock_dealloc(ReaderWriterLock* self) {
  MUTEX_DESTROY(self->rw_lock);
  COND_DESTROY(self->rw_condition);
  Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject* ReaderWriterLock_lock_read(ReaderWriterLock* self) {
  Py_BEGIN_ALLOW_THREADS;
  MUTEX_LOCK(self->rw_lock);
  while (self->writers_waiting || self->writer_locked) {
    int result;
    if ((result = COND_WAIT(self->rw_condition, self->rw_lock))) {
      MUTEX_UNLOCK(self->rw_lock);
      Py_BLOCK_THREADS;
      PyErr_Format(
          PyExc_RuntimeError, "IntervalLock wait failed with error %d", result);
      return NULL;
    }
  }
  /* Atomic for observer threads - see other atomics also. */
  _Py_atomic_add_int32(&self->readers, 1);
  MUTEX_UNLOCK(self->rw_lock);
  Py_END_ALLOW_THREADS;
  Py_RETURN_NONE;
}

static PyObject* ReaderWriterLock_unlock_read(ReaderWriterLock* self) {
  Py_BEGIN_ALLOW_THREADS;
  MUTEX_LOCK(self->rw_lock);
  atomic_int32_sub(&self->readers, 1);
  COND_BROADCAST(self->rw_condition);
  MUTEX_UNLOCK(self->rw_lock);
  Py_END_ALLOW_THREADS;
  Py_RETURN_NONE;
}

static PyObject* ReaderWriterLock_lock_write(ReaderWriterLock* self) {
  Py_BEGIN_ALLOW_THREADS;
  MUTEX_LOCK(self->rw_lock);
  _Py_atomic_add_int32(&self->writers_waiting, 1);
  while (self->readers > 0 || self->writer_locked) {
    int result;
    if ((result = COND_WAIT(self->rw_condition, self->rw_lock))) {
      MUTEX_UNLOCK(self->rw_lock);
      Py_BLOCK_THREADS;
      PyErr_Format(
          PyExc_RuntimeError, "IntervalLock wait failed with error %d", result);
      return NULL;
    }
  }

  atomic_int32_sub(&self->writers_waiting, 1);
  _Py_atomic_store_int32_relaxed(&self->writer_locked, 1);
  MUTEX_UNLOCK(self->rw_lock);
  Py_END_ALLOW_THREADS;
  Py_RETURN_NONE;
}

static PyObject* ReaderWriterLock_unlock_write(ReaderWriterLock* self) {
  Py_BEGIN_ALLOW_THREADS;
  MUTEX_LOCK(self->rw_lock);
  _Py_atomic_store_int32_relaxed(&self->writer_locked, 0);
  COND_BROADCAST(self->rw_condition);
  MUTEX_UNLOCK(self->rw_lock);
  Py_END_ALLOW_THREADS;
  Py_RETURN_NONE;
}

static PyObject* ReaderWriterLock_readers(ReaderWriterLock* self) {
  return PyLong_FromLong(_Py_atomic_load_int32_relaxed(&self->readers));
}

static PyObject* ReaderWriterLock_writers_waiting(ReaderWriterLock* self) {
  return PyLong_FromLong(_Py_atomic_load_int32_relaxed(&self->writers_waiting));
}

static PyObject* ReaderWriterLock_writer_locked(ReaderWriterLock* self) {
  if (_Py_atomic_load_int32_relaxed(&self->writer_locked) == 0) {
    Py_RETURN_FALSE;
  } else {
    Py_RETURN_TRUE;
  }
}

typedef struct {
  PyObject_HEAD ReaderWriterLock* rwlock;
} RWReadContext;

static PyTypeObject ReaderWriterLockType;
static int
RWReadContext_init(RWReadContext* self, PyObject* args, PyObject* kwds) {
  PyObject* lock;
  if (!PyArg_ParseTuple(args, "O!", &ReaderWriterLockType, &lock)) {
    return -1;
  }
  Py_INCREF(lock);
  self->rwlock = (ReaderWriterLock*)lock;
  return 0;
}

static PyObject* RWReadContext_enter(RWReadContext* self) {
  return ReaderWriterLock_lock_read(self->rwlock);
}

static PyObject* RWReadContext_exit(
    RWReadContext* self,
    PyObject* exc_type,
    PyObject* exc_value,
    PyObject* traceback) {
  return ReaderWriterLock_unlock_read(self->rwlock);
}

static void RWReadContext_dealloc(RWReadContext* self) {
  Py_XDECREF(self->rwlock);
  Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyMethodDef RWReadContext_methods[] = {
    {"__enter__",
     (PyCFunction)RWReadContext_enter,
     METH_NOARGS,
     "Enter the read lock context"},
    {"__exit__",
     (PyCFunction)RWReadContext_exit,
     METH_VARARGS,
     "Exit the read lock context"},
    {NULL}};

static PyTypeObject RWReadContextType = {
    PyVarObject_HEAD_INIT(NULL, 0).tp_name = "synchronisation.RWReadContext",
    .tp_doc = "Read context for Reader-Writer Lock",
    .tp_basicsize = sizeof(RWReadContext),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_new = PyType_GenericNew,
    .tp_init = (initproc)RWReadContext_init,
    .tp_dealloc = (destructor)RWReadContext_dealloc,
    .tp_methods = RWReadContext_methods,
};

typedef struct {
  PyObject_HEAD ReaderWriterLock* rwlock;
} RWWriteContext;

static int
RWWriteContext_init(RWWriteContext* self, PyObject* args, PyObject* kwds) {
  PyObject* lock;
  if (!PyArg_ParseTuple(args, "O!", &ReaderWriterLockType, &lock)) {
    return -1;
  }
  Py_INCREF(lock);
  self->rwlock = (ReaderWriterLock*)lock;
  return 0;
}

static PyObject* RWWriteContext_enter(RWWriteContext* self) {
  return ReaderWriterLock_lock_write(self->rwlock);
}

static PyObject* RWWriteContext_exit(
    RWWriteContext* self,
    PyObject* exc_type,
    PyObject* exc_value,
    PyObject* traceback) {
  return ReaderWriterLock_unlock_write(self->rwlock);
}

static void RWWriteContext_dealloc(RWWriteContext* self) {
  Py_XDECREF(self->rwlock);
  Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyMethodDef RWWriteContext_methods[] = {
    {"__enter__",
     (PyCFunction)RWWriteContext_enter,
     METH_NOARGS,
     "Enter the write lock context"},
    {"__exit__",
     (PyCFunction)RWWriteContext_exit,
     METH_VARARGS,
     "Exit the write lock context"},
    {NULL}};

static PyTypeObject RWWriteContextType = {
    PyVarObject_HEAD_INIT(NULL, 0).tp_name = "synchronisation.RWWriteContext",
    .tp_doc = "Write context for Reader-Writer Lock",
    .tp_basicsize = sizeof(RWWriteContext),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_new = PyType_GenericNew,
    .tp_init = (initproc)RWWriteContext_init,
    .tp_dealloc = (destructor)RWWriteContext_dealloc,
    .tp_methods = RWWriteContext_methods,
};

static PyMethodDef ReaderWriterLock_methods[] = {
    {"lock_read",
     (PyCFunction)ReaderWriterLock_lock_read,
     METH_NOARGS,
     "Acquire read lock"},
    {"unlock_read",
     (PyCFunction)ReaderWriterLock_unlock_read,
     METH_NOARGS,
     "Release read lock"},
    {"lock_write",
     (PyCFunction)ReaderWriterLock_lock_write,
     METH_NOARGS,
     "Acquire write lock"},
    {"unlock_write",
     (PyCFunction)ReaderWriterLock_unlock_write,
     METH_NOARGS,
     "Release write lock"},
    {"readers",
     (PyCFunction)ReaderWriterLock_readers,
     METH_NOARGS,
     "How many readers hold the lock"},
    {"writers_waiting",
     (PyCFunction)ReaderWriterLock_writers_waiting,
     METH_NOARGS,
     "Is there a writer waiting to hold the lock?"},
    {"writer_locked",
     (PyCFunction)ReaderWriterLock_writer_locked,
     METH_NOARGS,
     "Is the writer lock held?"},
    {NULL} /* Sentinel */
};

static PyTypeObject ReaderWriterLockType = {
    PyVarObject_HEAD_INIT(NULL, 0).tp_name = "synchronisation.RWLock",
    .tp_doc = "Reader-Writer Lock",
    .tp_basicsize = sizeof(ReaderWriterLock),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_new = (newfunc)ReaderWriterLock_new,
    .tp_dealloc = (destructor)ReaderWriterLock_dealloc,
    .tp_methods = ReaderWriterLock_methods,
};

/* ****************
   End RWLock
*/

static int exec_local_module(PyObject* module) {
  if (PyType_Ready(&IntervalLockType) < 0) {
    return -1;
  }

  if (PyType_Ready(&ReaderWriterLockType) < 0) {
    return -1;
  }

  if (PyType_Ready(&RWReadContextType) < 0) {
    return -1;
  }

  if (PyType_Ready(&RWWriteContextType) < 0) {
    return -1;
  }

  if (PyModule_AddObjectRef(
          module, "IntervalLock", (PyObject*)&IntervalLockType) < 0) {
    return -1;
  }

  if (PyModule_AddObjectRef(
          module, "RWLock", (PyObject*)&ReaderWriterLockType) < 0) {
    return -1;
  }

  if (PyModule_AddObjectRef(
          module, "RWReadContext", (PyObject*)&RWReadContextType) < 0) {
    return -1;
  }

  if (PyModule_AddObjectRef(
          module, "RWWriteContext", (PyObject*)&RWWriteContextType) < 0) {
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
    "synchronization",
    "Synchronization utilies for FTPython.",
    0,
    NULL,
    module_slots,
    NULL,
    NULL,
    NULL};

PyMODINIT_FUNC PyInit_synchronization(void) {
  return PyModuleDef_Init(&local_module);
}
