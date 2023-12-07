/**************************************************************************/ /**
 * @brief Emscripten bindings for structs in defs.h.
 ******************************************************************************/

#include <emscripten/bind.h>
#include <emscripten/emscripten.h>

#include <point_one/fusion_engine/messages/core.h>
#include <point_one/fusion_engine/messages/crc.h>

#include "binding_utils.h"

using namespace emscripten;
using namespace point_one::fusion_engine::messages;

/******************************************************************************/
static void SetMessageCRC(const emscripten::val& buffer) {
  auto header = reinterpret_cast<MessageHeader*>(buffer.as<size_t>());
  header->crc = CalculateCRC(header);
}

/******************************************************************************/
static uint32_t CalculateMessageCRC(const emscripten::val& buffer) {
  auto header = reinterpret_cast<const MessageHeader*>(buffer.as<size_t>());
  return CalculateCRC(header);
}

/******************************************************************************/
EMSCRIPTEN_BINDINGS(defs) {
  enum_<MessageType>("MessageType")
      .value("INVALID", MessageType::INVALID)

      // Navigation solution messages.
      .value("POSE", MessageType::POSE)
      .value("GNSS_INFO", MessageType::GNSS_INFO)
      .value("GNSS_SATELLITE", MessageType::GNSS_SATELLITE)
      .value("POSE_AUX", MessageType::POSE_AUX)
      .value("CALIBRATION_STATUS", MessageType::CALIBRATION_STATUS)
      .value("RELATIVE_ENU_POSITION", MessageType::RELATIVE_ENU_POSITION)

       // Device status messages
       .value("SYSTEM_STATUS", MessageType::SYSTEM_STATUS)

      // Sensor measurement messages.
      .value("IMU_OUTPUT", MessageType::IMU_OUTPUT)
      .value("RAW_HEADING_OUTPUT", MessageType::RAW_HEADING_OUTPUT)
      .value("RAW_IMU_OUTPUT", MessageType::RAW_IMU_OUTPUT)
      .value("HEADING_OUTPUT", MessageType::HEADING_OUTPUT)
      .value("IMU_INPUT", MessageType::IMU_INPUT)


      // Vehicle measurement messages.
      .value("DEPRECATED_WHEEL_SPEED_MEASUREMENT", MessageType::DEPRECATED_WHEEL_SPEED_MEASUREMENT)
      .value("DEPRECATED_VEHICLE_SPEED_MEASUREMENT", MessageType::DEPRECATED_VEHICLE_SPEED_MEASUREMENT)

      .value("WHEEL_TICK_INPUT", MessageType::WHEEL_TICK_INPUT)
      .value("VEHICLE_TICK_INPUT", MessageType::VEHICLE_TICK_INPUT)
      .value("WHEEL_SPEED_INPUT", MessageType::WHEEL_SPEED_INPUT)
      .value("VEHICLE_SPEED_INPUT", MessageType::VEHICLE_SPEED_INPUT)

      .value("RAW_WHEEL_TICK_OUTPUT", MessageType::RAW_WHEEL_TICK_OUTPUT)
      .value("RAW_VEHICLE_TICK_OUTPUT", MessageType::RAW_VEHICLE_TICK_OUTPUT)
      .value("RAW_WHEEL_SPEED_OUTPUT", MessageType::RAW_WHEEL_SPEED_OUTPUT)
      .value("RAW_VEHICLE_SPEED_OUTPUT", MessageType::RAW_VEHICLE_SPEED_OUTPUT)

      .value("WHEEL_SPEED_OUTPUT", MessageType::WHEEL_SPEED_OUTPUT)
      .value("VEHICLE_SPEED_OUTPUT", MessageType::VEHICLE_SPEED_OUTPUT)

      // ROS messages.
      .value("ROS_POSE", MessageType::ROS_POSE)
      .value("ROS_GPS_FIX", MessageType::ROS_GPS_FIX)
      .value("ROS_IMU", MessageType::ROS_IMU)

      // Command and control messages.
      .value("COMMAND_RESPONSE", MessageType::COMMAND_RESPONSE)
      .value("MESSAGE_REQUEST", MessageType::MESSAGE_REQUEST)
      .value("RESET_REQUEST", MessageType::RESET_REQUEST)
      .value("VERSION_INFO", MessageType::VERSION_INFO)
      .value("EVENT_NOTIFICATION", MessageType::EVENT_NOTIFICATION)
      .value("SHUTDOWN_REQUEST", MessageType::SHUTDOWN_REQUEST)
      .value("FAULT_CONTROL", MessageType::FAULT_CONTROL)
      .value("DEVICE_ID", MessageType::DEVICE_ID)
      .value("STARTUP_REQUEST", MessageType::STARTUP_REQUEST)

      .value("SET_CONFIG", MessageType::SET_CONFIG)
      .value("GET_CONFIG", MessageType::GET_CONFIG)
      .value("SAVE_CONFIG", MessageType::SAVE_CONFIG)
      .value("CONFIG_RESPONSE", MessageType::CONFIG_RESPONSE)

      .value("IMPORT_DATA", MessageType::IMPORT_DATA)
      .value("EXPORT_DATA", MessageType::EXPORT_DATA)
      .value("PLATFORM_STORAGE_DATA", MessageType::PLATFORM_STORAGE_DATA)

      .value("SET_MESSAGE_RATE", MessageType::SET_MESSAGE_RATE)
      .value("GET_MESSAGE_RATE", MessageType::GET_MESSAGE_RATE)
      .value("MESSAGE_RATE_RESPONSE", MessageType::MESSAGE_RATE_RESPONSE)
      .value("SUPPORTED_IO_INTERFACES", MessageType::SUPPORTED_IO_INTERFACES)

      .value("LBAND_FRAME", MessageType::LBAND_FRAME);

  enum_<Response>("Response")
      .value("OK", Response::OK)
      .value("UNSUPPORTED_CMD_VERSION", Response::UNSUPPORTED_CMD_VERSION)
      .value("UNSUPPORTED_FEATURE", Response::UNSUPPORTED_FEATURE)
      .value("VALUE_ERROR", Response::VALUE_ERROR)
      .value("INSUFFICIENT_SPACE", Response::INSUFFICIENT_SPACE)
      .value("EXECUTION_FAILURE", Response::EXECUTION_FAILURE)
      .value("INCONSISTENT_PAYLOAD_LENGTH",
             Response::INCONSISTENT_PAYLOAD_LENGTH)
      .value("DATA_CORRUPTED", Response::DATA_CORRUPTED)
      .value("NO_DATA_STORED", Response::NO_DATA_STORED)
      .value("UNAVAILABLE", Response::UNAVAILABLE);

  enum_<SolutionType>("SolutionType")
      .value("Invalid", SolutionType::Invalid)
      .value("AutonomousGPS", SolutionType::AutonomousGPS)
      .value("DGPS", SolutionType::DGPS)
      .value("RTKFixed", SolutionType::RTKFixed)
      .value("RTKFloat", SolutionType::RTKFloat)
      .value("Integrate", SolutionType::Integrate)
      .value("Visual", SolutionType::Visual)
      .value("PPP", SolutionType::PPP);

  static auto Timestamp_INVALID = Timestamp::INVALID;
  class_<Timestamp>("Timestamp")
      .constructor<>()
      .class_property("INVALID", &Timestamp_INVALID)
      .property("seconds", &Timestamp::seconds)
      .property("fraction_ns", &Timestamp::fraction_ns)
      .function("GetValue", select_overload<double(const Timestamp&)>(
                                [](const Timestamp& timestamp) -> double {
                                  if (timestamp.seconds == Timestamp::INVALID) {
                                    return NAN;
                                  } else {
                                    return timestamp.seconds +
                                           timestamp.fraction_ns * 1e-9;
                                  }
                                }))
      .function("SetValue", select_overload<void(Timestamp&, double)>(
                                [](Timestamp& timestamp, double value_sec) {
                                  if (std::isnan(value_sec)) {
                                    timestamp.seconds = Timestamp::INVALID;
                                    timestamp.fraction_ns = Timestamp::INVALID;
                                  } else {
                                    timestamp.seconds = std::floor(value_sec);
                                    timestamp.fraction_ns = std::lround(
                                        (value_sec - timestamp.seconds) * 1e9);
                                  }
                                }))
      .STRUCT_FUNCTIONS(Timestamp);

  static auto MessageHeader_SYNC0 = MessageHeader::SYNC0;
  static auto MessageHeader_SYNC1 = MessageHeader::SYNC1;
  static auto MessageHeader_INVALID_SOURCE_ID =
      MessageHeader::INVALID_SOURCE_ID;
  class_<MessageHeader>("MessageHeader")
      .constructor<>()
      .class_property("SYNC0", &MessageHeader_SYNC0)
      .class_property("SYNC1", &MessageHeader_SYNC1)
      .class_property("INVALID_SOURCE_ID", &MessageHeader_INVALID_SOURCE_ID)
      .ARRAY_PROPERTY(MessageHeader, sync)
      .ARRAY_PROPERTY(MessageHeader, reserved)
      .property("crc", &MessageHeader::crc)
      .property("protocol_version", &MessageHeader::protocol_version)
      .property("message_version", &MessageHeader::message_version)
      .property("message_type", &MessageHeader::message_type)
      .property("sequence_number", &MessageHeader::sequence_number)
      .property("payload_size_bytes", &MessageHeader::payload_size_bytes)
      .property("source_identifier", &MessageHeader::source_identifier)
      .STRUCT_FUNCTIONS(MessageHeader)
      .function("GetMessageSize", select_overload<size_t(const MessageHeader&)>(
                                      [](const MessageHeader& message) {
                                        return sizeof(MessageHeader) +
                                               message.payload_size_bytes;
                                      }));

  function("SetCRC", &SetMessageCRC);
  function("CalculateCRC", &SetMessageCRC);
}
