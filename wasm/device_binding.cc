/**************************************************************************/ /**
 * @brief Emscripten bindings for structs in configuration.h.
 ******************************************************************************/

#include <emscripten/bind.h>
#include <emscripten/emscripten.h>

#include <point_one/fusion_engine/messages/core.h>

#include "binding_utils.h"

using namespace emscripten;
using namespace point_one::fusion_engine::messages;

/******************************************************************************/
EMSCRIPTEN_BINDINGS(device) {
  static auto SystemStatusMessage_MESSAGE_TYPE =
      SystemStatusMessage::MESSAGE_TYPE;
  static auto SystemStatusMessage_MESSAGE_VERSION =
      SystemStatusMessage::MESSAGE_VERSION;
  static auto SystemStatusMessage_INVALID_TEMPERATURE =
      SystemStatusMessage::INVALID_TEMPERATURE;
  class_<SystemStatusMessage>("SystemStatusMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &SystemStatusMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &SystemStatusMessage_MESSAGE_VERSION)
      .class_property("INVALID_TEMPERATURE",
                      &SystemStatusMessage_INVALID_TEMPERATURE)
      .property("p1_time", &SystemStatusMessage::p1_time)
      .property("gnss_temperature", &SystemStatusMessage::gnss_temperature)
      .ARRAY_PROPERTY(SystemStatusMessage, reserved)
      .STRUCT_FUNCTIONS(SystemStatusMessage);
}
