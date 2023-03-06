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
  enum_<SystemTimeSource>("SystemTimeSource")
      .value("INVALID", SystemTimeSource::INVALID)
      .value("P1_TIME", SystemTimeSource::P1_TIME)
      .value("TIMESTAMPED_ON_RECEPTION",
             SystemTimeSource::TIMESTAMPED_ON_RECEPTION)
      .value("SENDER_SYSTEM_TIME", SystemTimeSource::SENDER_SYSTEM_TIME)
      .value("GPS_TIME", SystemTimeSource::GPS_TIME);

  class_<MeasurementTimestamps>("MeasurementTimestamps")
      .constructor<>()
      .property("measurement_time", &MeasurementTimestamps::measurement_time)
      .property("measurement_time_source",
                &MeasurementTimestamps::measurement_time_source)
      .ARRAY_PROPERTY(MeasurementTimestamps, reserved)
      .STRUCT_FUNCTIONS(MeasurementTimestamps);

  static auto IMUMeasurement_MESSAGE_TYPE = IMUMeasurement::MESSAGE_TYPE;
  static auto IMUMeasurement_MESSAGE_VERSION = IMUMeasurement::MESSAGE_VERSION;
  class_<IMUMeasurement>("IMUMeasurement")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &IMUMeasurement_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &IMUMeasurement_MESSAGE_VERSION)
      .property("p1_time", &IMUMeasurement::p1_time)
      .ARRAY_PROPERTY(IMUMeasurement, accel_mps2)
      .ARRAY_PROPERTY(IMUMeasurement, accel_std_mps2)
      .ARRAY_PROPERTY(IMUMeasurement, gyro_rps)
      .ARRAY_PROPERTY(IMUMeasurement, gyro_std_rps)
      .STRUCT_FUNCTIONS(IMUMeasurement);

  enum_<GearType>("GearType")
      .value("UNKNOWN", GearType::UNKNOWN)
      .value("FORWARD", GearType::FORWARD)
      .value("REVERSE", GearType::REVERSE)
      .value("PARK", GearType::PARK)
      .value("NEUTRAL", GearType::NEUTRAL);

  static auto WheelSpeedMeasurement_MESSAGE_TYPE =
      WheelSpeedMeasurement::MESSAGE_TYPE;
  static auto WheelSpeedMeasurement_MESSAGE_VERSION =
      WheelSpeedMeasurement::MESSAGE_VERSION;
  class_<WheelSpeedMeasurement>("WheelSpeedMeasurement")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &WheelSpeedMeasurement_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &WheelSpeedMeasurement_MESSAGE_VERSION)
      .property("timestamps", &WheelSpeedMeasurement::timestamps)
      .property("front_left_speed_mps",
                &WheelSpeedMeasurement::front_left_speed_mps)
      .property("front_right_speed_mps",
                &WheelSpeedMeasurement::front_right_speed_mps)
      .property("rear_left_speed_mps",
                &WheelSpeedMeasurement::rear_left_speed_mps)
      .property("rear_right_speed_mps",
                &WheelSpeedMeasurement::rear_right_speed_mps)
      .property("gear", &WheelSpeedMeasurement::gear)
      .property("is_signed", &WheelSpeedMeasurement::is_signed)
      .ARRAY_PROPERTY(WheelSpeedMeasurement, reserved)
      .STRUCT_FUNCTIONS(WheelSpeedMeasurement);

  static auto VehicleSpeedMeasurement_MESSAGE_TYPE =
      WheelSpeedMeasurement::MESSAGE_TYPE;
  static auto VehicleSpeedMeasurement_MESSAGE_VERSION =
      WheelSpeedMeasurement::MESSAGE_VERSION;
  class_<VehicleSpeedMeasurement>("VehicleSpeedMeasurement")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &VehicleSpeedMeasurement_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION",
                      &VehicleSpeedMeasurement_MESSAGE_VERSION)
      .property("timestamps", &VehicleSpeedMeasurement::timestamps)
      .property("vehicle_speed_mps",
                &VehicleSpeedMeasurement::vehicle_speed_mps)
      .property("gear", &VehicleSpeedMeasurement::gear)
      .property("is_signed", &VehicleSpeedMeasurement::is_signed)
      .ARRAY_PROPERTY(VehicleSpeedMeasurement, reserved)
      .STRUCT_FUNCTIONS(VehicleSpeedMeasurement);

  static auto WheelTickMeasurement_MESSAGE_TYPE =
      WheelTickMeasurement::MESSAGE_TYPE;
  static auto WheelTickMeasurement_MESSAGE_VERSION =
      WheelTickMeasurement::MESSAGE_VERSION;
  class_<WheelTickMeasurement>("WheelTickMeasurement")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &WheelTickMeasurement_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &WheelTickMeasurement_MESSAGE_VERSION)
      .property("timestamps", &WheelTickMeasurement::timestamps)
      .property("front_left_wheel_ticks",
                &WheelTickMeasurement::front_left_wheel_ticks)
      .property("front_right_wheel_ticks",
                &WheelTickMeasurement::front_right_wheel_ticks)
      .property("rear_left_wheel_ticks",
                &WheelTickMeasurement::rear_left_wheel_ticks)
      .property("rear_right_wheel_ticks",
                &WheelTickMeasurement::rear_right_wheel_ticks)
      .property("gear", &WheelTickMeasurement::gear)
      .ARRAY_PROPERTY(WheelTickMeasurement, reserved)
      .STRUCT_FUNCTIONS(WheelTickMeasurement);

  static auto VehicleTickMeasurement_MESSAGE_TYPE =
      VehicleTickMeasurement::MESSAGE_TYPE;
  static auto VehicleTickMeasurement_MESSAGE_VERSION =
      VehicleTickMeasurement::MESSAGE_VERSION;
  class_<VehicleTickMeasurement>("VehicleTickMeasurement")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &VehicleTickMeasurement_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION",
                      &VehicleTickMeasurement_MESSAGE_VERSION)
      .property("timestamps", &VehicleTickMeasurement::timestamps)
      .property("tick_count", &VehicleTickMeasurement::tick_count)
      .property("gear", &VehicleTickMeasurement::gear)
      .ARRAY_PROPERTY(VehicleTickMeasurement, reserved)
      .STRUCT_FUNCTIONS(VehicleTickMeasurement);

  static auto HeadingMeasurement_MESSAGE_TYPE =
      HeadingMeasurement::MESSAGE_TYPE;
  static auto HeadingMeasurement_MESSAGE_VERSION =
      HeadingMeasurement::MESSAGE_VERSION;
  class_<HeadingMeasurement>("HeadingMeasurement")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &HeadingMeasurement_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &HeadingMeasurement_MESSAGE_VERSION)
      .property("timestamps", &HeadingMeasurement::timestamps)
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
