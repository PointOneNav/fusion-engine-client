/**************************************************************************/ /**
* @brief Example of decoding FusionEngine messages from a recorded file.
* @file
******************************************************************************/

#include <cstdint>
#include <cstdio>
#include <fstream>

#include <point_one/fusion_engine/messages/core.h>
#include <point_one/fusion_engine/parsers/fusion_engine_framer.h>

#include "../common/print_message.h"

using namespace point_one::fusion_engine::examples;
using namespace point_one::fusion_engine::messages;
using namespace point_one::fusion_engine::parsers;

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

  // Create a decoder and configure it to print when messaes arrive.
  FusionEngineFramer framer(MessageHeader::MAX_MESSAGE_SIZE_BYTES);
  framer.SetMessageCallback(PrintMessage);

  // Read the file in chunks and decode any messages that are found.
  uint8_t buffer[4096];
  while (!stream.eof()) {
    stream.read(reinterpret_cast<char*>(buffer), sizeof(buffer));
    size_t bytes_read = stream.gcount();
    framer.OnData(buffer, bytes_read);
  }

  // Close the file.
  stream.close();

  return 0;
}
