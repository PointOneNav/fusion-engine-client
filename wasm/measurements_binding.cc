/**************************************************************************/ /**
 * @brief Emscripten bindings for structs in measurements.h.
 ******************************************************************************/

#include <emscripten/bind.h>
#include <emscripten/emscripten.h>

#include <point_one/fusion_engine/messages/core.h>

#include "binding_utils.h"

using namespace emscripten;
using namespace point_one::fusion_engine::messages;

/******************************************************************************/
EMSCRIPTEN_BINDINGS(measurements) {
  enum_<SensorDataSource>("SensorDataSource")
      .value("UNKNOWN", SensorDataSource::UNKNOWN)
      .value("INTERNAL", SensorDataSource::INTERNAL)
      .value("HARDWARE_IO", SensorDataSource::HARDWARE_IO)
      .value("CAN", SensorDataSource::CAN)
      .value("SERIAL", SensorDataSource::SERIAL)
      .value("NETWORK", SensorDataSource::NETWORK);

  enum_<SystemTimeSource>("SystemTimeSource")
      .value("INVALID", SystemTimeSource::INVALID)
      .value("P1_TIME", SystemTimeSource::P1_TIME)
      .value("TIMESTAMPED_ON_RECEPTION",
             SystemTimeSource::TIMESTAMPED_ON_RECEPTION)
      .value("SENDER_SYSTEM_TIME", SystemTimeSource::SENDER_SYSTEM_TIME)
      .value("GPS_TIME", SystemTimeSource::GPS_TIME);

  class_<MeasurementDetails>("MeasurementDetails")
      .constructor<>()
      .property("measurement_time", &MeasurementDetails::measurement_time)
      .property("measurement_time_source",
                &MeasurementDetails::measurement_time_source)
      .property("data_source", &MeasurementDetails::data_source)
      .ARRAY_PROPERTY(MeasurementDetails, reserved)
      .property("p1_time", &MeasurementDetails::p1_time)
      .STRUCT_FUNCTIONS(MeasurementDetails);

  static auto IMUOutput_MESSAGE_TYPE = IMUOutput::MESSAGE_TYPE;
  static auto IMUOutput_MESSAGE_VERSION = IMUOutput::MESSAGE_VERSION;
  class_<IMUOutput>("IMUOutput")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &IMUOutput_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &IMUOutput_MESSAGE_VERSION)
      .property("p1_time", &IMUOutput::p1_time)
      .ARRAY_PROPERTY(IMUOutput, accel_mps2)
      .ARRAY_PROPERTY(IMUOutput, accel_std_mps2)
      .ARRAY_PROPERTY(IMUOutput, gyro_rps)
      .ARRAY_PROPERTY(IMUOutput, gyro_std_rps)
      .STRUCT_FUNCTIONS(IMUOutput);

  static auto RawIMUOutput_MESSAGE_TYPE = RawIMUOutput::MESSAGE_TYPE;
  static auto RawIMUOutput_MESSAGE_VERSION = RawIMUOutput::MESSAGE_VERSION;
  class_<RawIMUOutput>("RawIMUOutput")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &RawIMUOutput_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &RawIMUOutput_MESSAGE_VERSION)
      .property("details", &RawIMUOutput::details)
      .ARRAY_PROPERTY(RawIMUOutput, reserved)
      .property("temperature", &RawIMUOutput::temperature)
      .ARRAY_PROPERTY(RawIMUOutput, accel)
      .ARRAY_PROPERTY(RawIMUOutput, gyro)
      .STRUCT_FUNCTIONS(RawIMUOutput);

  enum_<GearType>("GearType")
      .value("UNKNOWN", GearType::UNKNOWN)
      .value("FORWARD", GearType::FORWARD)
      .value("REVERSE", GearType::REVERSE)
      .value("PARK", GearType::PARK)
      .value("NEUTRAL", GearType::NEUTRAL);

  static auto WheelSpeedInput_MESSAGE_TYPE =  WheelSpeedInput::MESSAGE_TYPE;
  static auto WheelSpeedInput_MESSAGE_VERSION = WheelSpeedInput::MESSAGE_VERSION;
  static auto WheelSpeedInput_FLAG_SIGNED = WheelSpeedInput::FLAG_SIGNED;
  class_<WheelSpeedInput>("WheelSpeedInput")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &WheelSpeedInput_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &WheelSpeedInput_MESSAGE_VERSION)
      .property("details", &WheelSpeedInput::details)
      .property("front_left_speed",  &WheelSpeedInput::front_left_speed)
      .property("front_right_speed", &WheelSpeedInput::front_right_speed)
      .property("rear_left_speed", &WheelSpeedInput::rear_left_speed)
      .property("rear_right_speed", &WheelSpeedInput::rear_right_speed)
      .property("gear", &WheelSpeedInput::gear)
      .property("flags", &WheelSpeedInput::flags)
      .ARRAY_PROPERTY(WheelSpeedInput, reserved)
      .STRUCT_FUNCTIONS(WheelSpeedInput);

  static auto WheelSpeedOutput_MESSAGE_TYPE = WheelSpeedOutput::MESSAGE_TYPE;
  static auto WheelSpeedOutput_MESSAGE_VERSION = WheelSpeedOutput::MESSAGE_VERSION;
  static auto WheelSpeedOutput_FLAG_SIGNED = WheelSpeedOutput::FLAG_SIGNED;
  class_<WheelSpeedOutput>("WheelSpeedOutput")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &WheelSpeedOutput_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &WheelSpeedOutput_MESSAGE_VERSION)
      .property("p1_time", &WheelSpeedOutput::p1_time)
      .property("data_source", &WheelSpeedOutput::data_source)
      .property("gear", &WheelSpeedOutput::gear)
      .property("flags", &WheelSpeedOutput::flags)
      .property("reserved", &WheelSpeedOutput::reserved)
      .property("front_left_speed_mps", &WheelSpeedOutput::front_left_speed_mps)
      .property("front_right_speed_mps", &WheelSpeedOutput::front_right_speed_mps)
      .property("rear_left_speed_mps", &WheelSpeedOutput::rear_left_speed_mps)
      .property("rear_right_speed_mps", &WheelSpeedOutput::rear_right_speed_mps)
      .STRUCT_FUNCTIONS(WheelSpeedOutput);

  static auto RawWheelSpeedOutput_MESSAGE_TYPE = RawWheelSpeedOutput::MESSAGE_TYPE;
  static auto RawWheelSpeedOutput_MESSAGE_VERSION = RawWheelSpeedOutput::MESSAGE_VERSION;
  static auto RawWheelSpeedOutput_FLAG_SIGNED = RawWheelSpeedOutput::FLAG_SIGNED;
  class_<RawWheelSpeedOutput>("RawWheelSpeedOutput")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &RawWheelSpeedOutput_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &RawWheelSpeedOutput_MESSAGE_VERSION)
      .property("details", &RawWheelSpeedOutput::details)
      .property("front_left_speed", &RawWheelSpeedOutput::front_left_speed)
      .property("front_right_speed", &RawWheelSpeedOutput::front_right_speed)
      .property("rear_left_speed", &RawWheelSpeedOutput::rear_left_speed)
      .property("rear_right_speed", &RawWheelSpeedOutput::rear_right_speed)
      .property("gear", &RawWheelSpeedOutput::gear)
      .property("flags", &RawWheelSpeedOutput::flags)
      .ARRAY_PROPERTY(RawWheelSpeedOutput, reserved)
      .STRUCT_FUNCTIONS(RawWheelSpeedOutput);

  static auto VehicleSpeedInput_MESSAGE_TYPE =  VehicleSpeedInput::MESSAGE_TYPE;
  static auto VehicleSpeedInput_MESSAGE_VERSION = VehicleSpeedInput::MESSAGE_VERSION;
  static auto VehicleSpeedInput_FLAG_SIGNED = VehicleSpeedInput::FLAG_SIGNED;
  class_<VehicleSpeedInput>("VehicleSpeedInput")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &VehicleSpeedInput_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &VehicleSpeedInput_MESSAGE_VERSION)
      .property("details", &VehicleSpeedInput::details)
      .property("vehicle_speed", &VehicleSpeedInput::vehicle_speed)
      .property("gear", &VehicleSpeedInput::gear)
      .property("flags", &VehicleSpeedInput::flags)
      .ARRAY_PROPERTY(VehicleSpeedInput, reserved)
      .STRUCT_FUNCTIONS(VehicleSpeedInput);

  static auto DeprecatedWheelSpeedMeasurement_MESSAGE_TYPE = DeprecatedWheelSpeedMeasurement::MESSAGE_TYPE;
  static auto DeprecatedWheelSpeedMeasurement_MESSAGE_VERSION = DeprecatedWheelSpeedMeasurement::MESSAGE_VERSION;
  class_<DeprecatedWheelSpeedMeasurement>("DeprecatedWheelSpeedMeasurement")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &DeprecatedWheelSpeedMeasurement_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &DeprecatedWheelSpeedMeasurement_MESSAGE_VERSION)
      .property("details", &DeprecatedWheelSpeedMeasurement::details)
      .property("front_left_speed_mps", &DeprecatedWheelSpeedMeasurement::front_left_speed_mps)
      .property("front_right_speed_mps", &DeprecatedWheelSpeedMeasurement::front_right_speed_mps)
      .property("rear_left_speed_mps", &DeprecatedWheelSpeedMeasurement::rear_left_speed_mps)
      .property("rear_right_speed_mps",&DeprecatedWheelSpeedMeasurement::rear_right_speed_mps)
      .property("gear", &DeprecatedWheelSpeedMeasurement::gear)
      .property("is_signed", &DeprecatedWheelSpeedMeasurement::is_signed)
      .ARRAY_PROPERTY(DeprecatedWheelSpeedMeasurement, reserved)
      .STRUCT_FUNCTIONS(DeprecatedWheelSpeedMeasurement);

  static auto DeprecatedVehicleSpeedMeasurement_MESSAGE_TYPE =
      DeprecatedVehicleSpeedMeasurement::MESSAGE_TYPE;
  static auto DeprecatedVehicleSpeedMeasurement_MESSAGE_VERSION =
      DeprecatedVehicleSpeedMeasurement::MESSAGE_VERSION;
  class_<DeprecatedVehicleSpeedMeasurement>("DeprecatedVehicleSpeedMeasurement")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &DeprecatedVehicleSpeedMeasurement_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION",
                      &DeprecatedVehicleSpeedMeasurement_MESSAGE_VERSION)
      .property("details", &DeprecatedVehicleSpeedMeasurement::details)
      .property("vehicle_speed_mps",
                &DeprecatedVehicleSpeedMeasurement::vehicle_speed_mps)
      .property("gear", &DeprecatedVehicleSpeedMeasurement::gear)
      .property("is_signed", &DeprecatedVehicleSpeedMeasurement::is_signed)
      .ARRAY_PROPERTY(DeprecatedVehicleSpeedMeasurement, reserved)
      .STRUCT_FUNCTIONS(DeprecatedVehicleSpeedMeasurement);

  static auto HeadingMeasurement_MESSAGE_TYPE =
      HeadingMeasurement::MESSAGE_TYPE;
  static auto HeadingMeasurement_MESSAGE_VERSION =
      HeadingMeasurement::MESSAGE_VERSION;
  class_<HeadingMeasurement>("HeadingMeasurement")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &HeadingMeasurement_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &HeadingMeasurement_MESSAGE_VERSION)
      .property("details", &HeadingMeasurement::details)
      .property("solution_type", &HeadingMeasurement::solution_type)
      .ARRAY_PROPERTY(HeadingMeasurement, reserved)
      .property("flags", &HeadingMeasurement::flags)
      .ARRAY_PROPERTY(HeadingMeasurement, relative_position_enu_m)
      .ARRAY_PROPERTY(HeadingMeasurement, position_std_enu_m)
      .property("heading_true_north_deg",
                &HeadingMeasurement::heading_true_north_deg)
      .property("baseline_distance_m", &HeadingMeasurement::baseline_distance_m)
      .STRUCT_FUNCTIONS(HeadingMeasurement);
}
