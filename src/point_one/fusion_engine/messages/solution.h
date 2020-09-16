/**************************************************************************/ /**
 * @brief Platform position/attitude solution messages.
 ******************************************************************************/

#pragma once

#include "point_one/fusion_engine/messages/defs.h"

namespace point_one {
namespace fusion_engine {
namespace messages {

// Enforce 4-byte alignment and packing of all data structures and values so
// that floating point values are aligned on platforms that require it.
#pragma pack(push, 4)

/**
 * @brief Platform pose solution (position, velocity, attitude). \[@ref
 *        MessageType::POSE\]
 *
 * @note
 * All data is timestamped using the Point One Time, which is a monotonic
 * timestamp referenced to the start of the device. Corresponding messages (@ref
 * GNSSInfoMessage, @ref IMUCorrectionsMessage, etc.) may be associated using
 * their @ref p1_time values.
 */
struct PoseMessage {
  /** The time of the message, in P1 time (beginning at power-on). */
  Timestamp p1_time;

  /** The GPS time of the message, if available, referenced to 1980/1/6. */
  Timestamp gps_time;

  /** The type of this position solution. */
  SolutionType solution_type;

  uint8_t reserved[3] = {0};

  /**
   * The WGS-84 geodetic latitude, longitude, and altitude (in degrees/meters).
   */
  double lla_deg[3] = {NAN, NAN, NAN};

  /**
   * The position standard deviation (in meters), resolved in the local level
   * frame: east, north, up.
   */
  float position_std_enu_m[3] = {NAN, NAN, NAN};

  /**
   * The platform attitude (in degrees), if known, described as intrinsic
   * Euler-321 angles (yaw, pitch, roll) with respect to the local level frame.
   * Set to `NAN` if attitude is not available.
   *
   * @note
   * The platform body axes are defined as +x forward, +y left, and +z up. A
   * positive yaw is a left turn, positive pitch points the nose of the vehicle
   * down, and positive roll is a roll toward the right. Yaw is measured from
   * east in a counter-clockwise direction. For example, north is +90 degrees
   * (i.e., `heading = 90.0 - ypr_deg[0]`).
   */
  double ypr_deg[3] = {NAN, NAN, NAN};

  /**
   * The attitude standard deviation (in degrees): yaw, pitch, roll.
   */
  float ypr_std_deg[3] = {NAN, NAN, NAN};

  /**
   * The platform velocity (in meters/second), resolved in the body frame.
   */
  double velocity_body_mps[3] = {NAN, NAN, NAN};

  /**
   * The velocity standard deviation (in meters/second), resolved in the body
   * frame.
   */
  float velocity_std_body_mps[3] = {NAN, NAN, NAN};

  /** The estimated aggregate 3D protection level (in meters). */
  float aggregate_protection_level_m = NAN;
  /** The estimated 2D horizontal protection level (in meters). */
  float horizontal_protection_level_m = NAN;
  /** The estimated vertical protection level (in meters). */
  float vertical_protection_level_m = NAN;
};

/**
 * @brief Information about the GNSS data used in the @ref PoseMessage with the
 *        corresponding timestamp. \[@ref MessageType::GNSS_INFO\]
 *
 * This message is followed by `N` @ref SatelliteInfo objects, where `N` is
 * equal to @ref num_satellites. For example, a message with two satellites
 * would be serialized as:
 *
 * ```
 * {MessageHeader, GNSSInfoMessage, SatelliteInfo, SatelliteInfo}
 * ```
 */
struct GNSSInfoMessage {
  static constexpr uint32_t INVALID_REFERENCE_STATION = 0xFFFFFFFF;

  /** The time of the message, in P1 time (beginning at power-on). */
  Timestamp p1_time;

  /** The GPS time of the message, if available, referenced to 1980/1/6. */
  Timestamp gps_time;

  /** The P1 time of the last differential GNSS update. */
  Timestamp last_differential_time;

  /** The ID of the differential base station, if used. */
  uint32_t reference_station_id = INVALID_REFERENCE_STATION;

  /** The geometric dilution of precision (GDOP). */
  float gdop = NAN;
  /** The position dilution of precision (PDOP). */
  float pdop = NAN;
  /** The horizontal dilution of precision (HDOP). */
  float hdop = NAN;
  /** The vertical dilution of precision (VDOP). */
  float vdop = NAN;

  /** The number of known satellites. */
  uint16_t num_satellites = 0;

  uint8_t reserved[2] = {0};
};

/**
 * @brief Information about an individual satellite.
 *
 * For satellites where @ref used_in_solution is 0, the satellite may either be
 * currently tracked by the receiver, or may just be expected according to
 * available ephemeris data.
 */
struct SatelliteInfo {
  /** The GNSS system to which this satellite belongs. */
  SatelliteType system = SatelliteType::UNKNOWN;

  /** The satellite's PRN (or slot number for GLONASS). */
  uint8_t prn = 0;

  /**
   * Set to 1 if the satellite was used in the latest navigation solution, 0
   * if not.
   */
  uint8_t used_in_solution = 0;

  uint8_t reserved = 0;

  /** The azimuth of the satellite (in degrees). */
  float azimuth_deg = NAN;

  /** The elevation of the satellite (in degrees). */
  float elevation_deg = NAN;
};

#pragma pack(pop)

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
