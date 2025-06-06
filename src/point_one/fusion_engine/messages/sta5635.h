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
 * @brief A command to be sent to an attached STA5635 RF front-end. (@ref
 *        MessageType::STA5635_COMMAND, version 1.0).
 * @ingroup sta5635
 *
 * See the STA5635 data sheet for the allowed command, address, and data values.
 */
struct P1_ALIGNAS(4) STA5635Command : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::STA5635_COMMAND;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /** The STA5635 command code to be issued. */
  uint8_t command = 0;
  /** The address of the STA5635 register to be accessed. */
  uint8_t address = 0;
  /**
   * The value to be sent to the device, where `data[0]` contains the MSB.
   */
  uint8_t data[2] = {0};
};

/**
 * @brief Result from an STA5635 sent in response to an @ref STA5635Command.
 *        (@ref MessageType::STA5635_COMMAND_RESPONSE, version 1.0).
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
  /**
   * The sequence number contained in the @ref STA5635Command to which this
   * response belongs.
   */
  uint32_t command_sequence_number = 0;
  /**
   * The response from the device, where `data[0]` contains the first byte in
   * the response.
   */
  uint8_t data[4] = {0};
};

/**
 * @brief IQ sample data from an STA5635
 *        (@ref MessageType::STA5635_IQ_DATA, version 1.0).
 * @ingroup sta5635
 * @note
 * The rest of this message contains the wrapped payload data. The size of
 * the data is found by subtracting the size of the other fields in this
 * message from the header `payload_size_bytes` (i.e. `size_t content_size =
 * header->payload_size_bytes - sizeof(STA5635IQData)`).
 */
struct P1_ALIGNAS(4) STA5635IQData : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::STA5635_IQ_DATA;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  uint8_t reserved[4] = {0};
};

#pragma pack(pop)

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
