/**************************************************************************/ /**
 * @brief Message CRC support.
 * @file
 ******************************************************************************/

#pragma once

#include <cstdint>
#include <string>

#include "point_one/fusion_engine/common/portability.h"
#include "point_one/fusion_engine/messages/defs.h"

namespace point_one {
namespace fusion_engine {
namespace messages {

/**
 * @defgroup crc_support CRC Calculation/Message Validation Support
 * @{
 */

/**
 * @brief Calculate the CRC for the message (header + payload) contained in the
 *        buffer.
 *
 * @param buffer A byte buffer containing a @ref MessageHeader and payload.
 *
 * @return The calculated CRC value.
 */
P1_EXPORT uint32_t CalculateCRC(const void* buffer);

/**
 * @brief Check if the message contained in the buffer has a valid CRC.
 *
 * @param buffer A byte buffer containing a @ref MessageHeader and payload.
 *
 * @return `true` if the CRC value in the header matches the CRC computed from
 *         the current contents.
 */
inline bool IsValid(const void* buffer) {
  // Sanity check the message payload length before calculating the CRC.
  const MessageHeader& header = *static_cast<const MessageHeader*>(buffer);
  if (sizeof(MessageHeader) + header.payload_size_bytes >
      MessageHeader::MAX_MESSAGE_SIZE_BYTES) {
    return false;
  } else {
    return header.crc == CalculateCRC(buffer);
  }
}

/** @} */

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
