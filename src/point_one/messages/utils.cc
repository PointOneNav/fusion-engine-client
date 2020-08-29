/**************************************************************************/ /**
 * @brief Utility functions.
 ******************************************************************************/

#include "point_one/messages/utils.h"

namespace point_one {
namespace messages {

/******************************************************************************/
std::string GetMessageTypeName(MessageType type) {
  switch (type) {
    case MessageType::INVALID:
      return "Invalid";

    case MessageType::POSE:
      return "Pose";

    case MessageType::GNSS_INFO:
      return "GNSS Info";

    default:
      return "Unrecognized Message (" + std::to_string((int)type) + ")";
  }
}

/******************************************************************************/
std::string GetSatelliteTypeName(SatelliteType type) {
  switch (type) {
    case SatelliteType::UNKNOWN:
      return "Unknown";

    case SatelliteType::GPS:
      return "GPS";

    case SatelliteType::GLONASS:
      return "GLONASS";

    case SatelliteType::LEO:
      return "LEO";

    case SatelliteType::GALILEO:
      return "Galileo";

    case SatelliteType::BEIDOU:
      return "BeiDou";

    case SatelliteType::QZSS:
      return "QZSS";

    case SatelliteType::MIXED:
      return "Mixed";

    case SatelliteType::SBAS:
      return "SBAS";

    case SatelliteType::IRNSS:
      return "IRNSS";

    default:
      return "Invalid System (" + std::to_string((int)type) + ")";
  }
}

} // namespace point_one
} // namespace messages
