/**************************************************************************/ /**
* @brief Message encode example.
* @file
******************************************************************************/

#include <cmath>
#include <cstdio>
#include <cstring>

#include <point_one/fusion_engine/messages/core.h>
#include <point_one/fusion_engine/messages/crc.h>
#include <point_one/fusion_engine/parsers/fusion_engine_framer.h>

#include "../common/print_message.h"

using namespace point_one::fusion_engine::examples;
using namespace point_one::fusion_engine::messages;
using namespace point_one::fusion_engine::parsers;

bool message_found = false;

// Enforce a 4-byte aligned address.
alignas(4) uint8_t storage[4096];

// Fake Send/Receive functions.
/******************************************************************************/
void SendData(void* data, size_t data_len_bytes) {}

/******************************************************************************/
size_t ReceiveData(uint8_t* buffer, size_t read_size) {
  static size_t offset = 0;
  if (offset + read_size < sizeof(storage)) {
    // We're using this data as if it were received from the device.
    memcpy(buffer, storage + offset, read_size);
    offset += read_size;
    return read_size;
  } else {
    return 0;
  }
}

/******************************************************************************/
int main(int argc, const char* argv[]) {
  if (argc != 1) {
    printf("Usage: %s\n", argv[0]);
    printf(R"EOF(
Simulate sending a version request, and parsing the response.
)EOF");
    return 0;
  }

  //////////////////////////////////////////////////////////////////////////////
  // Write a VersionInfoMessage request.
  //////////////////////////////////////////////////////////////////////////////

  uint8_t* buffer = storage;
  auto header = reinterpret_cast<MessageHeader*>(buffer);
  buffer += sizeof(MessageHeader);
  *header = MessageHeader();

  header->sequence_number = 0;
  header->message_type = MessageType::MESSAGE_REQUEST;
  header->payload_size_bytes = sizeof(MessageRequest);

  auto req_message = reinterpret_cast<MessageRequest*>(buffer);
  *req_message = MessageRequest();

  req_message->message_type = VersionInfoMessage::MESSAGE_TYPE;

  header->crc = CalculateCRC(storage);

  printf("Sending VersionInfoMessage request:\n  ");
  PrintHex(storage, sizeof(MessageHeader) + sizeof(MessageRequest));
  // This data would be sent over serial to the device.
  SendData(storage, sizeof(MessageHeader) + sizeof(MessageRequest));

  printf("\n");

  //////////////////////////////////////////////////////////////////////////////
  // Generate an example response of the data a device would send back.
  //////////////////////////////////////////////////////////////////////////////

  static constexpr char VERSION_STR[] = {'t', 'e', 's', 't'};

  // @ref ReceiveData will read data from `storage`.
  buffer = storage;
  header = reinterpret_cast<MessageHeader*>(buffer);
  buffer += sizeof(MessageHeader);
  *header = MessageHeader();

  header->sequence_number = 0;
  header->message_type = MessageType::VERSION_INFO;
  header->payload_size_bytes = sizeof(VersionInfoMessage) + sizeof(VERSION_STR);

  auto version_message = reinterpret_cast<VersionInfoMessage*>(buffer);
  *version_message = VersionInfoMessage();
  version_message->fw_version_length = sizeof(VERSION_STR);
  buffer += sizeof(VersionInfoMessage);

  char* version_str_ptr = reinterpret_cast<char*>(buffer);
  // NOTE: Not NULL terminated.
  memcpy(version_str_ptr, VERSION_STR, sizeof(VERSION_STR));

  header->crc = CalculateCRC(storage);

  //////////////////////////////////////////////////////////////////////////////
  // Receive example response.
  //////////////////////////////////////////////////////////////////////////////

  printf("Waiting for response\n");
  // In a real application, you'd need to do the bookkeeping to trigger a
  // timeout if no response is received after a couple seconds.
  bool has_timed_out = false;
  uint8_t read_buffer[10];

  FusionEngineFramer framer(1024);
  framer.SetMessageCallback(
      [](const MessageHeader& header, const void* payload) {
        // Ignore messages besides the expected response type.
        if (header.message_type == VersionInfoMessage::MESSAGE_TYPE) {
          PrintMessage(header, payload);
          message_found = true;
        }
      });

  while (!has_timed_out && !message_found) {
    size_t data_read = ReceiveData(read_buffer, sizeof(read_buffer));
    framer.OnData(read_buffer, data_read);
  }

  printf("Response received.\n");

  return 0;
}
