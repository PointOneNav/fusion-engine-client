/**************************************************************************/ /**
 * @brief Uart to ST5365 and back messages.
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
 * @defgroup uart_spi Uart to/from SPI messages
 * @brief Messages for sending/receiving control messages to/from the ST5635
 * @ingroup device_control
 *
 * TODO PUT something here
 *
 * See also @ref messages.
 */

/**************************************************************************/ /**
 * @defgroup device_control Device Control Messages
 * @brief Messages for high-level device control (reset, shutdown, etc.).
 * @ingroup config_and_ctrl_messages
 ******************************************************************************/

/**
 * @brief Response to indicate if command was processed successfully (@ref
 *        MessageType::COMMAND_RESPONSE, version 1.0).
 * @ingroup device_control
 */
        struct P1_ALIGNAS(4) SpiCmdResponse : public MessagePayload {
            static constexpr MessageType MESSAGE_TYPE = MessageType::SPI_CMD_RESPONSE;
            static constexpr uint8_t MESSAGE_VERSION = 0;

            int64_t system_time_ns = 0;
            uint8_t data_0 = 0;
            uint8_t data_1 = 0;
            uint8_t data_2 = 0;
            uint8_t data_3 = 0;

        };

/**
 * @brief Request transmission of a specified message type, (@ref
 *        MessageType::MESSAGE_REQUEST, version 1.0).
 * @ingroup device_control
 *
 * On success, the device will output the requested message type.
 *
 * Not all message types may be requested explicitly. If a message type cannot
 * be requested on demand or is not supported, the device will respond with a
 * @ref Response::UNSUPPORTED_FEATURE message.
 *
 * @note
 * The generated response may not immediately follow the request if other
 * outbound messages are already enqueued to be sent.
 *
 * # Expected Response
 * The requested message type, or @ref CommandResponseMessage on error.
 */
//            struct P1_ALIGNAS(4) MessageRequest : public MessagePayload {
//                static constexpr MessageType MESSAGE_TYPE = MessageType::MESSAGE_REQUEST;
//                static constexpr uint8_t MESSAGE_VERSION = 0;
//
//                /** The desired message type. */
//                MessageType message_type = MessageType::INVALID;
//
//                uint8_t reserved[2] = {0};
//            };



/**
 * @brief Perform a device shutdown (@ref
 *        MessageType::SHUTDOWN_REQUEST, version 1.0).
 * @ingroup device_control
 *
 * # Expected Response
 * The device will respond with a @ref CommandResponseMessage indicating whether
 * or not the request succeeded.
 */
            struct P1_ALIGNAS(4) SpiCmd : public MessagePayload {
                static constexpr MessageType MESSAGE_TYPE = MessageType::SPI_CMD;
                static constexpr uint8_t MESSAGE_VERSION = 0;

                uint8_t cmd = 0;
                uint8_t address = 0;
                uint8_t val1 = 0;
                uint8_t val2 = 0;
            };



        struct P1_ALIGNAS(4) SpiLbandPacket : public MessagePayload {
            static constexpr MessageType MESSAGE_TYPE = MessageType::SPI_LBAND_PACKET;
            static constexpr uint8_t MESSAGE_VERSION = 0;
            uint32_t msg_counter;
            uint8_t packet[260];
        };



#pragma pack(pop)

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
