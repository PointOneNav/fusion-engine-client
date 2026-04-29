/**************************************************************************/ /**
 * @brief Example utility for converting between P1 and GPS time.
 * @file
 ******************************************************************************/

#pragma once

#include <point_one/fusion_engine/messages/core.h>

namespace point_one {
namespace fusion_engine {
namespace examples {

/**
 * @brief Utility for converting between P1 and GPS time.
 */
class TimeProvider {
 public:
  TimeProvider() = default;

  void Reset();

  void HandleMessage(const messages::MessageHeader& header,
                     const void* payload);

  messages::Timestamp P1ToGPS(const messages::Timestamp& p1_time) const;

  messages::Timestamp GPSToP1(const messages::Timestamp& gps_time) const;

 private:
  messages::Timestamp current_p1_time_;
  messages::Timestamp current_gps_time_;

  messages::Timestamp prev_p1_time_;
  messages::Timestamp prev_gps_time_;
};

} // namespace examples
} // namespace fusion_engine
} // namespace point_one
