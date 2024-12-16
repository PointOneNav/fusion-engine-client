/**************************************************************************/ /**
 * @brief Emscripten bindings for structs in fault_control.h.
 ******************************************************************************/

#include <emscripten/bind.h>
#include <emscripten/emscripten.h>

#include <point_one/fusion_engine/messages/core.h>

#include "binding_utils.h"

using namespace emscripten;
using namespace point_one::fusion_engine::messages;

/******************************************************************************/

EMSCRIPTEN_BINDINGS(fault) {
  enum_<FaultType>("FaultType")
      .value("CLEAR_ALL", FaultType::CLEAR_ALL)
      .value("CRASH", FaultType::CRASH)
      .value("FATAL_ERROR", FaultType::FATAL_ERROR)
      .value("COCOM", FaultType::COCOM)
      .value("ENABLE_GNSS", FaultType::ENABLE_GNSS)
      .value("REGION_BLACKOUT", FaultType::REGION_BLACKOUT)
      .value("QUECTEL_TEST", FaultType::QUECTEL_TEST);

  enum_<CoComType>("CoComType")
      .value("NONE", CoComType::NONE)
      .value("ACCELERATION", CoComType::ACCELERATION)
      .value("SPEED", CoComType::SPEED)
      .value("ALTITUDE", CoComType::ALTITUDE);

  static auto FaultControlMessage_MESSAGE_TYPE =
      FaultControlMessage::MESSAGE_TYPE;
  static auto FaultControlMessage_MESSAGE_VERSION =
      FaultControlMessage::MESSAGE_VERSION;
  class_<FaultControlMessage>("FaultControlMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &FaultControlMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &FaultControlMessage_MESSAGE_VERSION)
      .property("fault_type", &FaultControlMessage::fault_type)
      .ARRAY_PROPERTY(FaultControlMessage, reserved)
      .property("payload_length_bytes",
                &FaultControlMessage::payload_length_bytes)
      .STRUCT_FUNCTIONS(FaultControlMessage);
}
