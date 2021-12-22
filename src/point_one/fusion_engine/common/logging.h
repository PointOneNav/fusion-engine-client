/**************************************************************************/ /**
 * @brief API wrapper for optional compilation of logging support.
 * @file
 *
 * To enable logging support, include
 * [Google glog](https://github.com/google/glog) in your project, and define
 * the following macro:
 * ```cpp
 * #define P1_HAVE_GLOG 1
 * ```
 *
 * This is typically done during compilation by specifying the
 * `-DP1_HAVE_GLOG=1` command-line argument to the compiler.
 ******************************************************************************/

#pragma once

// Use Google Logging Library (glog).
#if P1_HAVE_GLOG && !P1_NO_LOGGING
#  include <glog/logging.h>

// For internal use only.
#elif P1_HAVE_PORTABLE_LOGGING && !P1_NO_LOGGING
#  include "point_one/common/portability/logging.h"

// Disable logging support at compile time.
#else // Logging disabled

#  include <ostream>

#  if !P1_NO_LOGGING
#    undef P1_NO_LOGGING
#    define P1_NO_LOGGING 1
#  endif // !P1_NO_LOGGING

namespace point_one {
namespace fusion_engine {
namespace common {

class NullStream : public std::ostream {
 public:
  NullStream() : std::ostream(nullptr) {}
};

template <class T>
inline NullStream& operator<<(NullStream& stream, const T&) {
  return stream;
}

class NullMessage {
 public:
  static NullStream stream_;
  static NullMessage instance_;

  NullStream& stream() { return stream_; }
};

} // namespace common
} // namespace fusion_engine
} // namespace point_one

#  define P1_NULL_STREAM point_one::fusion_engine::common::NullMessage::stream_
#  define P1_NULL_MESSAGE \
    point_one::fusion_engine::common::NullMessage::instance_

#  define COMPACT_GOOGLE_LOG_INFO P1_NULL_MESSAGE
#  define COMPACT_GOOGLE_LOG_WARNING P1_NULL_MESSAGE
#  define COMPACT_GOOGLE_LOG_ERROR P1_NULL_MESSAGE
#  define COMPACT_GOOGLE_LOG_FATAL P1_NULL_MESSAGE

#  define LOG(severity) COMPACT_GOOGLE_LOG_##severity.stream()
#  define LOG_IF(severity, condition) COMPACT_GOOGLE_LOG_##severity.stream()
#  define LOG_EVERY_N(verboselevel, n) COMPACT_GOOGLE_LOG_##severity.stream()
#  define LOG_IF_EVERY_N(verboselevel, condition, n) \
    COMPACT_GOOGLE_LOG_##severity.stream()

#  define VLOG_IS_ON(verboselevel) false
#  define COMPACT_GOOGLE_VLOG(verboselevel) P1_NULL_MESSAGE

#  define VLOG_IF(verboselevel, condition) \
    COMPACT_GOOGLE_VLOG(verboselevel).stream()
#  define VLOG(verboselevel) COMPACT_GOOGLE_VLOG(verboselevel).stream()
#  define VLOG_EVERY_N(verboselevel, n) \
    COMPACT_GOOGLE_VLOG(verboselevel).stream()
#  define VLOG_IF_EVERY_N(verboselevel, condition, n) \
    COMPACT_GOOGLE_VLOG(verboselevel).stream()

#endif
