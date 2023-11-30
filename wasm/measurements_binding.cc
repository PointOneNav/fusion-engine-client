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
      .REF_TO(MeasurementDetails, p1_time)
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
      .class_property("FLAG_SIGNED", &WheelSpeedInput_FLAG_SIGNED)
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
      .class_property("FLAG_SIGNED", &WheelSpeedOutput_FLAG_SIGNED)
      .property("p1_time", &WheelSpeedOutput::p1_time)
      .REF_TO(WheelSpeedOutput, p1_time)
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
      .class_property("FLAG_SIGNED", &RawWheelSpeedOutput_FLAG_SIGNED)
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
      .class_property("FLAG_SIGNED", &VehicleSpeedInput_FLAG_SIGNED)
      .property("details", &VehicleSpeedInput::details)
      .property("vehicle_speed", &VehicleSpeedInput::vehicle_speed)
      .property("gear", &VehicleSpeedInput::gear)
      .property("flags", &VehicleSpeedInput::flags)
      .ARRAY_PROPERTY(VehicleSpeedInput, reserved)
      .STRUCT_FUNCTIONS(VehicleSpeedInput);

  static auto VehicleSpeedOutput_MESSAGE_TYPE = VehicleSpeedOutput::MESSAGE_TYPE;
  static auto VehicleSpeedOutput_MESSAGE_VERSION = VehicleSpeedOutput::MESSAGE_VERSION;
  static auto VehicleSpeedOutput_FLAG_SIGNED = VehicleSpeedOutput::FLAG_SIGNED;
  class_<VehicleSpeedOutput>("VehicleSpeedOutput")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &VehicleSpeedOutput_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &VehicleSpeedOutput_MESSAGE_VERSION)
      .class_property("FLAG_SIGNED", &VehicleSpeedOutput_FLAG_SIGNED)
      .property("p1_time", &VehicleSpeedOutput::p1_time)
      .REF_TO(VehicleSpeedOutput, p1_time)
      .property("data_source", &VehicleSpeedOutput::data_source)
      .property("gear", &VehicleSpeedOutput::gear)
      .property("flags", &VehicleSpeedOutput::flags)
      .property("reserved", &VehicleSpeedOutput::reserved)
      .property("vehicle_speed_mps", &VehicleSpeedOutput::vehicle_speed_mps)
      .STRUCT_FUNCTIONS(VehicleSpeedOutput);

  static auto RawVehicleSpeedOutput_MESSAGE_TYPE = RawVehicleSpeedOutput::MESSAGE_TYPE;
  static auto RawVehicleSpeedOutput_MESSAGE_VERSION = RawVehicleSpeedOutput::MESSAGE_VERSION;
  static auto RawVehicleSpeedOutput_FLAG_SIGNED = RawVehicleSpeedOutput::FLAG_SIGNED;
  class_<RawVehicleSpeedOutput>("RawVehicleSpeedOutput")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &RawVehicleSpeedOutput_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &RawVehicleSpeedOutput_MESSAGE_VERSION)
      .class_property("FLAG_SIGNED", &RawVehicleSpeedOutput_FLAG_SIGNED)
      .property("details", &RawVehicleSpeedOutput::details)
      .property("vehicle_speed", &RawVehicleSpeedOutput::vehicle_speed)
      .property("gear", &RawVehicleSpeedOutput::gear)
      .property("flags", &RawVehicleSpeedOutput::flags)
      .ARRAY_PROPERTY(RawVehicleSpeedOutput, reserved)
      .STRUCT_FUNCTIONS(RawVehicleSpeedOutput);

  static auto WheelTickInput_MESSAGE_TYPE =  WheelTickInput::MESSAGE_TYPE;
  static auto WheelTickInput_MESSAGE_VERSION = WheelTickInput::MESSAGE_VERSION;
  class_<WheelTickInput>("WheelTickInput")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &WheelTickInput_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &WheelTickInput_MESSAGE_VERSION)
      .property("details", &WheelTickInput::details)
      .property("front_left_wheel_ticks", &WheelTickInput::front_left_wheel_ticks)
      .property("front_right_wheel_ticks", &WheelTickInput::front_right_wheel_ticks)
      .property("rear_left_wheel_ticks", &WheelTickInput::rear_left_wheel_ticks)
      .property("rear_right_wheel_ticks", &WheelTickInput::rear_right_wheel_ticks)
      .ARRAY_PROPERTY(WheelTickInput, reserved)
      .STRUCT_FUNCTIONS(WheelTickInput);

  static auto RawWheelTickOutput_MESSAGE_TYPE =  RawWheelTickOutput::MESSAGE_TYPE;
  static auto RawWheelTickOutput_MESSAGE_VERSION = RawWheelTickOutput::MESSAGE_VERSION;
  class_<RawWheelTickOutput>("RawWheelTickOutput")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &RawWheelTickOutput_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &RawWheelTickOutput_MESSAGE_VERSION)
      .property("details", &RawWheelTickOutput::details)
      .property("front_left_wheel_ticks", &RawWheelTickOutput::front_left_wheel_ticks)
      .property("front_right_wheel_ticks", &RawWheelTickOutput::front_right_wheel_ticks)
      .property("rear_left_wheel_ticks", &RawWheelTickOutput::rear_left_wheel_ticks)
      .property("rear_right_wheel_ticks", &RawWheelTickOutput::rear_right_wheel_ticks)
      .property("gear", &RawWheelTickOutput::gear)
      .ARRAY_PROPERTY(RawWheelTickOutput, reserved)
      .STRUCT_FUNCTIONS(RawWheelTickOutput);

  static auto VehicleTickInput_MESSAGE_TYPE =  VehicleTickInput::MESSAGE_TYPE;
  static auto VehicleTickInput_MESSAGE_VERSION = VehicleTickInput::MESSAGE_VERSION;
  class_<VehicleTickInput>("VehicleTickInput")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &VehicleTickInput_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &VehicleTickInput_MESSAGE_VERSION)
      .property("details", &VehicleTickInput::details)
      .property("tick_count", &VehicleTickInput::tick_count)
      .property("gear", &VehicleTickInput::gear)
      .ARRAY_PROPERTY(VehicleTickInput, reserved)
      .STRUCT_FUNCTIONS(VehicleTickInput);

  static auto RawVehicleTickOutput_MESSAGE_TYPE =  RawVehicleTickOutput::MESSAGE_TYPE;
  static auto RawVehicleTickOutput_MESSAGE_VERSION = RawVehicleTickOutput::MESSAGE_VERSION;
  class_<RawVehicleTickOutput>("RawVehicleTickOutput")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &RawVehicleTickOutput_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &RawVehicleTickOutput_MESSAGE_VERSION)
      .property("details", &RawVehicleTickOutput::details)
      .property("tick_count", &RawVehicleTickOutput::tick_count)
      .property("gear", &RawVehicleTickOutput::gear)
      .ARRAY_PROPERTY(RawVehicleTickOutput, reserved)
      .STRUCT_FUNCTIONS(RawVehicleTickOutput);

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

  static auto RawHeadingOutput_MESSAGE_TYPE =
      RawHeadingOutput::MESSAGE_TYPE;
  static auto RawHeadingOutput_MESSAGE_VERSION =
      RawHeadingOutput::MESSAGE_VERSION;
  class_<RawHeadingOutput>("RawHeadingOutput")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &RawHeadingOutput_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &RawHeadingOutput_MESSAGE_VERSION)
      .property("details", &RawHeadingOutput::details)
      .property("solution_type", &RawHeadingOutput::solution_type)
      .ARRAY_PROPERTY(RawHeadingOutput, reserved)
      .property("flags", &RawHeadingOutput::flags)
      .ARRAY_PROPERTY(RawHeadingOutput, relative_position_enu_m)
      .ARRAY_PROPERTY(RawHeadingOutput, position_std_enu_m)
      .property("heading_true_north_deg",
                &RawHeadingOutput::heading_true_north_deg)
      .property("baseline_distance_m", &RawHeadingOutput::baseline_distance_m)
      .STRUCT_FUNCTIONS(RawHeadingOutput);

  static auto HeadingOutput_MESSAGE_TYPE =
      HeadingOutput::MESSAGE_TYPE;
  static auto HeadingOutput_MESSAGE_VERSION =
      HeadingOutput::MESSAGE_VERSION;
  class_<HeadingOutput>("HeadingOutput")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &HeadingOutput_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &HeadingOutput_MESSAGE_VERSION)
      .property("details", &HeadingOutput::details)
      .property("solution_type", &HeadingOutput::solution_type)
      .ARRAY_PROPERTY(HeadingOutput, reserved)
      .property("flags", &HeadingOutput::flags)
      .ARRAY_PROPERTY(HeadingOutput, ypr_deg)
      .property("heading_true_north_deg",
                &HeadingOutput::heading_true_north_deg)
      .STRUCT_FUNCTIONS(HeadingOutput);
}
