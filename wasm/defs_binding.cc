/**************************************************************************/ /**
 * @brief Emscripten bindings for structs in defs.h.
 ******************************************************************************/

#include <emscripten/bind.h>
#include <emscripten/emscripten.h>

#include <point_one/fusion_engine/messages/core.h>

#include "binding_utils.h"

using namespace emscripten;
using namespace point_one::fusion_engine::messages;

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

      // Sensor measurement messages.
      .value("IMU_MEASUREMENT", MessageType::IMU_MEASUREMENT)

      // Vehicle measurement messages.
      .value("WHEEL_SPEED_MEASUREMENT", MessageType::WHEEL_SPEED_MEASUREMENT)
      .value("VEHICLE_SPEED_MEASUREMENT",
             MessageType::VEHICLE_SPEED_MEASUREMENT)
      .value("WHEEL_TICK_MEASUREMENT", MessageType::WHEEL_TICK_MEASUREMENT)
      .value("VEHICLE_TICK_MEASUREMENT", MessageType::VEHICLE_TICK_MEASUREMENT)

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

      .value("SET_CONFIG", MessageType::SET_CONFIG)
      .value("GET_CONFIG", MessageType::GET_CONFIG)
      .value("SAVE_CONFIG", MessageType::SAVE_CONFIG)
      .value("CONFIG_RESPONSE", MessageType::CONFIG_RESPONSE)

      .value("SET_OUTPUT_INTERFACE_CONFIG",
             MessageType::SET_OUTPUT_INTERFACE_CONFIG)
      .value("GET_OUTPUT_INTERFACE_CONFIG",
             MessageType::GET_OUTPUT_INTERFACE_CONFIG)
      .value("OUTPUT_INTERFACE_CONFIG_RESPONSE",
             MessageType::OUTPUT_INTERFACE_CONFIG_RESPONSE)

      .value("SET_OUTPUT_MESSAGE_RATE", MessageType::SET_OUTPUT_MESSAGE_RATE)
      .value("GET_OUTPUT_MESSAGE_RATE", MessageType::GET_OUTPUT_MESSAGE_RATE)
      .value("OUTPUT_MESSAGE_RATE_RESPONSE",
             MessageType::OUTPUT_MESSAGE_RATE_RESPONSE);

  enum_<SatelliteType>("SatelliteType")
      .value("UNKNOWN", SatelliteType::UNKNOWN)
      .value("GPS", SatelliteType::GPS)
      .value("GLONASS", SatelliteType::GLONASS)
      .value("LEO", SatelliteType::LEO)
      .value("GALILEO", SatelliteType::GALILEO)
      .value("BEIDOU", SatelliteType::BEIDOU)
      .value("QZSS", SatelliteType::QZSS)
      .value("MIXED", SatelliteType::MIXED)
      .value("SBAS", SatelliteType::SBAS)
      .value("IRNSS", SatelliteType::IRNSS);

  enum_<Response>("Response")
      .value("OK", Response::OK)
      .value("UNSUPPORTED_CMD_VERSION", Response::UNSUPPORTED_CMD_VERSION)
      .value("UNSUPPORTED_FEATURE", Response::UNSUPPORTED_FEATURE)
      .value("VALUE_ERROR", Response::VALUE_ERROR)
      .value("INSUFFICIENT_SPACE", Response::INSUFFICIENT_SPACE)
      .value("EXECUTION_FAILURE", Response::EXECUTION_FAILURE)
      .value("INCONSISTENT_PAYLOAD_LENGTH",
             Response::INCONSISTENT_PAYLOAD_LENGTH)
      .value("DATA_CORRUPTED", Response::DATA_CORRUPTED);

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
      .PARSE_FUNCTION(Timestamp);

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
      .PARSE_FUNCTION(MessageHeader);
}
