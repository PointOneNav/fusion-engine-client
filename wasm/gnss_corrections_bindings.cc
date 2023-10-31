/**************************************************************************/ /**
 * @brief Emscripten bindings for structs in gnss_corrections.h.
 ******************************************************************************/

#include <emscripten/bind.h>
#include <emscripten/emscripten.h>

#include <point_one/fusion_engine/messages/core.h>

#include "binding_utils.h"

using namespace emscripten;
using namespace point_one::fusion_engine::messages;

/******************************************************************************/

EMSCRIPTEN_BINDINGS(gnss) {
  static auto LBandFrameMessage_MESSAGE_TYPE =
      LBandFrameMessage::MESSAGE_TYPE;
  static auto LBandFrameMessage_MESSAGE_VERSION =
      LBandFrameMessage::MESSAGE_VERSION;
  class_<LBandFrameMessage>("LBandFrameMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &LBandFrameMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &LBandFrameMessage_MESSAGE_VERSION)
      .property("system_time_ns", &LBandFrameMessage::system_time_ns)
      .property("user_data_size_bytes", &LBandFrameMessage::user_data_size_bytes)
      .property("bit_error_count", &LBandFrameMessage::bit_error_count)
      .property("signal_power_db", &LBandFrameMessage::signal_power_db)
      .ARRAY_PROPERTY(LBandFrameMessage, reserved)
      .property("payload_length_bytes", &LBandFrameMessage::doppler_hz)
      .STRUCT_FUNCTIONS(LBandFrameMessage);

}
