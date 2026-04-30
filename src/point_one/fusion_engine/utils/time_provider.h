/**************************************************************************/ /**
 * @brief Helper utility for converting between P1 and GPS time.
 * @file
 ******************************************************************************/

#pragma once

#include <point_one/fusion_engine/common/portability.h> // For P1_EXPORT
#include <point_one/fusion_engine/messages/core.h>

namespace point_one {
namespace fusion_engine {
namespace utils {

// Suppress MSVC C4251: private Timestamp members don't need DLL interface since
// they are a POD type fully defined in the header and not directly accessible
// by clients.
#ifdef _MSC_VER
#  pragma warning(push)
#  pragma warning(disable : 4251)
#endif

/**
 * @brief Utility for converting between P1 and GPS time.
 */
class P1_EXPORT TimeProvider {
 public:
  TimeProvider() = default;

  /**
   * @brief Reset all known time relationships.
   */
  void Reset();

  /**
   * @brief Learn time relationships from incoming FusionEngine messages.
   *
   * @param header The message header.
   * @param payload The message payload.
   */
  void HandleMessage(const messages::MessageHeader& header,
                     const void* payload);

  /**
   * @brief Convert a P1 timestamp to GPS time.
   *
   * @param p1_time The P1 time to convert.
   *
   * @return The resulting GPS time, or an invalid timestamp if the time could
   *         not be converted.
   */
  messages::Timestamp P1ToGPS(const messages::Timestamp& p1_time) const;

  /**
   * @brief Convert a GPS timestamp to P1 time.
   *
   * @param gps_time The GPS time to convert.
   *
   * @return The resulting P1 time, or an invalid timestamp if the time could
   *         not be converted.
   */
  messages::Timestamp GPSToP1(const messages::Timestamp& gps_time) const;

 private:
  messages::Timestamp current_p1_time_;
  messages::Timestamp current_gps_time_;

  messages::Timestamp prev_p1_time_;
  messages::Timestamp prev_gps_time_;
};

#ifdef _MSC_VER
#  pragma warning(pop)
#endif

} // namespace utils
} // namespace fusion_engine
} // namespace point_one
