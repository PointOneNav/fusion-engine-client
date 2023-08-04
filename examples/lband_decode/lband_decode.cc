/**************************************************************************/ /**
* @brief Example of decoding FusionEngine messages from a recorded file.
* @file
******************************************************************************/

#include <cstdint>
#include <cstdio>
#include <fstream>

#include <point_one/fusion_engine/messages/gnss_corrections.h>
#include <point_one/fusion_engine/parsers/fusion_engine_framer.h>
#include <point_one/rtcm/rtcm_framer.h>

using namespace point_one::fusion_engine::messages;
using namespace point_one::fusion_engine::parsers;
using namespace point_one::rtcm;

static constexpr size_t READ_SIZE_BYTES = 1024;
// The max FE L-band message is (FE header + message) + 504 B.
static constexpr size_t FE_FRAMER_BUFFER_BYTES = 600;
// The max RTCM message size is (RTCM header) + 1023 B.
static constexpr size_t RTCM_FRAMER_BUFFER_BYTES = 1030;
static RTCMFramer rtcm_framer(RTCM_FRAMER_BUFFER_BYTES);

// This is the callback for handling decoded FusionEngine messages.
/******************************************************************************/
void OnFEMessage(const MessageHeader& header, const void* data) {
  // If the FusionEngine message is L-band data, process its payload.
  if (header.message_type == LBandFrameMessage::MESSAGE_TYPE) {
    auto frame = reinterpret_cast<const LBandFrameMessage*>(data);
    auto lband_data =
        static_cast<const uint8_t*>(data) + sizeof(LBandFrameMessage);
    printf("Decoded %u L-band bytes.\n", frame->user_data_size_bytes);
    rtcm_framer.OnData(lband_data, frame->user_data_size_bytes);
  }
}

// This is the callback for handling decoded RTCM messages.
/******************************************************************************/
void OnRTCMMessage(uint16_t message_type, const void* data, size_t data_len) {
  // Don't warn unused.
  (void)data;
  printf("Decoded RTCM message. [type=%hu, size=%zu B]\n", message_type,
         data_len);
}

/******************************************************************************/
int main(int argc, const char* argv[]) {
  if (argc != 2) {
    printf("Usage: %s FILE\n", argv[0]);
    printf("Decode L-band corrections and write contents to 'lband.bin'.");
    return 0;
  }

  char buffer[READ_SIZE_BYTES];
  FusionEngineFramer fe_framer(FE_FRAMER_BUFFER_BYTES);
  // Set a callback to handle the decoded L-band data.
  fe_framer.SetMessageCallback(&OnFEMessage);

  // Set a callback to handle the decoded RTCM in the decoded L-band data.
  rtcm_framer.SetMessageCallback(&OnRTCMMessage);

  std::ifstream in_stream(argv[1], std::ifstream::binary);
  if (!in_stream.is_open()) {
    printf("Error opening file '%s'.\n", argv[1]);
    return 1;
  }

  while (true) {
    in_stream.read(buffer, READ_SIZE_BYTES);
    if (in_stream.eof()) {
      break;
    }

    // Feed the FusionEngine data into the decoder.
    fe_framer.OnData(reinterpret_cast<uint8_t*>(buffer), sizeof(buffer));
  }
  printf("Decoded %u messages successfully and had %u decoding errors.\n",
         rtcm_framer.GetNumDecodedMessages(), rtcm_framer.GetNumErrors());

  return 0;
}
