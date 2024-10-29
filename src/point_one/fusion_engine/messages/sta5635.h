/**************************************************************************/ /**
 * @brief Command/control support for an attached STA5635 RF front-end.
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
 * @defgroup sta5635 STA5635 Command/Control Messages
 * @brief Messages for interacting with an attached STA5635 RF front-end device.
 * @ingroup device_control
 *
 * These messages are intended to be used only for devices with an
 * STMicroelectronics STA5635 RF front-end where direct user control of the
 * front-end is needed. This is not common and should not be used on most
 * platforms.
 *
 * For platforms using an STA5635, the device will output @ref LBandFrameMessage
 * containing I/Q samples from the RF front-end. The format and use of the I/Q
 * samples is platform-specific.
 *
 * See also @ref messages.
 ******************************************************************************/

/**
 * @brief Result from a STA5635 sent in response to an @ref STA5635Command (@ref
 *        MessageType::STA5635_COMMAND_RESPONSE, version 1.0).
 * @ingroup sta5635
 */
struct P1_ALIGNAS(4) STA5635CommandResponse : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE =
      MessageType::STA5635_COMMAND_RESPONSE;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * The system time when the response was received (in nanoseconds). Note that
   * this is not synchronized to P1 or GNSS time.
   */
  int64_t system_time_ns = 0;
  uint32_t sequence_number = 0;
  uint8_t data_0 = 0;
  uint8_t data_1 = 0;
  uint8_t data_2 = 0;
  uint8_t data_3 = 0;
};

/**
 * @brief A command to be sent to an attached STA5635 front end. (@ref
 *        MessageType::STA5635_COMMAND, version 1.0).
 * @ingroup sta5635
 */
struct P1_ALIGNAS(4) STA5635Command : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::STA5635_COMMAND;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * See the STA5635 data sheet for the values below can be.
   */
  uint8_t command = 0; // STA5635 command code
  uint8_t address = 0; // STA5635 register address
  uint8_t value_msb = 0; // STA5635 register value msb
  uint8_t value_lsb = 0; // STA5635 register value lsb
};

#pragma pack(pop)

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
