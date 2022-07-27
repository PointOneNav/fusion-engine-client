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
      .property("gps_time", &PoseMessage::gps_time)
      .property("solution_type", &PoseMessage::solution_type)
      .property("reserved", &PoseMessage::reserved)
      .property("undulation_cm", &PoseMessage::undulation_cm)
      .ARRAY_PROPERTY(PoseMessage, lla_deg)
      .ARRAY_PROPERTY(PoseMessage, position_std_enu_m)
      .PARSE_FUNCTION(PoseMessage);

  static auto PoseAuxMessage_MESSAGE_TYPE = PoseAuxMessage::MESSAGE_TYPE;
  static auto PoseAuxMessage_MESSAGE_VERSION = PoseAuxMessage::MESSAGE_VERSION;
  class_<PoseAuxMessage>("PoseAuxMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &PoseAuxMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &PoseAuxMessage_MESSAGE_VERSION)
      .property("p1_time", &PoseAuxMessage::p1_time)
      .ARRAY_PROPERTY(PoseAuxMessage, position_std_body_m)
      .ARRAY_PROPERTY(PoseAuxMessage, position_cov_enu_m2)
      .ARRAY_PROPERTY(PoseAuxMessage, attitude_quaternion)
      .ARRAY_PROPERTY(PoseAuxMessage, velocity_enu_mps)
      .ARRAY_PROPERTY(PoseAuxMessage, velocity_std_enu_mps)
      .PARSE_FUNCTION(PoseAuxMessage);

  static auto GNSSInfoMessage_MESSAGE_TYPE = GNSSInfoMessage::MESSAGE_TYPE;
  static auto GNSSInfoMessage_MESSAGE_VERSION =
      GNSSInfoMessage::MESSAGE_VERSION;
  class_<GNSSInfoMessage>("GNSSInfoMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &GNSSInfoMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &GNSSInfoMessage_MESSAGE_VERSION)
      .property("p1_time", &GNSSInfoMessage::p1_time)
      .property("gps_time", &GNSSInfoMessage::gps_time)
      .property("last_differential_time",
                &GNSSInfoMessage::last_differential_time)
      .property("reference_station_id", &GNSSInfoMessage::reference_station_id)
      .property("gdop", &GNSSInfoMessage::gdop)
      .property("pdop", &GNSSInfoMessage::pdop)
      .property("hdop", &GNSSInfoMessage::hdop)
      .property("vdop", &GNSSInfoMessage::vdop)
      .property("gps_time_std_sec", &GNSSInfoMessage::gps_time_std_sec)
      .PARSE_FUNCTION(GNSSInfoMessage);

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
      .property("elevation_deg", &SatelliteInfo::elevation_deg);

  static auto GNSSSatelliteMessage_MESSAGE_TYPE =
      GNSSSatelliteMessage::MESSAGE_TYPE;
  static auto GNSSSatelliteMessage_MESSAGE_VERSION =
      GNSSSatelliteMessage::MESSAGE_VERSION;
  class_<GNSSSatelliteMessage>("GNSSSatelliteMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &GNSSSatelliteMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &GNSSSatelliteMessage_MESSAGE_VERSION)
      .property("p1_time", &GNSSSatelliteMessage::p1_time)
      .property("gps_time", &GNSSSatelliteMessage::gps_time)
      .property("num_satellites", &GNSSSatelliteMessage::num_satellites)
      .ARRAY_PROPERTY(GNSSSatelliteMessage, reserved)
      .CHLID_ACCESSOR("GetSatelliteInfo", GNSSSatelliteMessage, num_satellites,
                      SatelliteInfo)
      .PARSE_FUNCTION(GNSSSatelliteMessage);
}
