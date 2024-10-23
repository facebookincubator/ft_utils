/* Copyright (c) Meta Platforms, Inc. and affiliates. */

#ifndef FT_REFCOUNT_H
#define FT_REFCOUNT_H

#include <Python.h>

/**
 * Registers an object so it can take part in the concurrent API.
 * This must be done or the results of any other call in the API are
 * undefined.
 */
void ConcurrentRegisterReference(PyObject* obj);

/**
 * Returns a new reference to the passed object reference.
 * This is an concurrent safe implementaion of loading the reference from a
 * pointer then incrementing the reference count. We pass in an pointer to the
 * object pointer so the call can cope with the value pointed to changing under
 * race conditions.
 */
PyObject* ConcurrentGetNewReference(PyObject** obj_ptr);

/**
 * The same as ConcurrentGetNewReference but will allow dereferencing in a NULL
 * pointer. It is better to not default to this - use only if you believe there
 * is a good case for not trapping nulls.
 */
PyObject* ConcurrentXGetNewReference(PyObject** obj_ptr);

/**
 * Even lower than ConcurrentGetNewReference this attempts to increment the ref
 * count of the obejct pointed to by obj_ptr if and only if expected is what is
 * found in *obj_ptr at the time of increment. This is optimized for scenarios
 * where concurrency checks are not required or for other cases (like imortal
 * objects).
 */
int ConcurrentTryIncReference(PyObject** obj_ptr, PyObject* expected);

#endif /* FT_REFCOUNT_H */
