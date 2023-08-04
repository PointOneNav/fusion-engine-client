/**************************************************************************/ /**
* @brief Example of decoding FusionEngine messages from a recorded file.
* @file
******************************************************************************/

#include <cstdint>
#include <cstdio>
#include <fstream>

#include <point_one/fusion_engine/messages/gnss_corrections.h>
#include <point_one/fusion_engine/parsers/fusion_engine_framer.h>

using namespace point_one::fusion_engine::messages;
using namespace point_one::fusion_engine::parsers;

static std::ofstream out_stream;

// This is the callback for handling decoded FusionEngine messages.
/******************************************************************************/
void OnFEMessage(const MessageHeader& header, const void* data) {
  // If the FusionEngine message is L-band data, process its payload.
  if (header.message_type == LBandFrameMessage::MESSAGE_TYPE) {
    auto frame = reinterpret_cast<const LBandFrameMessage*>(data);
    auto lband_data =
        static_cast<const char*>(data) + sizeof(LBandFrameMessage);
    printf("Decoded %u L-band bytes.\n", frame->user_data_size_bytes);
    out_stream.write(lband_data, frame->user_data_size_bytes);
  }
}

/******************************************************************************/
int main(int argc, const char* argv[]) {
  if (argc != 2) {
    printf("Usage: %s FILE\n", argv[0]);
    printf("Decode L-band corrections and write contents to 'lband.bin'.");
    return 0;
  }

  char buffer[2048];
  static constexpr size_t FRAME_BUFFER_BYTES = 1024;
  FusionEngineFramer framer(FRAME_BUFFER_BYTES);

  std::ifstream in_stream(argv[1], std::ifstream::binary);
  if (!in_stream.is_open()) {
    printf("Error opening file '%s'.\n", argv[1]);
    return 1;
  }
  out_stream.open("lband.bin", std::ifstream::binary);
  if (!out_stream.is_open()) {
    printf("Error opening file 'lband.bin'.\n");
    return 1;
  }

  // Set a callback to handle the decoded L-band data.
  framer.SetMessageCallback(&OnFEMessage);

  while (true) {
    in_stream.read(buffer, sizeof(buffer));
    if (in_stream.eof()) {
      break;
    }

    // Feed the FusionEngine data into the decoder.
    framer.OnData(reinterpret_cast<uint8_t*>(buffer), sizeof(buffer));
  }

  return 0;
}
