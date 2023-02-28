/**************************************************************************/ /**
 * @brief Emscripten bindings for structs in solution.h.
 ******************************************************************************/

#include <emscripten/bind.h>
#include <emscripten/emscripten.h>

#include <point_one/fusion_engine/messages/core.h>

#include "binding_utils.h"

using namespace emscripten;
using namespace point_one::fusion_engine::messages;

/******************************************************************************/
EMSCRIPTEN_BINDINGS(solution) {
  static auto PoseMessage_MESSAGE_TYPE = PoseMessage::MESSAGE_TYPE;
  static auto PoseMessage_MESSAGE_VERSION = PoseMessage::MESSAGE_VERSION;
  static auto PoseMessage_INVALID_UNDULATION = PoseMessage::INVALID_UNDULATION;
  class_<PoseMessage>("PoseMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &PoseMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &PoseMessage_MESSAGE_VERSION)
      .class_property("INVALID_UNDULATION", &PoseMessage_INVALID_UNDULATION)
      .property("p1_time", &PoseMessage::p1_time)
      .REF_TO(PoseMessage, p1_time)
      .property("gps_time", &PoseMessage::gps_time)
      .REF_TO(PoseMessage, gps_time)
      .property("solution_type", &PoseMessage::solution_type)
      .property("reserved", &PoseMessage::reserved)
      .property("undulation_cm", &PoseMessage::undulation_cm)
      .ARRAY_PROPERTY(PoseMessage, lla_deg)
      .ARRAY_PROPERTY(PoseMessage, position_std_enu_m)
      .ARRAY_PROPERTY(PoseMessage, ypr_deg)
      .ARRAY_PROPERTY(PoseMessage, ypr_std_deg)
      .ARRAY_PROPERTY(PoseMessage, velocity_body_mps)
      .ARRAY_PROPERTY(PoseMessage, velocity_std_body_mps)
      .property("aggregate_protection_level_m",
                &PoseMessage::aggregate_protection_level_m)
      .property("horizontal_protection_level_m",
                &PoseMessage::horizontal_protection_level_m)
      .property("vertical_protection_level_m",
                &PoseMessage::vertical_protection_level_m)
      .STRUCT_FUNCTIONS(PoseMessage);

  static auto PoseAuxMessage_MESSAGE_TYPE = PoseAuxMessage::MESSAGE_TYPE;
  static auto PoseAuxMessage_MESSAGE_VERSION = PoseAuxMessage::MESSAGE_VERSION;
  class_<PoseAuxMessage>("PoseAuxMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &PoseAuxMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &PoseAuxMessage_MESSAGE_VERSION)
      .property("p1_time", &PoseAuxMessage::p1_time)
      .REF_TO(PoseAuxMessage, p1_time)
      .ARRAY_PROPERTY(PoseAuxMessage, position_std_body_m)
      .ARRAY_PROPERTY(PoseAuxMessage, position_cov_enu_m2)
      .ARRAY_PROPERTY(PoseAuxMessage, attitude_quaternion)
      .ARRAY_PROPERTY(PoseAuxMessage, velocity_enu_mps)
      .ARRAY_PROPERTY(PoseAuxMessage, velocity_std_enu_mps)
      .STRUCT_FUNCTIONS(PoseAuxMessage);

  static auto GNSSInfoMessage_MESSAGE_TYPE = GNSSInfoMessage::MESSAGE_TYPE;
  static auto GNSSInfoMessage_MESSAGE_VERSION =
      GNSSInfoMessage::MESSAGE_VERSION;
  class_<GNSSInfoMessage>("GNSSInfoMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &GNSSInfoMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &GNSSInfoMessage_MESSAGE_VERSION)
      .property("p1_time", &GNSSInfoMessage::p1_time)
      .REF_TO(GNSSInfoMessage, p1_time)
      .property("gps_time", &GNSSInfoMessage::gps_time)
      .REF_TO(GNSSInfoMessage, gps_time)
      .property("last_differential_time",
                &GNSSInfoMessage::last_differential_time)
      .REF_TO(GNSSInfoMessage, last_differential_time)
      .property("reference_station_id", &GNSSInfoMessage::reference_station_id)
      .property("gdop", &GNSSInfoMessage::gdop)
      .property("pdop", &GNSSInfoMessage::pdop)
      .property("hdop", &GNSSInfoMessage::hdop)
      .property("vdop", &GNSSInfoMessage::vdop)
      .property("gps_time_std_sec", &GNSSInfoMessage::gps_time_std_sec)
      .STRUCT_FUNCTIONS(GNSSInfoMessage);

  static auto SatelliteInfo_SATELLITE_USED = SatelliteInfo::SATELLITE_USED;
  static auto SatelliteInfo_INVALID_CN0 = SatelliteInfo::INVALID_CN0;
  class_<SatelliteInfo>("SatelliteInfo")
      .constructor<>()
      .class_property("SATELLITE_USED", &SatelliteInfo_SATELLITE_USED)
      .class_property("INVALID_CN0", &SatelliteInfo_INVALID_CN0)
      .property("system", &SatelliteInfo::system)
      .property("prn", &SatelliteInfo::prn)
      .property("usage", &SatelliteInfo::usage)
      .property("cn0", &SatelliteInfo::cn0)
      .property("azimuth_deg", &SatelliteInfo::azimuth_deg)
      .property("elevation_deg", &SatelliteInfo::elevation_deg)
      .STRUCT_FUNCTIONS(SatelliteInfo);

  static auto GNSSSatelliteMessage_MESSAGE_TYPE =
      GNSSSatelliteMessage::MESSAGE_TYPE;
  static auto GNSSSatelliteMessage_MESSAGE_VERSION =
      GNSSSatelliteMessage::MESSAGE_VERSION;
  class_<GNSSSatelliteMessage>("GNSSSatelliteMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &GNSSSatelliteMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &GNSSSatelliteMessage_MESSAGE_VERSION)
      .property("p1_time", &GNSSSatelliteMessage::p1_time)
      .REF_TO(GNSSSatelliteMessage, p1_time)
      .property("gps_time", &GNSSSatelliteMessage::gps_time)
      .REF_TO(GNSSSatelliteMessage, gps_time)
      .property("num_satellites", &GNSSSatelliteMessage::num_satellites)
      .ARRAY_PROPERTY(GNSSSatelliteMessage, reserved)
      .CHILD_ACCESSOR("GetSatelliteInfo", GNSSSatelliteMessage, num_satellites,
                      SatelliteInfo)
      .STRUCT_FUNCTIONS(GNSSSatelliteMessage);

  enum_<CalibrationStage>("CalibrationStage")
      .value("UNKNOWN", CalibrationStage::UNKNOWN)
      .value("MOUNTING_ANGLE", CalibrationStage::MOUNTING_ANGLE)
      .value("DONE", CalibrationStage::DONE);

  static auto CalibrationStatusMessage_MESSAGE_TYPE =
      CalibrationStatusMessage::MESSAGE_TYPE;
  static auto CalibrationStatusMessage_MESSAGE_VERSION =
      CalibrationStatusMessage::MESSAGE_VERSION;
  class_<CalibrationStatusMessage>("CalibrationStatusMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &CalibrationStatusMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION",
                      &CalibrationStatusMessage_MESSAGE_VERSION)
      .property("p1_time", &CalibrationStatusMessage::p1_time)
      .REF_TO(CalibrationStatusMessage, p1_time)
      .property("calibration_stage",
                &CalibrationStatusMessage::calibration_stage)
      .ARRAY_PROPERTY(CalibrationStatusMessage, reserved1)
      .ARRAY_PROPERTY(CalibrationStatusMessage, ypr_deg)
      .ARRAY_PROPERTY(CalibrationStatusMessage, ypr_std_dev_deg)
      .property("travel_distance_m",
                &CalibrationStatusMessage::travel_distance_m)
      .ARRAY_PROPERTY(CalibrationStatusMessage, reserved2)
      .property("state_verified", &CalibrationStatusMessage::state_verified)
      .ARRAY_PROPERTY(CalibrationStatusMessage, reserved3)
      .property("gyro_bias_percent_complete",
                &CalibrationStatusMessage::gyro_bias_percent_complete)
      .property("accel_bias_percent_complete",
                &CalibrationStatusMessage::accel_bias_percent_complete)
      .property("mounting_angle_percent_complete",
                &CalibrationStatusMessage::mounting_angle_percent_complete)
      .ARRAY_PROPERTY(CalibrationStatusMessage, reserved4)
      .property("min_travel_distance_m",
                &CalibrationStatusMessage::min_travel_distance_m)
      .ARRAY_PROPERTY(CalibrationStatusMessage, mounting_angle_max_std_dev_deg)
      .STRUCT_FUNCTIONS(CalibrationStatusMessage);

  static auto RelativeENUPositionMessage_MESSAGE_TYPE =
      RelativeENUPositionMessage::MESSAGE_TYPE;
  static auto RelativeENUPositionMessage_MESSAGE_VERSION =
      RelativeENUPositionMessage::MESSAGE_VERSION;
  static auto RelativeENUPositionMessage_INVALID_REFERENCE_STATION =
      RelativeENUPositionMessage::INVALID_REFERENCE_STATION;
  class_<RelativeENUPositionMessage>("RelativeENUPositionMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &RelativeENUPositionMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION",
                      &RelativeENUPositionMessage_MESSAGE_VERSION)
      .class_property("INVALID_REFERENCE_STATION",
                      &RelativeENUPositionMessage_INVALID_REFERENCE_STATION)
      .property("p1_time", &RelativeENUPositionMessage::p1_time)
      .REF_TO(RelativeENUPositionMessage, p1_time)
      .property("gps_time", &RelativeENUPositionMessage::gps_time)
      .REF_TO(RelativeENUPositionMessage, gps_time)
      .property("solution_type", &RelativeENUPositionMessage::solution_type)
      .ARRAY_PROPERTY(RelativeENUPositionMessage, reserved)
      .property("reference_station_id",
                &RelativeENUPositionMessage::reference_station_id)
      .ARRAY_PROPERTY(RelativeENUPositionMessage, relative_position_enu_m)
      .ARRAY_PROPERTY(RelativeENUPositionMessage, position_std_enu_m)
      .STRUCT_FUNCTIONS(RelativeENUPositionMessage);
}
