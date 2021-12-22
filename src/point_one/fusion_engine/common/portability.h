/**************************************************************************/ /**
 * @brief Library portability helper definitions.
 * @file
 ******************************************************************************/

#pragma once

#include <cstdint>

// References:
// - https://gcc.gnu.org/wiki/Visibility.
// - https://github.com/protocolbuffers/protobuf/blob/master/src/google/protobuf/port_def.inc
#if defined(_WIN32) || defined(_MSC_VER) || defined(__CYGWIN__)
  #ifdef BUILDING_DLL
    #ifdef __GNUC__
      #define P1_EXPORT __attribute__ ((dllexport))
    #else
      #define P1_EXPORT __declspec(dllexport)
    #endif
  #else
    #ifdef __GNUC__
      #define P1_EXPORT __attribute__ ((dllimport))
    #else
      #define P1_EXPORT __declspec(dllimport)
    #endif
  #endif
  #define P1_HIDDEN
#else
  #if __GNUC__ >= 4
    #define P1_EXPORT __attribute__ ((visibility ("default")))
    #define P1_HIDDEN  __attribute__ ((visibility ("hidden")))
  #else
    #define P1_EXPORT
    #define P1_HIDDEN
  #endif
#endif

// ssize_t is a POSIX extension and is not supported on Windows.
#if defined(_WIN32)
typedef int32_t p1_ssize_t;
#elif defined(_MSC_VER)
typedef int64_t p1_ssize_t;
#else
#include <sys/types.h> // For ssize_t
typedef ssize_t p1_ssize_t;
#endif
