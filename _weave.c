/* Copyright (c) Meta Platforms, Inc. and affiliates. */
#include <Python.h>
#include "ft_weave.h"

/* Thead local storge definition.
   ==============================
*/

#ifdef _WIN32

int wvls_key_create(wvls_key_t* key, wvls_destructor_t destructor) {
  if (!key) {
    return ERROR_INVALID_PARAMETER;
  }

  if (destructor) {
    *key = FlsAlloc((PFLS_CALLBACK_FUNCTION)destructor);
    if (*key == FLS_OUT_OF_INDEXES) {
      return GetLastError();
    }
  } else {
    *key = TlsAlloc();
    if (*key == TLS_OUT_OF_INDEXES) {
      return GetLastError();
    }
  }

  return 0;
}

int wvls_key_delete(wvls_key_t key) {
  if (!key) {
    return ERROR_INVALID_PARAMETER;
  }

  if (!FlsFree(key) && !TlsFree(key)) {
    return GetLastError();
  }

  return 0;
}

int wvls_set_value(wvls_key_t key, void* value) {
  if (!key) {
    return ERROR_INVALID_PARAMETER;
  }

  /* If TlsGetValue returns NULL, it may be because the thread existed before
     the DLL was loaded (e.g., main thread or threads created by other
     libraries). In this case, we need to allocate memory for the TLS value and
     set it. */
  LPVOID lpvData = TlsGetValue(key);
  if (lpvData == NULL && GetLastError() != ERROR_SUCCESS) {
    lpvData = LocalAlloc(LPTR, 256);
    if (lpvData == NULL) {
      return ERROR_NOT_ENOUGH_MEMORY;
    }
    if (!TlsSetValue(key, lpvData)) {
      LocalFree(lpvData);
      return GetLastError();
    }
  }

  *(LPVOID*)lpvData = value;

  return 0;
}

void* wvls_get_value(wvls_key_t key) {
  if (!key) {
    return NULL;
  }

  void* value = FlsGetValue(key);
  if (value == NULL && GetLastError() != ERROR_SUCCESS) {
    value = TlsGetValue(key);
  }

  return value;
}

#else /* POSIX */

int wvls_key_create(wvls_key_t* key, wvls_destructor_t destructor) {
  if (!key) {
    return EINVAL;
  }

  return pthread_key_create(key, destructor);
}

int wvls_key_delete(wvls_key_t key) {
  if (!key) {
    return EINVAL;
  }

  return pthread_key_delete(key);
}

int wvls_set_value(wvls_key_t key, void* value) {
  if (!key) {
    return EINVAL;
  }

  return pthread_setspecific(key, value);
}

void* wvls_get_value(wvls_key_t key) {
  if (!key) {
    return NULL;
  }

  return pthread_getspecific(key);
}
#endif

typedef struct wvls_destructor_node {
  void** wvls_variable_ptr;
  wvls_destructor_t destructor;
  struct wvls_destructor_node* next;
} wvls_destructor_node_t;

static wvls_key_t wvls_destructors_key;

void wvls_destructors_invoke(void* arg) {
  wvls_destructor_node_t* node = (wvls_destructor_node_t*)arg;

  /* Reverse the linked list to ensure destructor calling order matched
     destrutor registration order. */
  wvls_destructor_node_t* previous = NULL;
  while (node) {
    wvls_destructor_node_t* next_node = node->next;
    node->next = previous;
    previous = node;
    node = next_node;
  }
  node = previous;
  while (node) {
    if (node->destructor && node->wvls_variable_ptr) {
      node->destructor(*(node->wvls_variable_ptr));
    }
    wvls_destructor_node_t* temp = node;
    node = node->next;
    free(temp);
  }
}

static void init_wvls_destructor_key() {
  if (wvls_key_create(&wvls_destructors_key, wvls_destructors_invoke) != 0) {
    fprintf(stderr, "Failed to create TLS key.\n");
    abort();
  }
  /* Probably not necessary but let's be careful. */
  if (wvls_set_value(wvls_destructors_key, NULL)) {
    fprintf(stderr, "Failed to set TLS value.\n");
    abort();
  }
}

void register_wvls_destructor(
    void** wvls_variable_ptr,
    wvls_destructor_t destructor) {
  wvls_destructor_node_t* head =
      (wvls_destructor_node_t*)wvls_get_value(wvls_destructors_key);

  wvls_destructor_node_t* node =
      (wvls_destructor_node_t*)malloc(sizeof(wvls_destructor_node_t));
  if (!node) {
    fprintf(stderr, "Failed to allocate destructor node.\n");
    abort();
  }

  node->wvls_variable_ptr = wvls_variable_ptr;
  node->destructor = destructor;
  node->next = head;

  if (wvls_set_value(wvls_destructors_key, node) != 0) {
    fprintf(stderr, "Failed to set TLS value during insert.\n");
    abort();
  }
}

int unregister_wvls_destructor(void** wvls_variable_ptr) {
  wvls_destructor_node_t* node =
      (wvls_destructor_node_t*)wvls_get_value(wvls_destructors_key);
  wvls_destructor_node_t* previous = NULL;
  int found = 0;
  while (node != NULL) {
    if (node->wvls_variable_ptr == wvls_variable_ptr) {
      if (previous == NULL) {
        if (wvls_set_value(wvls_destructors_key, node->next) != 0) {
          fprintf(stderr, "Failed to set TLS value during delete.\n");
          abort();
        }
      } else {
        previous->next = node->next;
      }
      found = 1;
      wvls_destructor_node_t* temp = node;
      node = node->next;
      free(temp);
    } else {
      previous = node;
      node = node->next;
    }
  }
  return found;
}

/* Python Module definition.
   =========================
*/

/* The extension function */
static PyObject* wvlspy_register_destructor(PyObject* self, PyObject* args) {
  PyObject* wvls_var = NULL;
  PyObject* wvls_destructor = NULL;

  /* Parse the arguments */
  if (!PyArg_ParseTuple(args, "OO", &wvls_var, &wvls_destructor)) {
    return NULL;
  }

  void* var_ptr = PyLong_AsVoidPtr(wvls_var);
  if (var_ptr == NULL && PyErr_Occurred()) {
    return NULL;
  }

  void* destruct_ptr = PyLong_AsVoidPtr(wvls_destructor);
  if (destruct_ptr == NULL && PyErr_Occurred()) {
    return NULL;
  }

  register_wvls_destructor(var_ptr, (wvls_destructor_t)destruct_ptr);

  Py_RETURN_NONE;
}

static PyObject* wvlspy_unregister_destructor(PyObject* self, PyObject* args) {
  PyObject* wvls_var = NULL;

  /* Parse the arguments */
  if (!PyArg_ParseTuple(args, "O", &wvls_var)) {
    return NULL;
  }

  void* var_ptr = PyLong_AsVoidPtr(wvls_var);
  if (var_ptr == NULL && PyErr_Occurred()) {
    return NULL;
  }

  return PyBool_FromLong((long)unregister_wvls_destructor(var_ptr));
}

static int exec_weave_module(PyObject* module) {
  init_wvls_destructor_key();
  return 0; /* Return 0 on success */
}

static struct PyModuleDef_Slot weave_module_slots[] = {
    {Py_mod_exec, exec_weave_module},
#if PY_VERSION_HEX >= 0x030D0000
    {Py_mod_gil, Py_MOD_GIL_NOT_USED},
#endif
    {0, NULL} /* sentinel */
};

static PyMethodDef weave_module_methods[] = {
    {"register_native_destructor",
     wvlspy_register_destructor,
     METH_VARARGS,
     PyDoc_STR(
         "Register a native C ABI destructor for native thread local storage.")},
    {"unregister_native_destructor",
     wvlspy_unregister_destructor,
     METH_VARARGS,
     PyDoc_STR(
         "Unregister any destructors for the storage pointed to by the argument, returning true if any were removed.")},
    {NULL, NULL, 0, NULL}};

static PyModuleDef weave_module = {
    PyModuleDef_HEAD_INIT,
    "_weave",
    PyDoc_STR(
        "The native part of weave for managing thread based functionality."),
    0,
    weave_module_methods,
    weave_module_slots,
    NULL,
    NULL,
    NULL};

PyMODINIT_FUNC PyInit__weave(void) {
  return PyModuleDef_Init(&weave_module);
}
