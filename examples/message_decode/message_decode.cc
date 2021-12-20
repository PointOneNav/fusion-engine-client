/**************************************************************************/ /**
* @brief Example of decoding FusionEngine messages from a recorded file.
* @file
******************************************************************************/

#include <cstdint>
#include <cstdio>
#include <fstream>

#include <point_one/fusion_engine/messages/core.h>
#include <point_one/fusion_engine/messages/crc.h>

#include "../common/print_message.h"

using namespace point_one::fusion_engine::examples;
using namespace point_one::fusion_engine::messages;

/******************************************************************************/
bool DecodeMessage(std::ifstream& stream, size_t available_bytes) {
  static uint32_t expected_sequence_number = 0;

  // Enforce a 4-byte aligned address.
  alignas(4) uint8_t storage[4096];
  char* buffer = reinterpret_cast<char*>(storage);

  // Read the message header.
  if (available_bytes < sizeof(MessageHeader)) {
    printf("Not enough data: cannot read header. [%zu bytes < %zu bytes]\n",
           available_bytes, sizeof(MessageHeader));
    return false;
  }

  stream.read(buffer, sizeof(MessageHeader));
  if (!stream) {
    printf("Unexpected error reading header.\n");
    return false;
  }

  available_bytes -= sizeof(MessageHeader);

  auto& header = *reinterpret_cast<MessageHeader*>(buffer);
  buffer += sizeof(MessageHeader);

  // Read the message payload.
  if (available_bytes < header.payload_size_bytes) {
    printf("Not enough data: cannot read payload. [%zu bytes < %u bytes]\n",
           available_bytes, header.payload_size_bytes);
    return false;
  }

  stream.read(buffer, header.payload_size_bytes);
  if (!stream) {
    printf("Unexpected error reading payload.\n");
    return false;
  }

  // Verify the message checksum.
  size_t message_size = sizeof(MessageHeader) + header.payload_size_bytes;
  if (!IsValid(storage)) {
    printf(
        "CRC failure. [type=%s (%u), size=%zu bytes (payload size=%u bytes], "
        "sequence=%u, expected_crc=0x%08x, calculated_crc=0x%08x]\n",
        to_string(header.message_type),
        static_cast<unsigned>(header.message_type), message_size,
        header.payload_size_bytes, header.sequence_number, header.crc,
        CalculateCRC(storage));
    return false;
  }

  // Check that the sequence number increments as expected.
  if (header.sequence_number != expected_sequence_number) {
    printf(
        "Warning: unexpected sequence number. [type=%s (%u), size=%zu bytes "
        "(payload size=%u bytes], crc=0x%08x, expected_sequence=%u, "
        "received_sequence=%u]\n",
        to_string(header.message_type),
        static_cast<unsigned>(header.message_type), message_size,
        header.payload_size_bytes, header.crc, expected_sequence_number,
        header.sequence_number);
  }

  expected_sequence_number = header.sequence_number + 1;

  // Interpret the payload.
  PrintMessage(header, buffer);

  return true;
}

/******************************************************************************/
int main(int argc, const char* argv[]) {
  if (argc != 2) {
    printf("Usage: %s FILE\n", argv[0]);
    printf(R"EOF(
Decode platform pose messages from a binary file containing FusionEngine data.
)EOF");
    return 0;
  }

  // Open the file.
  std::ifstream stream(argv[1], std::ifstream::binary);
  if (!stream) {
    printf("Error opening file '%s'.\n", argv[1]);
    return 1;
  }

  // Determine the file size.
  stream.seekg(0, stream.end);
  std::streampos file_size_bytes = stream.tellg();
  stream.seekg(0, stream.beg);

  // Decode all messages in the file.
  int return_code = 0;
  while (stream.tellg() != file_size_bytes) {
    if (!DecodeMessage(stream,
                       static_cast<size_t>(file_size_bytes - stream.tellg()))) {
      return_code = 1;
      break;
    }
  }

  // Close the file.
  stream.close();

  return return_code;
}
