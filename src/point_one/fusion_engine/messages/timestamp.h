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

  /** @brief Construct an invalid timestamp. */
  Timestamp() = default;

  /**
   * @brief Construct a timestamp.
   *
   * @param sec The whole-seconds component.
   * @param ns  The nanoseconds component.
   */
  Timestamp(uint32_t sec, uint32_t ns) : seconds(sec), fraction_ns(ns) {}

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
   * @brief Construct a @ref Timestamp object from a GPS week number and time of
   *        week.
   *
   * @param week_number The GPS week number.
   * @param tow_sec The GPS time of week (in seconds).
   *
   * @return The resulting @ref Timestamp.
   */
  static Timestamp FromGPSTime(uint16_t week_number, double tow_sec) {
    Timestamp result;
    if (std::isfinite(tow_sec) && tow_sec >= 0.0) {
      uint32_t tow_sec_int = static_cast<uint32_t>(tow_sec);
      result.seconds = week_number * 604800 + tow_sec_int;
      result.fraction_ns =
          static_cast<uint32_t>(std::lround((tow_sec - tow_sec_int) * 1e9));
      if (result.fraction_ns >= 1000000000) {
        ++result.seconds;
        result.fraction_ns -= 1000000000;
      }
    }
    return result;
  }
};

/**
 * @brief Represents a signed duration or time difference between two @ref
 *        Timestamp values.
 *
 * Unlike @ref Timestamp, which represents an absolute point in time using
 * unsigned fields, `TimeDelta` uses signed integers to express durations that
 * may be negative (i.e., in the past relative to a reference time).
 *
 * Both @ref seconds and @ref fraction_ns always share the same sign: both
 * fields will be negative to represent negative values. For example, -1.5
 * seconds is represented as `{seconds=-1, fraction_ns=-500000000}`, never as
 * `{seconds=0, fraction_ns=-1500000000}` or `{seconds=-2,
 * fraction_ns=500000000}`.
 *
 * Both fields are set to @ref INVALID (`INT32_MIN`) to indicate an invalid or
 * unknown delta.
 */
struct TimeDelta {
  static constexpr int32_t INVALID = INT32_MIN;

  /**
   * The number of full seconds in the delta. Negative for deltas in the past.
   * Set to @ref INVALID if the delta is invalid or unknown.
   */
  int32_t seconds = INVALID;

  /**
   * The fractional part of the second, expressed in nanoseconds.
   *
   * Always has the same sign as @ref seconds (or is zero). Valid range is
   * `[-999,999,999, 999,999,999]`. Set to @ref INVALID if the delta is
   * invalid or unknown.
   */
  int32_t fraction_ns = INVALID;

  /** @brief Construct an invalid delta. */
  TimeDelta() = default;

  /**
   * @brief Construct a delta from seconds and nanoseconds, normalizing as
   *        needed.
   *
   * `fraction_ns` may exceed ±999,999,999; any excess is folded into
   * @ref seconds. For example, `TimeDelta(0, 1500000000)` produces
   * `{seconds=1, fraction_ns=500000000}`.
   *
   * @param sec The whole-seconds component.
   * @param ns  The nanoseconds component. May be larger than 1 sec.
   */
  TimeDelta(int32_t sec, int32_t ns) : seconds(sec), fraction_ns(ns) {
    if (seconds != INVALID && fraction_ns != INVALID) {
      Normalize();
    }
  }

  /**
   * @brief Construct a delta from a floating point second value.
   *
   * @param sec The second value.
   */
  TimeDelta(double sec) {
    if (std::isfinite(sec) && sec <= INT32_MAX &&
        sec >= static_cast<double>(INT32_MIN) - 1.0) {
      seconds = static_cast<int32_t>(sec);
      fraction_ns = static_cast<int32_t>(std::lround((sec - seconds) * 1e9));
      Normalize();
    }
  }

  /**
   * @brief Check if this delta is valid.
   *
   * @return `true` if the delta is valid.
   */
  bool IsValid() const { return seconds != INVALID && fraction_ns != INVALID; }

  /**
   * @brief Convert this delta to a floating-point number of seconds.
   *
   * @return The delta expressed as seconds, or `NAN` if the delta is
   *         invalid.
   */
  double ToSeconds() const {
    if (IsValid()) {
      return seconds + (fraction_ns * 1e-9);
    } else {
      return NAN;
    }
  }

  /**
   * @brief Normalize the delta so that @ref seconds and @ref fraction_ns
   *        share the same sign.
   *
   * After any arithmetic operation, this ensures the invariant that
   * `fraction_ns` is always in the range `(-999,999,999, 999,999,999)` and
   * has the same sign as `seconds` (or is zero). For example,
   * `{seconds=1, fraction_ns=-200000000}` is normalized to
   * `{seconds=0, fraction_ns=800000000}`.
   *
   * This is called automatically by the two-argument constructor and all
   * arithmetic operators and does not need to be called manually under normal
   * use.
   */
  void Normalize() {
    // Convert |fraction_ns| to <1 second. This must be done before sign
    // alignment.
    if (fraction_ns >= 1000000000) {
      seconds += fraction_ns / 1000000000;
      fraction_ns %= 1000000000;
    } else if (fraction_ns <= -1000000000) {
      seconds += fraction_ns / 1000000000;
      fraction_ns %= 1000000000;
    }

    // Align signs for second and fraction_ns. We already guaranteed fraction_ns
    // is <1 sec, so no % operation needed.
    if (fraction_ns > 0 && seconds < 0) {
      seconds += 1;
      fraction_ns -= 1000000000;
    } else if (fraction_ns < 0 && seconds > 0) {
      seconds -= 1;
      fraction_ns += 1000000000;
    }
  }

  /**
   * @brief Check if this is a valid delta.
   *
   * @return `true` if the delta is valid.
   */
  operator bool() const { return IsValid(); }

  /**
   * @brief Add another @ref TimeDelta to this one in place.
   *
   * If either operand is invalid, the result is set to @ref INVALID.
   *
   * @param rhs The delta to add.
   *
   * @return A reference to this delta after addition.
   */
  TimeDelta& operator+=(const TimeDelta& rhs) {
    if (IsValid()) {
      if (rhs.IsValid()) {
        seconds += rhs.seconds;
        fraction_ns += rhs.fraction_ns;
        Normalize();
      } else {
        *this = {INVALID, INVALID};
      }
    }
    return *this;
  }

  /**
   * @brief Subtract another @ref TimeDelta from this one in place.
   *
   * If either operand is invalid, the result is set to @ref INVALID.
   *
   * @param rhs The delta to subtract.
   *
   * @return A reference to this delta after subtraction.
   */
  TimeDelta& operator-=(const TimeDelta& rhs) {
    if (IsValid()) {
      if (rhs.IsValid()) {
        seconds -= rhs.seconds;
        fraction_ns -= rhs.fraction_ns;
        Normalize();
      } else {
        *this = {INVALID, INVALID};
      }
    }
    return *this;
  }

  /**
   * @brief Add two @ref TimeDelta values.
   *
   * If either operand is invalid, the result is @ref INVALID.
   *
   * @param lhs The left-hand operand.
   * @param rhs The right-hand operand.
   *
   * @return The sum of the two deltas.
   */
  friend TimeDelta operator+(TimeDelta lhs, const TimeDelta& rhs) {
    lhs += rhs;
    return lhs;
  }

  /**
   * @brief Subtract one @ref TimeDelta from another.
   *
   * If either operand is invalid, the result is @ref INVALID.
   *
   * @param lhs The left-hand operand.
   * @param rhs The delta to subtract.
   *
   * @return The difference of the two deltas.
   */
  friend TimeDelta operator-(TimeDelta lhs, const TimeDelta& rhs) {
    lhs -= rhs;
    return lhs;
  }
};

/**
 * @brief Compute the difference between two @ref Timestamp values as a
 *        @ref TimeDelta.
 *
 * @param lhs The timestamp to subtract from.
 * @param rhs The timestamp to subtract.
 *
 * @return A @ref TimeDelta representing `lhs - rhs`, or an invalid
 *         delta if either operand is invalid.
 */
inline TimeDelta operator-(const Timestamp& lhs, const Timestamp& rhs) {
  if (!lhs.IsValid() || !rhs.IsValid()) {
    return TimeDelta();
  }

  TimeDelta result;
  result.seconds =
      static_cast<int32_t>(lhs.seconds) - static_cast<int32_t>(rhs.seconds);
  result.fraction_ns = static_cast<int32_t>(lhs.fraction_ns) -
                       static_cast<int32_t>(rhs.fraction_ns);
  result.Normalize();
  return result;
}

/**
 * @brief Offset a @ref Timestamp forward by a @ref TimeDelta.
 *
 * @param lhs The base timestamp.
 * @param rhs The delta to add.
 *
 * @return A new @ref Timestamp equal to `lhs + rhs`, or an invalid
 *         timestamp if either operand is invalid or the result falls outside
 *         the representable range of @ref Timestamp.
 */
inline Timestamp operator+(Timestamp lhs, const TimeDelta& rhs) {
  if (!lhs.IsValid() || !rhs.IsValid()) {
    return Timestamp();
  }

  int64_t sec = static_cast<int64_t>(lhs.seconds) + rhs.seconds;
  int64_t ns = static_cast<int64_t>(lhs.fraction_ns) + rhs.fraction_ns;
  if (ns < 0) {
    sec -= 1;
    ns += 1000000000;
  } else if (ns >= 1000000000) {
    sec += ns / 1000000000;
    ns %= 1000000000;
  }

  if (sec < 0 || sec > static_cast<int64_t>(Timestamp::INVALID - 1)) {
    return Timestamp();
  } else {
    return Timestamp{static_cast<uint32_t>(sec), static_cast<uint32_t>(ns)};
  }
}

/**
 * @brief Offset a @ref Timestamp backwards by a @ref TimeDelta.
 *
 * @param lhs The base timestamp.
 * @param rhs The delta to subtract.
 *
 * @return A new @ref Timestamp equal to `lhs - rhs`, or an invalid
 *         timestamp if either operand is invalid or the result falls outside
 *         the representable range of @ref Timestamp.
 */
inline Timestamp operator-(const Timestamp& lhs, const TimeDelta& rhs) {
  if (!rhs.IsValid()) {
    return Timestamp();
  }

  TimeDelta negated{-rhs.seconds, -rhs.fraction_ns};
  negated.Normalize();
  return lhs + negated;
}

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
