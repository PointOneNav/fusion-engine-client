/**************************************************************************/ /**
 * @brief Device status messages.
 * @file
 ******************************************************************************/

#pragma once

#include "point_one/fusion_engine/common/portability.h"
#include "point_one/fusion_engine/messages/defs.h"

namespace point_one {
namespace fusion_engine {
namespace messages {

// Enforce 4-byte alignment and packing of all data structures and values.
// Floating point values are aligned on platforms that require it. This is done
// with a combination of setting struct attributes, and manual alignment
// within the definitions. See the "Message Packing" section of the README.
#pragma pack(push, 1)

/**************************************************************************/ /**
 * @defgroup device_status Device Status/Information Messages
 * @brief Messages for indicating high-level device status (notifications,
 *        software version, etc.).
 * @ingroup messages
 * @ingroup config_and_ctrl_messages
 *
 * See also @ref messages and @ref config_and_ctrl_messages.
 ******************************************************************************/

/**
 * @brief Software version information, (@ref
 *        MessageType::VERSION_INFO, version 1.0).
 * @ingroup device_status
 *
 * This message contains version strings for each of the following, where
 * available:
 * - Firmware - The current version of the platform software/firmware being used
 * - Engine - The version of Point One FusionEngine being used
 * - OS - The version of the operating system/kernel/bootloader being used
 * - GNSS Receiver - The version of firmware being used by the device's GNSS
 *   receiver
 *
 * The message payload specifies the length of each string (in bytes). It is
 * followed by each of the listed version strings consecutively. The strings are
 * _not_ null-terminated.
 *
 * ```
 * {MessageHeader, VersionInfoMessage, "Firmware Version", "Engine Version",
 *  "OS Version", "Receiver Version"}
 * ```
 *
 * The following is an example of extracting the firmware and engine version
 * strings from a byte array containing the entire message:
 * ```cpp
 * auto message = *reinterpret_cast<const VersionInfoMessage*>(buffer);
 * buffer += sizeof(VersionInfoMessage);
 * std::string fw_version(buffer, message.fw_version_length);
 * buffer += message.fw_version_length;
 * std::string engine_version(buffer, message.engine_version_length);
 * ```
 */
struct P1_ALIGNAS(4) VersionInfoMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::VERSION_INFO;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The current system timestamp (in ns).*/
  int64_t system_time_ns = 0;

  /** The length of the firmware version string (in bytes). */
  uint8_t fw_version_length = 0;

  /** The length of the FusionEngine version string (in bytes). */
  uint8_t engine_version_length = 0;

  /** The length of the OS version string (in bytes). */
  uint8_t os_version_length = 0;

  /** The length of the GNSS receiver version string (in bytes). */
  uint8_t rx_version_length = 0;

  uint8_t reserved[4] = {0};
};

/**
 * @brief Identifies a FusionEngine device.
 * @ingroup device_status
 */
enum class DeviceType : uint8_t {
  /** Unable to map device to a defined entry. */
  UNKNOWN = 0,
  /** Point One Atlas. */
  ATLAS = 1,
  /** Quectel LG69T-AM system. */
  LG69T_AM = 2,
  /** Quectel LG69T-AP system. */
  LG69T_AP = 3,
  /** Quectel LG69T-AH system. */
  LG69T_AH = 4,
  /** Nexar Beam2K system. */
  NEXAR_BEAM2K = 5,
  /** Point One SSR client running on an LG69T platform. */
  SSR_LG69T = 6,
  /** Point One SSR client running on a desktop platform. */
  SSR_DESKTOP = 7,
};

/**
 * @brief Get a human-friendly string name for the specified @ref DeviceType.
 * @ingroup device_status
 *
 * @param val The enum to get the string name for.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(DeviceType val) {
  switch (val) {
    case DeviceType::UNKNOWN:
      return "Unknown";
    case DeviceType::ATLAS:
      return "ATLAS";
    case DeviceType::LG69T_AM:
      return "LG69T_AM";
    case DeviceType::LG69T_AP:
      return "LG69T_AP";
    case DeviceType::LG69T_AH:
      return "LG69T_AH";
    case DeviceType::NEXAR_BEAM2K:
      return "NEXAR_BEAM2K";
    case DeviceType::SSR_LG69T:
      return "SSR_LG69T";
    case DeviceType::SSR_DESKTOP:
      return "SSR_DESKTOP";
  }
  return "Unrecognized";
}

/**
 * @brief @ref DeviceType stream operator.
 * @ingroup measurement_messages
 */
inline p1_ostream& operator<<(p1_ostream& stream, DeviceType val) {
  stream << to_string(val) << " (" << (int)val << ")";
  return stream;
}

/**
 * @brief Device identifier information (@ref MessageType::DEVICE_ID, version
 *        1.0).
 * @ingroup device_status
 *
 * This message contains ID fields for each of the following, where applicable.
 * - Hardware - A unique ROM identifier pulled from the device hardware (for
 *   example, a CPU serial number)
 * - User - A value set by the user to identify a device
 * - Receiver - A unique ROM identifier pulled from the GNSS receiver
 *
 * The message payload specifies the length of each field (in bytes), and is
 * followed by each of the ID values. ID values may be strings or binary,
 * depending on the type of device (@ref device_type). Strings are _not_
 * null-terminated.
 *
 * ```
 * {MessageHeader, DeviceIDMessage, "HW ID", "User ID", "Receiver ID"}
 * ```
 *
 * The following is an example of extracting the hardware and user IDs from a
 * byte array containing the entire message (assuming both are strings for this
 * example device):
 * ```cpp
 * auto message = *reinterpret_cast<const DeviceIDMessage*>(buffer);
 * buffer += sizeof(DeviceIDMessage);
 * std::string hw_id(buffer, message.hw_id_length);
 * buffer += message.hw_id_length;
 * std::string user_id(buffer, message.user_id_length);
 * ```
 */
struct P1_ALIGNAS(4) DeviceIDMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::DEVICE_ID;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The current system timestamp (in ns).*/
  int64_t system_time_ns = 0;

  /** The type of device this message originated from.*/
  DeviceType device_type = DeviceType::UNKNOWN;

  /** The length of the harware ID (in bytes). */
  uint8_t hw_id_length = 0;

  /** The length of the user specified ID (in bytes). */
  uint8_t user_id_length = 0;

  /** The length of the GNSS receiver ID (in bytes). */
  uint8_t receiver_id_length = 0;

  uint8_t reserved[4] = {0};
};

/**
 * @brief Notification of a system event for logging purposes (@ref
 *        MessageType::EVENT_NOTIFICATION, version 1.0).
 * @ingroup device_status
 *
 * This message is followed by a string describing the event or additional
 * binary content, depending on the type of event. The length of the description
 * is @ref event_description_len_bytes. Strings are _not_ null-terminated.
 *
 * ```
 * {MessageHeader, EventNotificationMessage, "Description"}
 * ```
 */
struct P1_ALIGNAS(4) EventNotificationMessage : public MessagePayload {
  enum class EventType : uint8_t {
    /**
     * Event containing a logged message string from the device.
     */
    LOG = 0,
    /**
     * Event indicating a device reset occurred. The event flags will be set to
     * the requested reset bitmask, if applicable (see @ref ResetRequest). The
     * payload will contain a string describing the cause of the reset.
     */
    RESET = 1,
    /**
     * Notification that the user configuration has been changed. Intended for
     * diagnostic purposes.
     */
    CONFIG_CHANGE = 2,
    /**
     * Notification that the user performed a command (e.g., configuration
     * request, fault injection enable/disable).
     */
    COMMAND = 3,
    /**
     * Record containing the response to a user command. Response events are not
     * output on the interface on which the command was received; that interface
     * will receive the response itself.
     */
    COMMAND_RESPONSE = 4,
  };

  static P1_CONSTEXPR_FUNC const char* to_string(EventType type) {
    switch (type) {
      case EventType::LOG:
        return "Log";

      case EventType::RESET:
        return "Reset";

      case EventType::CONFIG_CHANGE:
        return "Config Change";

      case EventType::COMMAND:
        return "Command";

      case EventType::COMMAND_RESPONSE:
        return "Command Response";

      default:
        return "Unknown";
    }
  }

  static constexpr MessageType MESSAGE_TYPE = MessageType::EVENT_NOTIFICATION;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The type of event that occurred. */
  EventType type = EventType::LOG;

  uint8_t reserved1[3] = {0};

  /** The system time when the event occurred (in ns).*/
  int64_t system_time_ns = 0;

  /** A bitmask of flags associated with the event. */
  uint64_t event_flags = 0;

  /** The number of bytes in the event description string. */
  uint16_t event_description_len_bytes = 0;

  uint8_t reserved2[2] = {0};
};

/**
 * @brief RTCM output source types.
 * @ingroup device_status
 */
enum class RTKOutputSource : uint8_t {
  /** No RTCM output available. */
  NONE = 0,
  /** RTCM output received from an incoming base station. */
  OSR = 1,
  /** RTCM output generated SSR model data. */
  SSR = 2,
};

/**
 * @brief Get a human-friendly string name for the specified @ref
 *        RTKOutputSource.
 * @ingroup device_status
 *
 * @param source The enum to get the string name for.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(RTKOutputSource source) {
  switch (source) {
    case RTKOutputSource::NONE:
      return "NONE";
    case RTKOutputSource::OSR:
      return "OSR";
    case RTKOutputSource::SSR:
      return "SSR";
  }
  return "Unknown";
}

/**
 * @brief @ref RTKOutputSource stream operator.
 * @ingroup device_status
 */
inline p1_ostream& operator<<(p1_ostream& stream, RTKOutputSource source) {
  stream << to_string(source) << " (" << (int)source << ")";
  return stream;
}

/**
 * @brief System status information (@ref
 *        MessageType::SYSTEM_STATUS, version 1.0).
 * @ingroup device_status
 */

struct P1_ALIGNAS(4) SystemStatusMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::SYSTEM_STATUS;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  static constexpr int16_t INVALID_TEMPERATURE = INT16_MAX;

  /** The time of the message, in P1 time (beginning at power-on). */
  Timestamp p1_time;

  /**
   * The temperature of the GNSS receiver (in deg Celcius * 2^-7). Set to
   * 0x7FFF if invalid.
   */
  int16_t gnss_temperature = INVALID_TEMPERATURE;

  uint8_t reserved[118] = {0};
};

/**
 * @brief State-space representation (SSR) GNSS corrections status (@ref
 *        MessageType::SSR_STATUS, version 1.0).
 * @ingroup device_status
 */
struct P1_ALIGNAS(4) SSRStatusMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::SSR_STATUS;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  static constexpr uint16_t INVALID_STATION_ID = 0xFFFF;
  static constexpr uint8_t INVALID_GRID_ID = 0xFF;

  /**
   * The time of the message, in P1 time (beginning at power-on).
   */
  Timestamp p1_time;

  /**
   * @name RTCM Output Status
   * @{
   */

  /**
   * The GPS time corresponding with the most recently output corrections data.
   */
  Timestamp output_gps_time;
  /**
   * The source of the most recent output RTCM corrections data.
   */
  RTKOutputSource output_source = RTKOutputSource::NONE;
  uint8_t reserved1 = 0;
  /**
   * The RTCM base station ID contained in the most recent corrections data.
   */
  uint16_t output_station_id = INVALID_STATION_ID;

  /** The base station longitude (in degrees). */
  double base_latitude_deg = NAN;
  /** The base station latitude (in degrees). */
  double base_longitude_deg = NAN;
  /** The base station altitude (in meters). */
  double base_altitude_m = NAN;

  /** The number of satellites present in the most recent corrections data. */
  uint8_t num_satellites = 0;
  /** The number of GNSS signals present in the most recent corrections data. */
  uint8_t num_signals = 0;

  /**
   * A bitmask indicating which GNSS constellations are present in the generated
   * corrections data.
   *
   * Bit offsets corresponding withe @ref SatelliteType enum values for each
   * constellation.
   *
   *  Bit  | Description
   * ----- | -----------
   *   0   | _Reserved for future use_
   *   1   | GPS
   *   2   | GLONASS
   *   3   | _Reserved for future use_
   *   4   | Galileo
   *   5   | BeiDou
   *   6   | QZSS
   *   7   | _Reserved for future use_
   *   8   | SBAS
   *   9   | IRNSS
   * 10-15 | _Reserved for future use_
   */
  uint16_t gnss_systems_mask = 0x0;

  /**
   * A bitmask indicating which GPS signal types are present in the generated
   * corrections data.
   *
   *  Bit  | Description
   * ----- | -----------
   *   0   | L1 C/A
   *   1   | L1P
   *   2   | L1C
   *   3   | _Reserved for future use_
   *   4   | L2C
   *   5   | L2P
   *  6-7  | _Reserved for future use_
   *   8   | L5
   *  9-15 | _Reserved for future use_
   */
  uint16_t gps_signal_types_mask = 0x0;

  /**
   * A bitmask indicating which GLONASS signal types are present in the
   * generated corrections data.
   *
   *  Bit  | Description
   * ----- | -----------
   *   0   | L1 C/A
   *   1   | L1P
   *  2-3  | _Reserved for future use_
   *   4   | L2 C/A
   *   5   | L2P
   *  6-15 | _Reserved for future use_
   */
  uint16_t glo_signal_types_mask = 0x0;

  /**
   * A bitmask indicating which Galileo signal types are present in the
   * generated corrections data.
   *
   *  Bit  | Description
   * ----- | -----------
   *   0   | E1-A
   *   1   | E1-BC
   *  2-3  | _Reserved for future use_
   *   4   | E5b
   *  5-7  | _Reserved for future use_
   *   8   | E5a
   *  9-11 | _Reserved for future use_
   *  12   | E6-A
   *  13   | E6-BC
   * 14-15 | _Reserved for future use_
   */
  uint16_t gal_signal_types_mask = 0x0;

  /**
   * A bitmask indicating which BeiDou signal types are present in the
   * generated corrections data.
   *
   *  Bit  | Description
   * ----- | -----------
   *   0   | B1I
   *   1   | B1C
   *  2-3  | _Reserved for future use_
   *   4   | B2I
   *   5   | B2b
   *  6-7  | _Reserved for future use_
   *   8   | B2a
   *  9-11 | _Reserved for future use_
   *  12   | B3
   * 13-15 | _Reserved for future use_
   */
  uint16_t bds_signal_types_mask = 0x0;

  uint8_t reserved2[8] = {0};

  /** @} */

  /**
   * @name Satellite Ephemeris Status
   * @{
   */

  /**
   * The number of GPS satellites for which ephemeris data is available (may
   * include satellites that are not currently visible).
   */
  uint8_t num_gps_ephemeris = 0;
  /**
   * The number of GLONASS satellites for which ephemeris data is available (may
   * include satellites that are not currently visible).
   */
  uint8_t num_glo_ephemeris = 0;
  /**
   * The number of Galileo satellites for which ephemeris data is available (may
   * include satellites that are not currently visible).
   */
  uint8_t num_gal_ephemeris = 0;
  /**
   * The number of BeiDou satellites for which ephemeris data is available (may
   * include satellites that are not currently visible).
   */
  uint8_t num_bds_ephemeris = 0;

  uint8_t reserved3[4] = {0};

  /** @} */

  /**
   * @name Incoming OSR Base Station Data Status
   * @{
   */

  /**
   * A bitmask indicating the status of incoming OSR corrections data from an
   * external base station RTCM data stream.
   *
   *  Bit  | Description
   * ----- | -----------
   *   0   | (Real) OSR corrections data available
   *  1-15 | _Reserved for future use_
   */
  uint16_t osr_data_status = 0x0;

  uint8_t reserved4[2] = {0};

  /** @} */

  /**
   * @name Incoming SSR Model Data Status
   * @{
   */

  /**
   * A bitmask indicating the status of incoming SSR corrections data.
   *
   *  Bit  | Description
   * ----- | -----------
   *   0   | SSR model data ready for OSR generation
   *  1-15 | _Reserved for future use_
   */
  uint16_t ssr_data_status = 0x0;

  uint8_t reserved5 = 0;

  /**
   * The identifier of the local SSR corrections grid currently in use.
   */
  uint8_t ssr_grid_id = INVALID_GRID_ID;

  /**
   * A bitmask indicating which SSR model components are enabled for the current
   * corrections region.
   *
   * The following table describes the bit definitions used by this mask, and by
   * the component status masks in this structure (@ref ssr_decode_status_mask,
   * @ref ssr_model_status_mask).
   *
   *  Bit  | Description
   * ----- | -----------
   *   0   | SSR network metadata
   *   1   | Grid definition
   *   2   | Satellite group definition
   *   3   | Geoid model data
   *   4   | Antenna corrections data (ATX)
   *   5   | High-rate satellite corrections data
   *   6   | Low-rate satellite corrections data
   *   7   | Global per-satellite ionosphere (GSI) data
   *   8   | Gridded per-satellite ionosphere (GRI) data
   *   9   | Gridded troposphere (GRT) data
   *  10   | Regional per-satellite ionosphere (RSI) data
   *  11   | Global vertical ionosphere delay (GVI) data
   *  12   | Regional troposphere (RT) data
   * 13-15 | _Reserved for future use_
   */
  uint16_t ssr_enabled_component_mask = 0x0;

  /**
   * A bitmask indicating the status of the individual SSR component models
   * (0 = model data not available/expired, 1 = model data usable).
   *
   * See @ref ssr_enabled_component_mask for bit definitions. Synthetic OSR
   * generation is ready when the bits for all models indicated by
   * @ref ssr_enabled_component_mask are set in this mask.
   *
   * See also @ref ssr_decode_status_mask.
   */
  uint16_t ssr_model_status_mask = 0x0;

  /**
   * A bitmask indicating the decoding status of the incoming SSR data messages
   * (0 = waiting for data, 1 = decoded data received).
   *
   * @note
   * Generating OSR measurements requires a complete set of SSR model data from
   * a consistent time epoch. SSR data will be made available to the SSR models
   * after a complete data set arrives. This bitmask indicates the status of the
   * individual incoming data messages as they arrive and get decoded.\n
   * \n
   * When the first SSR message of new time epoch arrives, the decode status for
   * the other SSR models in this bitmask may be cleared. They will be set again
   * as their data messages arrive for the new epoch. In the meantime, the SSR
   * models will continue to produce synthetic OSR measurements using model data
   * from the previous time epoch until either the new epoch is completed or the
   * previous data expires. @ref ssr_model_status_mask indicates the status of
   * the data in use by the SSR models.
   *
   * See @ref ssr_enabled_component_mask for bit definitions.
   */
  uint16_t ssr_decode_status_mask = 0x0;

  uint8_t reserved6[2] = {0};

  /** @} */

  /**
   * @name Incoming Data Interface Status
   * @{
   */

  /**
   * The number of messages successfully decoded from the primary SSR data
   * interface.
   */
  uint32_t ssr_primary_message_count = 0;

  /**
   * The number of CRC failures detected on the primary SSR interface.
   *
   * The sum of @c ssr_primary_message_count and @c ssr_primary_crc_fail_count
   * is an _approximation_ of the total number of SSR messages received on the
   * interface:
   * - If the data preamble appears in the middle of the data stream, it is
   *   possible to count a "failure" for a message that was not present
   * - If the interface contains both SSR data and other binary interleaved, CRC
   *   failures may occur whenever non-SSR data is received if the SSR preamble
   *   is present in the non-SSR data
   */
  uint32_t ssr_primary_crc_fail_count = 0;

  /** @} */
};

#pragma pack(pop)

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
