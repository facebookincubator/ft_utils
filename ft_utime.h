/* Copyright (c) Meta Platforms, Inc. and affiliates. */

#ifndef FT_UTIME_H
#define FT_UTIME_H

#include <stddef.h>

typedef uint64_t ustimestamp_t;

#if defined(_WIN32) || defined(_WIN64)

#include <windows.h>

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

#else

#include <pthread.h>
#include <time.h>

// NOLINTNEXTLINE
static ustimestamp_t us_time(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (ustimestamp_t)ts.tv_sec * 1000000 + ts.tv_nsec / 1000;
}

#endif

// NOLINTNEXTLINE
static int64_t us_difftime(ustimestamp_t end, ustimestamp_t start) {
  return end - start;
}

#endif /* FT_UTIME_H */
