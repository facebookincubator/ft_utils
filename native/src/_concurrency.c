/* Copyright (c) Meta Platforms, Inc. and affiliates. */

#include "ft_utils.h"

#include "concurrent_data_structures/atomic_int64.h"
#include "concurrent_data_structures/atomic_reference.h"
#include "concurrent_data_structures/concurrent_deque.h"
#include "concurrent_data_structures/concurrent_dict.h"

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

static PyModuleDef concurrency_module = {
    PyModuleDef_HEAD_INIT,
    "_concurrency",
    "Concurrently scalable data structures and patterns.",
    0,
    NULL,
    module_slots,
    NULL,
    NULL,
    NULL};

PyMODINIT_FUNC PyInit__concurrency(void) {
  return PyModuleDef_Init(&concurrency_module);
}
