/**************************************************************************/ /**
 * @brief Message CRC support.
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
 * @brief Calculate the CRC for the specified message.
 *
 * @pre
 * The supplied `header` must be followed in memory by a valid payload.
 *
 * @param header The message header.
 *
 * @return The calculated CRC value.
 */
P1_EXPORT uint32_t CalculateCRC(const MessageHeader& header);

/**
 * @brief Calculate the CRC for the message contained in the buffer.
 *
 * @param buffer A byte buffer containing a @ref MessageHeader and payload.
 *
 * @return The calculated CRC value.
 */
inline uint32_t CalculateCRC(const void* buffer) {
  return CalculateCRC(*static_cast<const MessageHeader*>(buffer));
}

/**
 * @brief Check if the specified message has a valid CRC.
 *
 * @param header The message header.
 *
 * @return `true` if the CRC value in the header matches the CRC computed from
 *         the current contents.
 */
inline bool IsValid(const MessageHeader& header) {
  return header.crc == CalculateCRC(header);
}

/**
 * @brief Check if the message contained in the buffer has a valid CRC.
 *
 * @param buffer A byte buffer containing a @ref MessageHeader and payload.
 *
 * @return `true` if the CRC value in the header matches the CRC computed from
 *         the current contents.
 */
inline bool IsValid(const void* buffer) {
  return static_cast<const MessageHeader*>(buffer)->crc == CalculateCRC(buffer);
}

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
