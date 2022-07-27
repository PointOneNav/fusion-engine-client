/**************************************************************************/ /**
 * @brief Emscripten bindings for the FusionEngineFramer class.
 ******************************************************************************/

#include <emscripten/bind.h>
#include <emscripten/emscripten.h>

#include <point_one/fusion_engine/parsers/fusion_engine_framer.h>

using namespace emscripten;
using namespace point_one::fusion_engine::messages;
using namespace point_one::fusion_engine::parsers;

/******************************************************************************/
static void RegisterCallback(FusionEngineFramer& framer,
                             const emscripten::val& callback) {
  // Note: We are intentionally capturing 'func' by value here so that the
  // lambda keeps a reference to the caller's function. Otherwise it'll get
  // destroyed as soon as this function returns..
  framer.SetMessageCallback(
      [callback](const MessageHeader& header, const void* payload) {
        // Create a memory view (i.e., JS Uint8Array) on top of the FusionEngine
        // message header + payload. In JS, the callback will be called with the
        // following arguments:
        // 1. A reference to the MessageHeader struct
        // 2. A Uint8Array containing the message payload
        // 3. A Uint8Array containing the complete message (header + payload)
        //
        // For example:
        //   function Callback(header, payload, buffer) {
        //     // header is a FusionEngine.MessageHeader object
        //     // ArrayBuffer.isView(payload) returns true
        //     // ArrayBuffer.isView(buffer) returns true
        //   }
        val full_message_view(
            typed_memory_view(sizeof(MessageHeader) + header.payload_size_bytes,
                              reinterpret_cast<const uint8_t*>(&header)));
        val payload_view(typed_memory_view(
            header.payload_size_bytes, static_cast<const uint8_t*>(payload)));
        callback(header, payload_view, full_message_view);
      });
}

/******************************************************************************/
static size_t OnData(FusionEngineFramer& framer, const emscripten::val& buffer,
                     size_t size_bytes) {
  // Embind passes JS buffers addresses in as val objects. Val cannot be cast
  // directly to a raw pointer, so we cast first to size_t. To pass in data from
  // JS, do the following:
  //   let ptr = Module._malloc(128);
  //   let buffer = MyLib.HEAPU8.subarray(ptr, ptr + 128);
  //   framer.OnData(buffer.byteOffset, buffer.length);
  //   Module._free(ptr);
  return framer.OnData(reinterpret_cast<const uint8_t*>(buffer.as<size_t>()),
                       size_bytes);
}

/******************************************************************************/
EMSCRIPTEN_BINDINGS(framer) {
  class_<FusionEngineFramer>("FusionEngineFramer")
    .constructor<size_t>()
    .function("WarnOnError", &FusionEngineFramer::WarnOnError)
    .function("SetMessageCallback", &RegisterCallback)
    .function("Reset", &FusionEngineFramer::Reset)
    .function("OnData", &OnData)
    ;
}
