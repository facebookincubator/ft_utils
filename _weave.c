/* Copyright (c) Meta Platforms, Inc. and affiliates. */
#include <Python.h>
#include "ft_compat.h"
#include "ft_weave.h"

/* Thead local storge definition.
   ==============================
*/

#ifdef _WIN32

/* When dynamic TLS keys are created through wvls_key_create, we keep track of
 * them in this linked list. On thread detach, we optionally call the callback
 * associated with the key, then set the value to NULL. On process detach, we
 * free the key and clear the linked list.
 */
typedef struct wvls_dynamic_key {
  struct wvls_dynamic_key* next;
  wvls_key_t key;
  wvls_destructor_t destructor;
} wvls_dynamic_key_t;

/* This is a process-level linked-list that keeps track of the allocated TLS
 * keys. On process detach, it will be walked to free all of the keys
 */
static wvls_dynamic_key_t* wvls_dynamic_keys = NULL;

/* The DllMain entrypoint allows us to hook into the dll process to get notified
 * when threads or processes are detached. Note that this works because the
 * ft_utils native extension is loaded as a dynamic library.
 *
 * If, in the future, a situation arises where we need to load the native
 * extension as a static library, there is some prior art we can copy from
 * mimalloc that is the new suggested way to hook into these kinds of
 * notifications here:
 *
 *   https://github.com/microsoft/mimalloc/blob/14b4f674fa2cff00f28333365fe07ce916575c30/src/prim/windows/prim.c#L658
 */
__declspec(dllexport) BOOL WINAPI
DllMain(HINSTANCE hinst_dll, DWORD fdw_reason, LPVOID lp_reserved) {
  /* If we have not been initialized yet, we do not need to worry about
   * notifications coming from DllMain. */
  if (!wvls_dynamic_keys) {
    return TRUE;
  }

  switch (fdw_reason) {
    case DLL_THREAD_DETACH: {
      /* On thread detach, we want to visit each TLS key and call its callback
       * if one has been registered and a value is associated with it. Then we
       * want to set the value to NULL. Note that we do _not_ want to free the
       * key here, since this needs to run on every thread being detached.
       */
      wvls_dynamic_key_t* dynamic_key = wvls_dynamic_keys;

      while (dynamic_key) {
        void* value = TlsGetValue(dynamic_key->key);
        if (value) {
          if (dynamic_key->destructor) {
            dynamic_key->destructor(value);
          }
          TlsSetValue(dynamic_key->key, NULL);
        }

        dynamic_key = dynamic_key->next;
      }

      break;
    }
    case DLL_PROCESS_DETACH: {
      /* On process detach, we want to visit each TLS key and return it, then
       * we want to clear our own bookkeeping.
       */
      wvls_dynamic_key_t* dynamic_key = wvls_dynamic_keys;

      while (dynamic_key) {
        wvls_dynamic_key_t* next = dynamic_key->next;
        TlsFree(dynamic_key->key);
        free(dynamic_key);
        dynamic_key = next;
      }

      wvls_dynamic_keys = NULL;
      break;
    }
  }

  return TRUE;
}

/* Create a weave key that will call the given destructor on thread exit. */
int wvls_key_create(wvls_key_t* key, wvls_destructor_t destructor) {
  if (!key) {
    return ERROR_INVALID_PARAMETER;
  }

  /* First, create the requested dynamic key. */
  *key = TlsAlloc();
  if (*key == TLS_OUT_OF_INDEXES) {
    return GetLastError();
  }

  /* Now keep track of the dynamic key. */
  wvls_dynamic_key_t* dynamic_key =
      (wvls_dynamic_key_t*)malloc(sizeof(wvls_dynamic_key_t));
  if (!dynamic_key) {
    TlsFree(*key);
    return ENOMEM;
  }

  dynamic_key->next = wvls_dynamic_keys;
  dynamic_key->key = *key;
  dynamic_key->destructor = destructor;
  wvls_dynamic_keys = dynamic_key;

  return 0;
}

/* Delete a weave key. Note that this will not call the callback associated with
 * the key if one was given on creation. */
int wvls_key_delete(wvls_key_t key) {
  if (!key || !wvls_dynamic_keys) {
    return ERROR_INVALID_PARAMETER;
  }

  /* Find the dynamic key in the list. */
  wvls_dynamic_key_t* previous = NULL;
  wvls_dynamic_key_t* current = wvls_dynamic_keys;

  while (current != NULL && current->key != key) {
    previous = current;
    current = current->next;
  }

  /* If we did not find the key, return an error. */
  if (!current) {
    return ERROR_INVALID_PARAMETER;
  }

  /* Remove the key from the list. */
  if (previous) {
    previous->next = current->next;
  } else {
    wvls_dynamic_keys = current->next;
  }

  /* Free the key. */
  free(current);
  if (!TlsFree(key)) {
    return GetLastError();
  }

  return 0;
}

/* Set the value associated with the given weave key. */
int wvls_set_value(wvls_key_t key, void* value) {
  if (!key) {
    return ERROR_INVALID_PARAMETER;
  }

  if (!TlsSetValue(key, value)) {
    return GetLastError();
  }

  return 0;
}

/* Get the value associated with the given weave key. */
void* wvls_get_value(wvls_key_t key) {
  if (!key) {
    return NULL;
  }

  return TlsGetValue(key);
}

#else /* POSIX */

/* Create a weave key that will call the given callback on thread exit. */
int wvls_key_create(wvls_key_t* key, wvls_destructor_t destructor) {
  if (!key) {
    return EINVAL;
  }

  return pthread_key_create(key, destructor);
}

/* Delete a weave key. Note that this will not call the callback associated with
 * the key if one was given on creation. */
int wvls_key_delete(wvls_key_t key) {
  if (!key) {
    return EINVAL;
  }

  return pthread_key_delete(key);
}

/* Set the value associated with the given weave key. */
int wvls_set_value(wvls_key_t key, void* value) {
  if (!key) {
    return EINVAL;
  }

  return pthread_setspecific(key, value);
}

/* Get the value associated with the given weave key. */
void* wvls_get_value(wvls_key_t key) {
  if (!key) {
    return NULL;
  }

  return pthread_getspecific(key);
}

#endif

static wvls_key_t wvls_destructors_key;

typedef struct wvls_destructor_node {
  void** wvls_variable_ptr;
  wvls_destructor_t destructor;
  struct wvls_destructor_node* next;
} wvls_destructor_node_t;

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
  int oops = wvls_key_create(&wvls_destructors_key, wvls_destructors_invoke);
  if (oops) {
    fprintf(stderr, "Failed to create TLS key: %i.\n", oops);
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
    _PY_NOGIL_MODULE_SLOT // NOLINT
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
