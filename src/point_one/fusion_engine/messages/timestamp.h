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

  /**
   * @brief Check if this is a valid timestamp.
   *
   * @return `true` if the timestamp is valid.
   */
  bool IsValid() const { return seconds != INVALID && fraction_ns != INVALID; }

  /**
   * @brief Get the timestamp value in seconds.
   *
   * @return The timestamp value (in seconds), or `NAN` if invalid.
   */
  double ToSeconds() const {
    if (IsValid()) {
      return seconds + (fraction_ns * 1e-9);
    } else {
      return NAN;
    }
  }

  /**
   * @brief Convert a timestamp to GPS week number and time of week.
   *
   * @param week_number Set to the GPS week number.
   * @param tow_sec Set to the GPS time of week (in seconds).
   *
   * @return `true` on success, `false` if the timestamp is invalid.
   */
  bool ToGPSWeekTOW(uint16_t* week_number, double* tow_sec) const {
    if (IsValid()) {
      if (week_number) {
        *week_number = static_cast<uint16_t>(seconds / 604800);
      }
      if (tow_sec) {
        *tow_sec = (seconds % 604800) + (fraction_ns * 1e-9);
      }
      return true;
    } else {
      return false;
    }
  }

  /**
   * @brief Check if this is valid timestamp.
   *
   * @return `true` if the timestamp is valid.
   */
  operator bool() const { return IsValid(); }

  /**
   * @brief Get the timestamp value in seconds.
   *
   * @return The timestamp value (in seconds), or `NAN` if invalid.
   */
  operator double() const { return ToSeconds(); }
};

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
