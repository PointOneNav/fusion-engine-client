/**************************************************************************/ /**
 * @brief Device-specific messages.
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

struct alignas(4) SystemStatusMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::SYSTEM_STATUS;
  static constexpr uint8_t MESSAGE_VERSION = 0;
  static constexpr int16_t INVALID_TEMPERATURE = INT16_MIN;

  /** The time of the message, in P1 time (beginning at power-on). */
  Timestamp p1_time;

  /**
   * The temperature of the GNSS receiver.
   *
   * Stored in units of 1/8 degrees Celsius: `gnss_temperature_degc =
   * gnss_temperature * 1/8`. Set to `-32768` if invalid.
   */
  int16_t gnss_temperature = INVALID_TEMPERATURE;

  uint8_t reserved[131] = {0};
};

#pragma pack(pop)

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
