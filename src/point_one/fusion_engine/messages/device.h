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

/**
 * @defgroup device_status System Status Message Definitions
 * @brief Output messages containing device-specific status information.
 * @ingroup messages
 *
 * See also @ref messages.
 */

/**
 * @brief System status information (@ref
 *        MessageType::SYSTEM_STATUS, version 1.0).
 * @ingroup device_status
 *
 * @note
 * All data is timestamped using the Point One Time, which is a monotonic
 * timestamp referenced to the start of the device. Corresponding messages (@ref
 * SystemStatusMessage) may be associated using their @ref p1_time values.
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

#pragma pack(pop)

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
