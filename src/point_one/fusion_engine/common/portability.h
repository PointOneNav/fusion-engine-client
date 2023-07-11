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
#  ifdef BUILDING_DLL
#    ifdef __GNUC__
#      define P1_EXPORT __attribute__((dllexport))
#    else
#      define P1_EXPORT __declspec(dllexport)
#    endif
#  else
#    ifdef __GNUC__
#      define P1_EXPORT __attribute__((dllimport))
#    else
#      define P1_EXPORT __declspec(dllimport)
#    endif
#  endif
#  define P1_HIDDEN
#else
#  if __GNUC__ >= 4
#    define P1_EXPORT __attribute__((visibility("default")))
#    define P1_HIDDEN __attribute__((visibility("hidden")))
#  else
#    define P1_EXPORT
#    define P1_HIDDEN
#  endif
#endif

// Support ARM CC quirks
#ifdef __CC_ARM
#  include "typedefs.h"
// ARM CC bug http://www.keil.com/forum/60227/
#  define __ESCAPE__(__x) (__x)
#  define P1_HAVE_STD_FUNCTION 0
#  define P1_HAVE_STD_OSTREAM 0
#  define P1_HAVE_STD_SMART_PTR 0
#  define P1_NO_LOGGING 1
#endif

// Different compilers support different ways of specifying default struct
// alignment. Since there's no universal method, a macro is used instead.
#ifdef __CC_ARM
#  define P1_ALIGNAS(N) __attribute__((aligned(N)))
#else
#  define P1_ALIGNAS(N) alignas(N)
#endif

// ssize_t is a POSIX extension and is not supported on Windows/ARM CC.
#if defined(_WIN32) || defined(__CC_ARM)
typedef int32_t p1_ssize_t;
#elif defined(_MSC_VER)
typedef int64_t p1_ssize_t;
#else
#  include <sys/types.h> // For ssize_t
typedef ssize_t p1_ssize_t;
#endif

#ifndef P1_HAVE_STD_OSTREAM
#  define P1_HAVE_STD_OSTREAM 1
#endif
#if P1_HAVE_STD_OSTREAM
#  include <ostream>
using p1_ostream = std::ostream;
#else
class p1_ostream {
 public:
  p1_ostream() = default;
};
template <class T>
inline p1_ostream& operator<<(p1_ostream& stream, const T&) {
  return stream;
}
#endif

#ifndef P1_HAVE_STD_FUNCTION
#  define P1_HAVE_STD_FUNCTION 1
#endif

#ifndef P1_HAVE_STD_SMART_PTR
#  define P1_HAVE_STD_SMART_PTR 1
#endif

// Support for multi-statement constexpr functions was not added until C++14.
// When compiling with C++11, we'll simply use inline instead.
#ifndef P1_HAVE_MULTILINE_CONSTEXPR_FUNC
#  define P1_HAVE_MULTILINE_CONSTEXPR_FUNC (__cplusplus >= 201402L)
#endif

#ifndef P1_CONSTEXPR_FUNC
#  if P1_HAVE_MULTILINE_CONSTEXPR_FUNC
#    define P1_CONSTEXPR_FUNC constexpr
#  else
#    define P1_CONSTEXPR_FUNC inline
#  endif
#endif
