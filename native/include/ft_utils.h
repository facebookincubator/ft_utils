/* Copyright (c) Meta Platforms, Inc. and affiliates. */

#ifndef FT_UTILS_H
#define FT_UTILS_H

#include "ft_compat.h" // @manual
#include "ft_refcount.h" // @manual
#include "ft_utime.h" // @manual

#if defined(_WIN32) || defined(_WIN64)

#include <windows.h>

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
static inline int64_t atomic_int64_sub(int64_t* obj, int64_t value) {
  return _Py_atomic_add_int64(obj, -value);
}

// NOLINTNEXTLINE
static inline int64_t atomic_int32_sub(int32_t* obj, int32_t value) {
  return _Py_atomic_add_int32(obj, -value);
}

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

#endif /* FT_UTILS_H */
