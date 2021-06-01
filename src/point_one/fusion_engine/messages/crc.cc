/**************************************************************************/ /**
 * @brief Utility functions.
 * @file
 ******************************************************************************/

#include <cstddef> // For offsetof()

#include "point_one/fusion_engine/messages/crc.h"

namespace {

/******************************************************************************/
const uint32_t* GetCRCTable() {
  // Note: This is the CRC-32 polynomial.
  static constexpr uint32_t polynomial = 0xEDB88320;

  static bool is_initialized = false;
  static uint32_t crc_table[256];

  if (!is_initialized) {
    for (uint32_t i = 0; i < 256; i++) {
      uint32_t c = i;
      for (size_t j = 0; j < 8; j++) {
        if (c & 1) {
          c = polynomial ^ (c >> 1);
        } else {
          c >>= 1;
        }
      }
      crc_table[i] = c;
    }

    is_initialized = true;
  }

  return crc_table;
}

/******************************************************************************/
uint32_t CalculateCRC(const void* buffer, size_t length,
                      uint32_t initial_value = 0) {
  static const uint32_t* crc_table = GetCRCTable();
  uint32_t c = initial_value ^ 0xFFFFFFFF;
  const uint8_t* u = static_cast<const uint8_t*>(buffer);
  for (size_t i = 0; i < length; ++i) {
    c = crc_table[(c ^ u[i]) & 0xFF] ^ (c >> 8);
  }
  return c ^ 0xFFFFFFFF;
}
} // namespace

namespace point_one {
namespace fusion_engine {
namespace messages {

/******************************************************************************/
uint32_t CalculateCRC(const void* buffer) {
  static constexpr size_t offset = offsetof(MessageHeader, protocol_version);
  const MessageHeader& header = *static_cast<const MessageHeader*>(buffer);
  size_t size_bytes =
      (sizeof(MessageHeader) - offset) + header.payload_size_bytes;
  return ::CalculateCRC(reinterpret_cast<const uint8_t*>(&header) + offset,
                        size_bytes);
}

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
