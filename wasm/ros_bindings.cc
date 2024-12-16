/**************************************************************************/ /**
 * @brief Emscripten bindings for structs in ros.h.
 ******************************************************************************/

#include <emscripten/bind.h>
#include <emscripten/emscripten.h>

#include <point_one/fusion_engine/messages/core.h>

#include "binding_utils.h"

using namespace emscripten;
using namespace point_one::fusion_engine::messages;

/******************************************************************************/

EMSCRIPTEN_BINDINGS(ros) {
  //   static auto PoseMessage_MESSAGE_TYPE =
  //       PoseMessage::MESSAGE_TYPE;
  //   static auto PoseMessage_MESSAGE_VERSION =
  //       PoseMessage::MESSAGE_VERSION;
  //   class_<PoseMessage>("PoseMessage")
  //       .constructor<>()
  //       .class_property("MESSAGE_TYPE", &PoseMessage_MESSAGE_TYPE)
  //       .class_property("MESSAGE_VERSION", &PoseMessage_MESSAGE_VERSION)
  //       .property("p1_time", &PoseMessage::p1_time)
  //       .ARRAY_PROPERTY(PoseMessage, position_rel_m)
  //       .ARRAY_PROPERTY(PoseMessage, orientation)
  //       .STRUCT_FUNCTIONS(PoseMessage);

  //   static auto GPSFixMessage_MESSAGE_TYPE =
  //       GPSFixMessage::MESSAGE_TYPE;
  //   static auto GPSFixMessage_MESSAGE_VERSION =
  //       GPSFixMessage::MESSAGE_VERSION;
  //   static auto GPSFixMessage_COVARIANCE_TYPE_UNKNOWN = GPSFixMessage::COVARIANCE_TYPE_UNKNOWN;
  //   static auto GPSFixMessage_COVARIANCE_TYPE_APPROXIMATED = GPSFixMessage::COVARIANCE_TYPE_APPROXIMATED;
  //   static auto GPSFixMessage_COVARIANCE_TYPE_DIAGONAL_KNOWN = GPSFixMessage::COVARIANCE_TYPE_DIAGONAL_KNOWN;
  //   static auto GPSFixMessage_COVARIANCE_TYPE_KNOWN = GPSFixMessage::COVARIANCE_TYPE_KNOWN;
  //   class_<GPSFixMessage>("GPSFixMessage")
  //       .constructor<>()
  //       .class_property("MESSAGE_TYPE", &GPSFixMessage_MESSAGE_TYPE)
  //       .class_property("MESSAGE_VERSION", &GPSFixMessage_MESSAGE_VERSION)
  //       .class_property("COVARIANCE_TYPE_UNKNOWN", &GPSFixMessage_COVARIANCE_TYPE_UNKNOWN)
  //       .class_property("COVARIANCE_TYPE_APPROXIMATED", &GPSFixMessage_COVARIANCE_TYPE_APPROXIMATED)
  //       .class_property("COVARIANCE_TYPE_DIAGONAL_KNOWN", &GPSFixMessage_COVARIANCE_TYPE_DIAGONAL_KNOWN)
  //       .class_property("COVARIANCE_TYPE_KNOWN", &GPSFixMessage_COVARIANCE_TYPE_KNOWN)
  //       .property("p1_time", &GPSFixMessage::p1_time)
  //       .property("latitude_deg", &GPSFixMessage::latitude_deg)
  //       .property("longitude_deg", &GPSFixMessage::longitude_deg)
  //       .property("altitude_m", &GPSFixMessage::altitude_m)
  //       .property("track_deg", &GPSFixMessage::track_deg)
  //       .property("speed_mps", &GPSFixMessage::speed_mps)
  //       .property("climb_mps", &GPSFixMessage::climb_mps)
  //       .property("pitch_deg", &GPSFixMessage::pitch_deg)
  //       .property("roll_deg", &GPSFixMessage::roll_deg)
  //       .property("dip_deg", &GPSFixMessage::dip_deg)
  //       .property("gps_time", &GPSFixMessage::gps_time)
  //       .property("gdop", &GPSFixMessage::gdop)
  //       .property("pdop", &GPSFixMessage::pdop)
  //       .property("hdop", &GPSFixMessage::hdop)
  //       .property("vdop", &GPSFixMessage::vdop)
  //       .property("tdop", &GPSFixMessage::tdop)
  //       .property("err_3d_m", &GPSFixMessage::err_3d_m)
  //       .property("err_horiz_m", &GPSFixMessage::err_horiz_m)
  //       .property("err_vert_m", &GPSFixMessage::err_vert_m)
  //       .property("err_track_deg", &GPSFixMessage::err_track_deg)
  //       .property("err_speed_mps", &GPSFixMessage::err_speed_mps)
  //       .property("err_climb_mps", &GPSFixMessage::err_climb_mps)
  //       .property("err_time_sec", &GPSFixMessage::err_time_sec)
  //       .property("err_pitch_deg", &GPSFixMessage::err_pitch_deg)
  //       .property("err_roll_deg", &GPSFixMessage::err_roll_deg)
  //       .property("err_dip_deg", &GPSFixMessage::err_dip_deg)
  //       .property("position_covariance_type", &GPSFixMessage::position_covariance_type)
  //       .ARRAY_PROPERTY(GPSFixMessage, position_covariance_m2)
  //       .ARRAY_PROPERTY(GPSFixMessage, reserved)
  //       .STRUCT_FUNCTIONS(GPSFixMessage);

  //   static auto IMUMessage_MESSAGE_TYPE =
  //       IMUMessage::MESSAGE_TYPE;
  //   static auto IMUMessage_MESSAGE_VERSION =
  //       IMUMessage::MESSAGE_VERSION;
  //   class_<IMUMessage>("IMUMessage")
  //       .constructor<>()
  //       .class_property("MESSAGE_TYPE", &IMUMessage_MESSAGE_TYPE)
  //       .class_property("MESSAGE_VERSION", &IMUMessage_MESSAGE_VERSION)
  //       .property("p1_time", &IMUMessage::p1_time)
  //       .ARRAY_PROPERTY(IMUMessage, orientation)
  //       .ARRAY_PROPERTY(IMUMessage, orientation_covariance)
  //       .ARRAY_PROPERTY(IMUMessage, angular_velocity_rps)
  //       .ARRAY_PROPERTY(IMUMessage, angular_velocity_covariance)
  //       .ARRAY_PROPERTY(IMUMessage, acceleration_mps2)
  //       .ARRAY_PROPERTY(IMUMessage, acceleration_covariance)
  //       .STRUCT_FUNCTIONS(IMUMessage);
}
