/**************************************************************************/ /**
 * @brief Helper utility for converting between P1 and GPS time.
 * @file
 ******************************************************************************/

#include "point_one/fusion_engine/utils/time_provider.h"

using namespace point_one::fusion_engine::messages;
using namespace point_one::fusion_engine::utils;

/******************************************************************************/
void TimeProvider::Reset() { *this = TimeProvider(); }

/******************************************************************************/
void TimeProvider::HandleMessage(const MessageHeader& header,
                                 const void* payload) {
  if (header.message_type == MessageType::POSE) {
    // Store the current and previous P1/GPS times, and use them to to convert
    // to/from P1 or GPS time by interpolating.
    //
    // Note: If we had GPS time and the incoming message no longer does, we will
    // no longer be able to convert P1<->GPS time.
    auto& message = *reinterpret_cast<const PoseMessage*>(payload);
    prev_p1_time_ = current_p1_time_;
    prev_gps_time_ = current_gps_time_;
    current_p1_time_ = message.p1_time;
    current_gps_time_ = message.gps_time;
  }
}

/******************************************************************************/
Timestamp TimeProvider::P1ToGPS(const Timestamp& p1_time) const {
  if (!p1_time.IsValid() || !current_p1_time_.IsValid() ||
      !current_gps_time_.IsValid()) {
    return Timestamp();
  }

  // If we have both P1 and GPS time from the previous update, interpolate
  // (or extrapolate) between the previous update and the current one for the
  // most accurate result.
  if (prev_p1_time_.IsValid() && prev_gps_time_.IsValid()) {
    double elapsed_p1_sec = current_p1_time_ - prev_p1_time_;
    double elapsed_gps_sec = current_gps_time_ - prev_gps_time_;
    double delta_p1_sec = p1_time - prev_p1_time_;
    double offset_sec = elapsed_gps_sec * delta_p1_sec / elapsed_p1_sec;
    int32_t int_sec = static_cast<int32_t>(offset_sec);
    TimestampDelta delta_gps(int_sec,
                             static_cast<int32_t>((offset_sec - int_sec) * 1e9));
    return prev_gps_time_ + delta_gps;
  }
  // Otherwise, use the current P1/GPS time offset with no interpolation. This
  // will be less accurate since it cannot account for drift between P1 and GPS
  // time, but for most purposes it will be fine as long as current_*_time_ is
  // recent.
  else {
    return p1_time + (current_gps_time_ - current_p1_time_);
  }
}

/******************************************************************************/
Timestamp TimeProvider::GPSToP1(const Timestamp& gps_time) const {
  if (!gps_time.IsValid() || !current_p1_time_.IsValid() ||
      !current_gps_time_.IsValid()) {
    return Timestamp();
  }

  // If we have both P1 and GPS time from the previous update, interpolate
  // (or extrapolate) between the previous update and the current one for the
  // most accurate result.
  if (prev_gps_time_.IsValid() && prev_p1_time_.IsValid()) {
    double elapsed_gps_sec = current_gps_time_ - prev_gps_time_;
    double elapsed_p1_sec = current_p1_time_ - prev_p1_time_;
    double delta_gps_sec = gps_time - prev_gps_time_;
    double offset_sec = elapsed_p1_sec * delta_gps_sec / elapsed_gps_sec;
    int32_t int_sec = static_cast<int32_t>(offset_sec);
    TimestampDelta delta_p1(int_sec,
                            static_cast<int32_t>((offset_sec - int_sec) * 1e9));
    return prev_p1_time_ + delta_p1;
  }
  // Otherwise, use the current P1/GPS time offset with no interpolation. This
  // will be less accurate since it cannot account for drift between P1 and GPS
  // time, but for most purposes it will be fine as long as current_*_time_ is
  // recent.
  else {
    return gps_time + (current_p1_time_ - current_gps_time_);
  }
}
