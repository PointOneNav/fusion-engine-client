/**************************************************************************/ /**
 * @brief Point One FusionEngine timestamp support.
 * @file
 ******************************************************************************/

#pragma once

#include <cmath> // For NAN
#include <cstdint>

#include "point_one/fusion_engine/common/portability.h"

namespace point_one {
namespace fusion_engine {
namespace messages {

/**
 * @brief Generic timestamp representation.
 * @ingroup messages
 *
 * This structure may be used to store Point One system time values (referenced
 * to the start of the device), UNIX times (referenced to January 1, 1970), or
 * GPS times (referenced to January 6, 1980).
 */
struct P1_ALIGNAS(4) Timestamp {
  static constexpr uint32_t INVALID = 0xFFFFFFFF;

  /**
   * The number of full seconds since the epoch. Set to @ref INVALID if
   * the timestamp is invalid or unknown.
   */
  uint32_t seconds = INVALID;

  /** The fractional part of the second, expressed in nanoseconds. */
  uint32_t fraction_ns = INVALID;
};

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
