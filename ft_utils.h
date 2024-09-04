/* Copyright (c) Meta Platforms, Inc. and affiliates. */

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stddef.h>

typedef uint64_t ustimestamp_t;

#if defined(_WIN32) || defined(_WIN64)
#include <windows.h>

/* This timing stuff needs moving out into its own compilation unit
   but for now we will leave it here because it makes setting up the
   wheel simpler. T198869932.
*/

// NOLINTNEXTLINE
static ustimestamp_t frequency;

// NOLINTNEXTLINE
static void initialize_frequency() {
  LARGE_INTEGER freq;
  QueryPerformanceFrequency(&freq);
  /* Convert frequency to microseconds. */
  frequency = (ustimestamp_t)freq.QuadPart / 1000000;
}

// NOLINTNEXTLINE
static ustimestamp_t us_time(void) {
  if (frequency == 0) {
    initialize_frequency();
  }
  LARGE_INTEGER counter;
  QueryPerformanceCounter(&counter);
  return (ustimestamp_t)((ustimestamp_t)counter.QuadPart / frequency);
}

typedef DWORD THREAD_TYPE;
typedef CRITICAL_SECTION MUTEX_TYPE;
typedef CONDITION_VARIABLE COND_TYPE;

#define THREAD_ID GetCurrentThreadId()
#define MUTEX_INIT(mutex) (InitializeCriticalSection(&mutex), 0)
#define MUTEX_DESTROY(mutex) (DeleteCriticalSection(&mutex), 0)
#define MUTEX_LOCK(mutex) (EnterCriticalSection(&mutex))
#define MUTEX_UNLOCK(mutex) (LeaveCriticalSection(&mutex))
#define COND_INIT(cond) (InitializeConditionVariable(&cond), 0)
#define COND_DESTROY(cond) (0)

// NOLINTNEXTLINE
static int cond_wait(COND_TYPE* cond, MUTEX_TYPE* mutex) {
  BOOL result = SleepConditionVariableCS(cond, mutex, INFINITE);
  return result ? 0 : 1;
}
#define COND_WAIT(cond, mutex) (cond_wait(&cond, &mutex))
#define COND_SIGNAL(cond) (WakeConditionVariable(&cond))
#define COND_BROADCAST(cond) (WakeAllConditionVariable(&cond))

#else
#include <pthread.h>
#include <time.h>

// NOLINTNEXTLINE
static ustimestamp_t us_time(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (ustimestamp_t)ts.tv_sec * 1000000 + ts.tv_nsec / 1000;
}

#define THREAD_TYPE pthread_t
#define THREAD_ID pthread_self()
#define MUTEX_TYPE pthread_mutex_t
#define COND_TYPE pthread_cond_t
#define MUTEX_INIT(mutex) (pthread_mutex_init(&mutex, NULL) != 0)
#define MUTEX_DESTROY(mutex) (pthread_mutex_destroy(&mutex) != 0)
#define MUTEX_LOCK(mutex) (pthread_mutex_lock(&mutex))
#define MUTEX_UNLOCK(mutex) (pthread_mutex_unlock(&mutex))
#define COND_INIT(cond) (pthread_cond_init(&cond, NULL) != 0)
#define COND_DESTROY(cond) (pthread_cond_destroy(&cond) != 0)
#define COND_WAIT(cond, mutex) (pthread_cond_wait(&cond, &mutex))
#define COND_SIGNAL(cond) (pthread_cond_signal(&cond))
#define COND_BROADCAST(cond) (pthread_cond_broadcast(&cond))
#endif

// NOLINTNEXTLINE
static int64_t us_difftime(ustimestamp_t end, ustimestamp_t start) {
  return end - start;
}

/* Allow this to compile on older versions of Python: */
#ifndef Py_ATOMIC_H
#define Py_BEGIN_CRITICAL_SECTION(self) {
#define Py_END_CRITICAL_SECTION() }
static inline void* _Py_atomic_load_ptr(void* from) {
  void** from_ptr = (void**)from;
  return (void*)(*from_ptr);
}

static inline Py_ssize_t _Py_atomic_load_ssize(Py_ssize_t* from) {
  return *from;
}

// NOLINTNEXTLINE
static inline void _Py_atomic_store_ssize(Py_ssize_t* to, Py_ssize_t from) {
  *to = from;
}

static inline Py_ssize_t _Py_atomic_add_ssize(
    Py_ssize_t* from,
    Py_ssize_t to_add) {
  Py_ssize_t ret = *from;
  *from += to_add;
  return ret;
}

static inline void _Py_atomic_fence_release(void) {
  /* noop; */
}

static inline void _Py_atomic_fence_seq_cst(void) {
  /* noop; */
}

static inline int64_t _Py_atomic_load_int64(int64_t* value) {
  return *value;
}

static inline void _Py_atomic_store_int64(int64_t* to, int64_t from) {
  *to = from;
}

// NOLINTNEXTLINE
static inline int64_t _Py_atomic_add_int64(int64_t* to, int64_t from) {
  int64_t old = *to;
  *to += from;
  return old;
}

static inline int _Py_atomic_compare_exchange_int64(
    int64_t* obj,
    int64_t* expected,
    int64_t desired) {
  if (*expected == *obj) {
    *obj = desired;
    return 1;
  } else {
    return 0;
  }
}

// NOLINTNEXTLINE
static inline int64_t _Py_atomic_load_int32_relaxed(int32_t* value) {
  return *value;
}

// NOLINTNEXTLINE
static inline void _Py_atomic_store_int32_relaxed(int32_t* to, int32_t from) {
  *to = from;
}

// NOLINTNEXTLINE
static inline int32_t _Py_atomic_add_int32(int32_t* to, int32_t from) {
  int32_t old = *to;
  *to += from;
  return old;
}

// NOLINTNEXTLINE
static inline void* _Py_atomic_exchange_ptr(void* to, void* from) {
  void** ref = (void**)to;
  void* old = *ref;
  *ref = from;
  return old;
}

static inline int
_Py_atomic_compare_exchange_ptr(void* obj, void* expected, void* desired) {
  void** vobj = (void**)obj;
  void** vexpected = (void**)expected;
  if (*vexpected == *vobj) {
    *vobj = desired;
    return 1;
  } else {
    return 0;
  }
}

#endif

// NOLINTNEXTLINE
static inline int64_t atomic_int64_sub(int64_t* obj, int64_t value) {
  return _Py_atomic_add_int64(obj, -value);
}

// NOLINTNEXTLINE
static inline int64_t atomic_int32_sub(int32_t* obj, int32_t value) {
  return _Py_atomic_add_int32(obj, -value);
}

/* Some of these can be done with single instructions on some compilers but we
   will stick with using the well tested optionf from pyatomic.g
*/
// NOLINTNEXTLINE
static inline int64_t atomic_int64_or(int64_t* obj, int64_t value) {
  int64_t expected, desired;
  do {
    expected = *obj;
    desired = expected | value;
  } while (!_Py_atomic_compare_exchange_int64(obj, &expected, desired));
  return expected;
}

// NOLINTNEXTLINE
static inline int64_t atomic_int64_xor(int64_t* obj, int64_t value) {
  int64_t expected, desired;
  do {
    expected = *obj;
    desired = expected ^ value;
  } while (!_Py_atomic_compare_exchange_int64(obj, &expected, desired));
  return expected;
}

// NOLINTNEXTLINE
static inline int64_t atomic_int64_and(int64_t* obj, int64_t value) {
  int64_t expected, desired;
  do {
    expected = *obj;
    desired = expected & value;
  } while (!_Py_atomic_compare_exchange_int64(obj, &expected, desired));
  return expected;
}

// NOLINTNEXTLINE
static inline int64_t atomic_int64_mul(int64_t* obj, int64_t value) {
  int64_t expected, desired;
  do {
    expected = *obj;
    desired = expected * value;
  } while (!_Py_atomic_compare_exchange_int64(obj, &expected, desired));
  return expected;
}

// NOLINTNEXTLINE
static inline int64_t atomic_int64_div(int64_t* obj, int64_t value) {
  int64_t expected, desired;
  if (value == 0) {
    abort();
  }
  do {
    expected = *obj;
    desired = expected / value;
  } while (!_Py_atomic_compare_exchange_int64(obj, &expected, desired));
  return expected;
}

/* The concurrent API is exposes some internals of the Free Threaded Python
 * runtime to none code code. Whilst it is C linked, not inlined, the advantage
 * is this API shields users from the implementation details and allows code
 * which is not compiled as Py_BUILD_CORE to still use some of the key features
 * of the Free Threaded Runtime from native code.
 */

/* Registers an object so it can take part in the concurrent API.
 * This must be done or the results of any other call in the API are
 * undefined.
 */
void ConcurrentRegisterReference(PyObject* obj);

/* Returns a new reference to the passed object reference.
 * This is an concurrent safe implementaion of loading the reference from a
 * pointer then incrementing the reference count. We pass in an pointer to the
 * object pointer so the call can cope with the value pointed to changing under
 * race conditions.
 */
PyObject* ConcurrentGetNewReference(PyObject** obj_ptr);

/* The same as ConcurrentGetNewReference but will allow dereferencing in a NULL
 * pointer. It is better to not default to this - use only if you believe there
 * is a good case for not trapping nulls.
 */
PyObject* ConcurrentXGetNewReference(PyObject** obj_ptr);

/* Even lower than ConcurrentGetNewReference this attempts to increment the ref
 * count of the obejct pointed to by obj_ptr if and only if expected is what is
 * found in *obj_ptr at the time of increment. This is optimized for scenarios
 * where concurrency checks are not required or for other cases (like imortal
 * objects).
 */
int ConcurrentTryIncReference(PyObject** obj_ptr, PyObject* expected);
