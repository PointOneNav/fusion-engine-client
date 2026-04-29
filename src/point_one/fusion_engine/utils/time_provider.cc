/**************************************************************************/ /**
 * @brief Helper utility for converting between P1 and GPS time.
 * @file
 ******************************************************************************/

 #define P1_VMODULE_NAME time_provider

#include "point_one/fusion_engine/utils/time_provider.h"

#include <ostream>

using namespace point_one::fusion_engine::messages;
using namespace point_one::fusion_engine::utils;

#include "point_one/fusion_engine/common/logging.h"

/******************************************************************************/
class P1TimeFormat {
 public:
  const Timestamp time_;

  explicit P1TimeFormat(const Timestamp& time) : time_(time) {}

  inline friend std::ostream& operator<<(std::ostream& stream,
                                         const P1TimeFormat& helper) {
    if (helper.time_) {
      stream << std::fixed << std::setprecision(9) << helper.time_.ToSeconds();
    } else {
      stream << "<invalid>";
    }
    return stream;
  }
};

/******************************************************************************/
class GPSTimeFormat {
 public:
  const Timestamp time_;

  explicit GPSTimeFormat(const Timestamp& time) : time_(time) {}

  inline friend std::ostream& operator<<(std::ostream& stream,
                                         const GPSTimeFormat& helper) {
    uint16_t week_number = 0;
    double tow_sec = NAN;
    if (helper.time_.ToGPSWeekTOW(&week_number, &tow_sec)) {
      stream << "Week " << week_number << ", TOW " << std::fixed
             << std::setprecision(9) << tow_sec;
    } else {
      stream << "<invalid>";
    }
    return stream;
  }
};

/******************************************************************************/
void TimeProvider::Reset() {
  VLOG(1) << "Resetting.";
  *this = TimeProvider();
}

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

    if (VLOG_IS_ON(1)) {
      VLOG(1) << "Received time update at:";
      VLOG(1) << "  P1: " << P1TimeFormat(current_p1_time_);
      VLOG(1) << "  GPS: " << GPSTimeFormat(current_gps_time_);
      if (current_p1_time_ && current_gps_time_ && prev_p1_time_ &&
          prev_gps_time_) {
        VLOG(1) << "  P1/GPS: " << std::fixed << std::setprecision(9)
                << ((current_p1_time_ - prev_p1_time_).ToSeconds() /
                    (current_gps_time_ - prev_gps_time_).ToSeconds())
                << " sec/sec";
      } else {
        VLOG(1) << "  P1/GPS: <unknown>";
      }
    }
  }
}

/******************************************************************************/
Timestamp TimeProvider::P1ToGPS(const Timestamp& p1_time) const {
  if (!p1_time.IsValid()){
    VLOG(2) << "Cannot convert invalid P1 time to GPS time.";
    return Timestamp();
  } else if (!current_p1_time_.IsValid() || !current_gps_time_.IsValid()) {
    VLOG(2) << "P1/GPS relationship not known. Cannot convert P1 "
            << P1TimeFormat(p1_time) << " to GPS time.";
    return Timestamp();
  }

  // If we have both P1 and GPS time from the previous update, interpolate
  // (or extrapolate) between the previous update and the current one for the
  // most accurate result.
  Timestamp gps_time;
  if (prev_p1_time_.IsValid() && prev_gps_time_.IsValid()) {
    double elapsed_p1_sec = current_p1_time_ - prev_p1_time_;
    double elapsed_gps_sec = current_gps_time_ - prev_gps_time_;
    double delta_p1_sec = p1_time - prev_p1_time_;
    double offset_sec = elapsed_gps_sec * delta_p1_sec / elapsed_p1_sec;
    int32_t int_sec = static_cast<int32_t>(offset_sec);
    TimestampDelta delta_gps(
        int_sec, static_cast<int32_t>((offset_sec - int_sec) * 1e9));
    gps_time = prev_gps_time_ + delta_gps;
  }
  // Otherwise, use the current P1/GPS time offset with no interpolation. This
  // will be less accurate since it cannot account for drift between P1 and GPS
  // time, but for most purposes it will be fine as long as current_*_time_ is
  // recent.
  else {
    gps_time = p1_time + (current_gps_time_ - current_p1_time_);
  }

  VLOG(2) << "Converted P1 " << P1TimeFormat(p1_time) << " to GPS "
          << GPSTimeFormat(gps_time);
  return gps_time;
}

/******************************************************************************/
Timestamp TimeProvider::GPSToP1(const Timestamp& gps_time) const {
  if (!gps_time.IsValid()){
    VLOG(2) << "Cannot convert invalid GPS time to P1 time.";
    return Timestamp();
  } else if (!current_p1_time_.IsValid() || !current_gps_time_.IsValid()) {
    VLOG(2) << "P1/GPS relationship not known. Cannot convert GPS "
            << GPSTimeFormat(gps_time) << " to P1 time.";
    return Timestamp();
  }

  // If we have both P1 and GPS time from the previous update, interpolate
  // (or extrapolate) between the previous update and the current one for the
  // most accurate result.
  Timestamp p1_time;
  if (prev_gps_time_.IsValid() && prev_p1_time_.IsValid()) {
    double elapsed_gps_sec = current_gps_time_ - prev_gps_time_;
    double elapsed_p1_sec = current_p1_time_ - prev_p1_time_;
    double delta_gps_sec = gps_time - prev_gps_time_;
    double offset_sec = elapsed_p1_sec * delta_gps_sec / elapsed_gps_sec;
    int32_t int_sec = static_cast<int32_t>(offset_sec);
    TimestampDelta delta_p1(int_sec,
                            static_cast<int32_t>((offset_sec - int_sec) * 1e9));
    p1_time = prev_p1_time_ + delta_p1;
  }
  // Otherwise, use the current P1/GPS time offset with no interpolation. This
  // will be less accurate since it cannot account for drift between P1 and GPS
  // time, but for most purposes it will be fine as long as current_*_time_ is
  // recent.
  else {
    p1_time = gps_time + (current_p1_time_ - current_gps_time_);
  }

  VLOG(2) << "Converted GPS " << GPSTimeFormat(gps_time) << " to P1 "
          << P1TimeFormat(p1_time);
  return p1_time;
}
