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
EMSCRIPTEN_BINDINGS(control) {
  static auto CommandResponseMessage_MESSAGE_TYPE =
      CommandResponseMessage::MESSAGE_TYPE;
  static auto CommandResponseMessage_MESSAGE_VERSION =
      CommandResponseMessage::MESSAGE_VERSION;
  class_<CommandResponseMessage>("CommandResponseMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &CommandResponseMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION",
                      &CommandResponseMessage_MESSAGE_VERSION)
      .property("source_seq_number", &CommandResponseMessage::source_seq_number)
      .property("response", &CommandResponseMessage::response)
      .ARRAY_PROPERTY(CommandResponseMessage, reserved)
      .STRUCT_FUNCTIONS(CommandResponseMessage);

  static auto VersionInfoMessage_MESSAGE_TYPE =
      VersionInfoMessage::MESSAGE_TYPE;
  static auto VersionInfoMessage_MESSAGE_VERSION =
      VersionInfoMessage::MESSAGE_VERSION;
  class_<VersionInfoMessage>("VersionInfoMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &VersionInfoMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &VersionInfoMessage_MESSAGE_VERSION)
      .property("system_time_ns", &VersionInfoMessage::system_time_ns)
      .property("fw_version_length", &VersionInfoMessage::fw_version_length)
      .property("engine_version_length",
                &VersionInfoMessage::engine_version_length)
      .property("hw_version_length", &VersionInfoMessage::hw_version_length)
      .property("rx_version_length", &VersionInfoMessage::rx_version_length)
      .ARRAY_PROPERTY(VersionInfoMessage, reserved)
      .ARRAY_PROPERTY(VersionInfoMessage, fw_version_str)
      .STRUCT_FUNCTIONS(VersionInfoMessage);

  static auto ResetRequest_MESSAGE_TYPE = ResetRequest::MESSAGE_TYPE;
  static auto ResetRequest_MESSAGE_VERSION = ResetRequest::MESSAGE_VERSION;
  static auto ResetRequest_RESTART_NAVIGATION_ENGINE =
      ResetRequest::RESTART_NAVIGATION_ENGINE;
  static auto ResetRequest_RESET_GNSS_CORRECTIONS =
      ResetRequest::RESET_GNSS_CORRECTIONS;
  static auto ResetRequest_RESET_POSITION_DATA =
      ResetRequest::RESET_POSITION_DATA;
  static auto ResetRequest_RESET_EPHEMERIS = ResetRequest::RESET_EPHEMERIS;
  static auto ResetRequest_RESET_FAST_IMU_CORRECTIONS =
      ResetRequest::RESET_FAST_IMU_CORRECTIONS;
  static auto ResetRequest_RESET_NAVIGATION_ENGINE_DATA =
      ResetRequest::RESET_NAVIGATION_ENGINE_DATA;
  static auto ResetRequest_RESET_CALIBRATION_DATA =
      ResetRequest::RESET_CALIBRATION_DATA;
  static auto ResetRequest_RESET_CONFIG = ResetRequest::RESET_CONFIG;
  static auto ResetRequest_REBOOT_GNSS_MEASUREMENT_ENGINE =
      ResetRequest::REBOOT_GNSS_MEASUREMENT_ENGINE;
  static auto ResetRequest_REBOOT_NAVIGATION_PROCESSOR =
      ResetRequest::REBOOT_NAVIGATION_PROCESSOR;
  static auto ResetRequest_HOT_START = ResetRequest::HOT_START;
  static auto ResetRequest_WARM_START = ResetRequest::WARM_START;
  static auto ResetRequest_COLD_START = ResetRequest::COLD_START;
  static auto ResetRequest_FACTORY_RESET = ResetRequest::FACTORY_RESET;
  class_<ResetRequest>("ResetRequest")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &ResetRequest_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &ResetRequest_MESSAGE_VERSION)
      .class_property("RESTART_NAVIGATION_ENGINE",
                      &ResetRequest_RESTART_NAVIGATION_ENGINE)
      .class_property("RESET_GNSS_CORRECTIONS",
                      &ResetRequest_RESET_GNSS_CORRECTIONS)
      .class_property("RESET_POSITION_DATA", &ResetRequest_RESET_POSITION_DATA)
      .class_property("RESET_EPHEMERIS", &ResetRequest_RESET_EPHEMERIS)
      .class_property("RESET_FAST_IMU_CORRECTIONS",
                      &ResetRequest_RESET_FAST_IMU_CORRECTIONS)
      .class_property("RESET_NAVIGATION_ENGINE_DATA",
                      &ResetRequest_RESET_NAVIGATION_ENGINE_DATA)
      .class_property("RESET_CALIBRATION_DATA",
                      &ResetRequest_RESET_CALIBRATION_DATA)
      .class_property("RESET_CONFIG", &ResetRequest_RESET_CONFIG)
      .class_property("REBOOT_GNSS_MEASUREMENT_ENGINE",
                      &ResetRequest_REBOOT_GNSS_MEASUREMENT_ENGINE)
      .class_property("REBOOT_NAVIGATION_PROCESSOR",
                      &ResetRequest_REBOOT_NAVIGATION_PROCESSOR)
      .class_property("HOT_START", &ResetRequest_HOT_START)
      .class_property("WARM_START", &ResetRequest_WARM_START)
      .class_property("COLD_START", &ResetRequest_COLD_START)
      .class_property("FACTORY_RESET", &ResetRequest_FACTORY_RESET)
      .property("reset_mask", &ResetRequest::reset_mask)
      .STRUCT_FUNCTIONS(ResetRequest);

  static auto MessageRequest_MESSAGE_TYPE = MessageRequest::MESSAGE_TYPE;
  static auto MessageRequest_MESSAGE_VERSION = MessageRequest::MESSAGE_VERSION;
  class_<MessageRequest>("MessageRequest")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &MessageRequest_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &MessageRequest_MESSAGE_VERSION)
      .property("message_type", &MessageRequest::message_type)
      .ARRAY_PROPERTY(MessageRequest, reserved)
      .STRUCT_FUNCTIONS(MessageRequest);

  static auto EventNotificationMessage_MESSAGE_TYPE =
      EventNotificationMessage::MESSAGE_TYPE;
  static auto EventNotificationMessage_MESSAGE_VERSION =
      EventNotificationMessage::MESSAGE_VERSION;
  class_<EventNotificationMessage>("EventNotificationMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &EventNotificationMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION",
                      &EventNotificationMessage_MESSAGE_VERSION)
      .property("type", &EventNotificationMessage::type)
      .ARRAY_PROPERTY(EventNotificationMessage, reserved1)
      .property("system_time_ns", &EventNotificationMessage::system_time_ns)
      .property("event_flags", &EventNotificationMessage::event_flags)
      .property("event_description_len_bytes",
                &EventNotificationMessage::event_description_len_bytes)
      .ARRAY_PROPERTY(EventNotificationMessage, reserved2)
      .ARRAY_PROPERTY(EventNotificationMessage, event_description)
      .STRUCT_FUNCTIONS(EventNotificationMessage);

  enum_<EventNotificationMessage::EventType>("EventType")
      .value("LOG", EventNotificationMessage::EventType::LOG)
      .value("RESET", EventNotificationMessage::EventType::RESET)
      .value("CONFIG_CHANGE",
             EventNotificationMessage::EventType::CONFIG_CHANGE);

  static auto ShutdownRequest_MESSAGE_TYPE =
      ShutdownRequest::MESSAGE_TYPE;
  static auto ShutdownRequest_MESSAGE_VERSION =
      ShutdownRequest::MESSAGE_VERSION;
  class_<ShutdownRequest>("ShutdownRequest")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &ShutdownRequest_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &ShutdownRequest_MESSAGE_VERSION)
      .property("shutdown_flags", &ShutdownRequest::shutdown_flags)
      .ARRAY_PROPERTY(ShutdownRequest, reserved1)
      .STRUCT_FUNCTIONS(ShutdownRequest);
}
