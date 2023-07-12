/**************************************************************************/ /**
 * @brief System fault control messages.
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
// within the definitions.
#pragma pack(push, 1)

/**
 * @defgroup fault_control_messages System Fault Control
 * @brief Messages/types for controlling or simulating system faults.
 * @ingroup config_and_ctrl_messages
 */

/**
 * @brief Available fault types/control inputs.
 * @ingroup fault_control_messages
 *
 * See @ref FaultControlMessage.
 */
enum class FaultType : uint8_t {
  /**
   * Clear existing faults.
   *
   * @note
   * This cannot be used to clear a @ref FaultType::CRASH or @ref
   * FaultType::FATAL_ERROR.
   *
   * Payload format: none
   */
  CLEAR_ALL = 0,
  /**
   * Force the device to crash (intended for factory test purposes only).
   *
   * On crash, the device no longer produce any output on any interfaces, and
   * will stop responding to commands. If the watchdog is enabled, the device
   * will restart automatically after the watchdog timer elapses.
   *
   * @warning
   * The device will crash immediately after receiving this request. It will not
   * send a @ref CommandResponseMessage back to the user.
   *
   * Payload format: none
   */
  CRASH = 1,
  /**
   * Force the device to exhibit a fatal error (intended for factory test
   * purposes only).
   *
   * After a fatal error, the device will stop navigating and will no longer
   * produce solution messages on any interfaces. Instead, it will output an
   * @ref EventNotificationMessage indicating the fault status. If the watchdog
   * is enabled, the device will restart automatically after the watchdog timer
   * elapses.
   *
   * Unlike @ref FaultType::CRASH, a fatal error will send an error notification
   * to the user, but will still not send a @ref CommandResponseMessage.
   *
   * Payload format: none
   */
  FATAL_ERROR = 2,
  /**
   * Simulate a COCOM limit (intended for factory test purposes only).
   *
   * When a COCOM limit is exceeded, the device will stop navigating and will
   * produce @ref SolutionType::Invalid solution messages. COCOM limits may be
   * cleared via @ref ResetRequest, or by sending a @ref CoComType::NONE fault
   * control.
   *
   * Payload format: @ref CoComType
   */
  COCOM = 3,
  /**
   * Enable/disable use of GNSS measurements (intended for dead reckoning
   * performance testing).
   *
   * Payload format: `uint8_t` (0=disable, 1=enable)
   */
  ENABLE_GNSS = 4,
  /**
   * Simulate a region blackout (intended for factory test purposes only).
   *
   * Payload format: `uint8_t` (0=disable, 1=enable)
   */
  REGION_BLACKOUT = 5,
  /**
   * Enable/disable Quectel test features (intended for factory test purposes
   * only).
   *
   * Payload format: `uint8_t` (0=disable, 1=enable)
   */
  QUECTEL_TEST = 6,
};

/**
 * @brief Get a human-friendly string name for the specified @ref FaultType.
 * @ingroup fault_control_messages
 *
 * @param type The desired fault type.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(FaultType type) {
  switch (type) {
    case FaultType::CLEAR_ALL:
      return "Clear Faults";

    case FaultType::CRASH:
      return "Crash";

    case FaultType::FATAL_ERROR:
      return "Fatal Error";

    case FaultType::COCOM:
      return "COCOM";

    case FaultType::ENABLE_GNSS:
      return "Enable GNSS";

    case FaultType::REGION_BLACKOUT:
      return "Region Blackout";

    case FaultType::QUECTEL_TEST:
      return "Quectel Test";

    default:
      return "Unrecognized";
  }
}

/**
 * @brief @ref ConfigurationSource stream operator.
 * @ingroup fault_control_messages
 */
inline p1_ostream& operator<<(p1_ostream& stream, FaultType type) {
  stream << to_string(type) << " (" << (int)type << ")";
  return stream;
}

/**
 * @brief The type of COCOM limit to be applied.
 * @ingroup fault_control_messages
 */
enum class CoComType : uint8_t {
  /** Clear the current COCOM limit. */
  NONE = 0,
  /** Simulate a maximum acceleration limit. */
  ACCELERATION = 1,
  /** Simulate a maximum speed limit. */
  SPEED = 2,
  /** Simulate a maximum altitude limit. */
  ALTITUDE = 3,
};

/**
 * @brief Get a human-friendly string name for the specified @ref CoComType.
 * @ingroup fault_control_messages
 *
 * @param type The desired type.
 *
 * @return The corresponding string name.
 */
P1_CONSTEXPR_FUNC const char* to_string(CoComType type) {
  switch (type) {
    case CoComType::NONE:
      return "No Limit";
    case CoComType::ACCELERATION:
      return "Acceleration";
    case CoComType::SPEED:
      return "Speed";
    case CoComType::ALTITUDE:
      return "Altitude";
    default:
      return "Unrecognized";
  }
}

/**
 * @brief @ref CoComType stream operator.
 * @ingroup fault_control_messages
 */
inline p1_ostream& operator<<(p1_ostream& stream, CoComType type) {
  stream << to_string(type) << " (" << (int)type << ")";
  return stream;
}

/**
 * @brief Enable/disable a specified system fault (@ref
 *        MessageType::FAULT_CONTROL, version 1.0).
 * @ingroup fault_control_messages
 *
 * This message is followed by an `N`-byte payload. The size and format of the
 * payload are specified by the @ref fault_type. See @ref FaultType for details.
 * For example, a message with a `uint8_t` payload will be serialized as
 * follows:
 *
 * ```
 * {MessageHeader, FaultControlMessage, uint8_t}
 * ```
 *
 * # Expected Response
 * The device will respond with a @ref CommandResponseMessage indicating whether
 * or not the request succeeded.
 */
struct P1_ALIGNAS(4) FaultControlMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::FAULT_CONTROL;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The type of fault/control to be performed. */
  FaultType fault_type = FaultType::CLEAR_ALL;

  uint8_t reserved[15] = {0};

  /** The size of the payload (in bytes). */
  uint32_t payload_length_bytes = 0;

  // uint8_t payload[N];
};

#pragma pack(pop)

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
