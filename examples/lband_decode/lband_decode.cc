/**************************************************************************/ /**
* @brief Example of decoding FusionEngine messages from a recorded file.
* @file
******************************************************************************/

#include <cstdint>
#include <cstdio>

#include <point_one/fusion_engine/messages/gnss_corrections.h>
#include <point_one/fusion_engine/parsers/fusion_engine_framer.h>

using namespace point_one::fusion_engine::messages;
using namespace point_one::fusion_engine::parsers;

/******************************************************************************/
class LbandDecoder {
 public:
  using LbandCallback =
      std::function<void(const uint8_t* lband_data, size_t lband_data_size)>;

  /**
   * @brief Process FusionEngine data and callback for any L-band frames
   *        decoded.
   *
   * @param fe_input_data A buffer containing data to be framed.
   * @param fe_input_data_size The number of bytes to be framed.
   */
  void ProcessFEInput(const uint8_t* fe_input_data, size_t fe_input_data_size) {
    auto callback = this->callback_;
    framer_.SetMessageCallback([callback](const MessageHeader& header,
                                          const void* data) {
      if (callback != nullptr &&
          header.message_type == LBandFrameMessage::MESSAGE_TYPE) {
        auto frame = reinterpret_cast<const LBandFrameMessage*>(data);
        auto lband_data =
            reinterpret_cast<const uint8_t*>(data) + sizeof(LBandFrameMessage);
        callback(lband_data, frame->user_data_size_bytes);
      }
    });
    framer_.OnData(fe_input_data, fe_input_data_size);
  }

  /**
   * @brief Specify a function to be called when L-band data is framed.
   *
   * @param callback The function to be called with the message payload.
   */
  void SetMessageCallback(LbandCallback callback) { callback_ = callback; }

 private:
  static constexpr size_t FRAMER_BUFFER_BYTES = 1024;
  FusionEngineFramer framer_ = FusionEngineFramer(FRAMER_BUFFER_BYTES);
  LbandCallback callback_ = nullptr;
};

/******************************************************************************/
int main(int argc, const char* argv[]) {
  if (argc != 2) {
    printf("Usage: %s FILE\n", argv[0]);
    printf(R"EOF(
Decode L-band corrections and write contents to "lband.bin".
)EOF");
    return 0;
  }

  FILE* out_fptr = fopen("lband.bin", "wb");

  LbandDecoder decoder;
  // Set a callback to handle the decoded L-band data.
  decoder.SetMessageCallback(
      [out_fptr](const uint8_t* lband_data, size_t lband_data_size) {
        printf("Decoded %ld L-band bytes.\n", lband_data_size);
        fwrite(lband_data, 1, lband_data_size, out_fptr);
      });

  FILE* in_fptr = fopen(argv[1], "rb");
  if (in_fptr == nullptr) {
    printf("Error opening file '%s'.\n", argv[1]);
    return 1;
  }

  uint8_t buffer[2048];

  while (true) {
    size_t read_size = fread(buffer, 1, sizeof(buffer), in_fptr);
    // Feed the FusionEngine data into the decoder.
    decoder.ProcessFEInput(buffer, read_size);
    if (read_size < sizeof(buffer)) {
      break;
    }
  }

  // Close the file.
  fclose(in_fptr);
  fclose(out_fptr);
  return 0;
}
