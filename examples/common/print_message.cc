/**************************************************************************/ /**
 * @brief Common print function used by example applications.
 * @file
 ******************************************************************************/

#include "common/print_message.h"

using namespace point_one::fusion_engine::messages;

namespace point_one {
namespace fusion_engine {
namespace examples {

/******************************************************************************/
void PrintMessage(const MessageHeader& header, const void* payload_in) {
  auto payload = static_cast<const uint8_t*>(payload_in);
  size_t message_size = sizeof(MessageHeader) + header.payload_size_bytes;

  if (header.message_type == MessageType::POSE) {
    auto& contents = *reinterpret_cast<const PoseMessage*>(payload);

    double p1_time_sec =
        contents.p1_time.seconds + (contents.p1_time.fraction_ns * 1e-9);

    static constexpr double SEC_PER_WEEK = 7 * 24 * 3600.0;
    double gps_time_sec =
        contents.gps_time.seconds + (contents.gps_time.fraction_ns * 1e-9);
    int gps_week = std::lround(gps_time_sec / SEC_PER_WEEK);
    double gps_tow_sec = gps_time_sec - (gps_week * SEC_PER_WEEK);

    printf("Pose message @ P1 time %.3f seconds. [sequence=%u, size=%zu B]\n",
           p1_time_sec, header.sequence_number, message_size);
    printf("  Position (LLA): %.6f, %.6f, %.3f (deg, deg, m)\n",
           contents.lla_deg[0], contents.lla_deg[1], contents.lla_deg[2]);
    printf("  GPS Time: %d:%.3f (%.3f seconds)\n", gps_week, gps_tow_sec,
           gps_time_sec);
    printf("  Attitude (YPR): %.2f, %.2f, %.2f (deg, deg, deg)\n",
           contents.ypr_deg[0], contents.ypr_deg[1], contents.ypr_deg[2]);
    printf("  Velocity (Body): %.2f, %.2f, %.2f (m/s, m/s, m/s)\n",
           contents.velocity_body_mps[0], contents.velocity_body_mps[1],
           contents.velocity_body_mps[2]);
    printf("  Position Std Dev (ENU): %.2f, %.2f, %.2f (m, m, m)\n",
           contents.position_std_enu_m[0], contents.position_std_enu_m[1],
           contents.position_std_enu_m[2]);
    printf("  Attitude Std Dev (YPR): %.2f, %.2f, %.2f (deg, deg, deg)\n",
           contents.ypr_std_deg[0], contents.ypr_std_deg[1],
           contents.ypr_std_deg[2]);
    printf("  Velocity Std Dev (Body): %.2f, %.2f, %.2f (m/s, m/s, m/s)\n",
           contents.velocity_std_body_mps[0], contents.velocity_std_body_mps[1],
           contents.velocity_std_body_mps[2]);
    printf("  Protection Levels:\n");
    printf("    Aggregate: %.2f m\n", contents.aggregate_protection_level_m);
    printf("    Horizontal: %.2f m\n", contents.horizontal_protection_level_m);
    printf("    Vertical: %.2f m\n", contents.vertical_protection_level_m);
  } else if (header.message_type == MessageType::GNSS_INFO) {
    auto& contents = *reinterpret_cast<const GNSSInfoMessage*>(payload);

    double p1_time_sec =
        contents.p1_time.seconds + (contents.p1_time.fraction_ns * 1e-9);
    double gps_time_sec =
        contents.gps_time.seconds + (contents.gps_time.fraction_ns * 1e-9);
    double last_diff_time_sec =
        contents.last_differential_time.seconds +
        (contents.last_differential_time.fraction_ns * 1e-9);

    printf(
        "GNSS info message @ P1 time %.3f seconds. [sequence=%u, size=%zu B]\n",
        p1_time_sec, header.sequence_number, message_size);
    printf("  GPS time: %.3f\n", gps_time_sec);
    printf("  GPS time std dev: %.2e sec\n", contents.gps_time_std_sec);
    printf("  Reference station: %s\n",
           contents.reference_station_id ==
                   GNSSInfoMessage::INVALID_REFERENCE_STATION
               ? "none"
               : std::to_string(contents.reference_station_id).c_str());
    printf("  Last differential time: %.3f\n", last_diff_time_sec);
    printf("  GDOP: %.1f  PDOP: %.1f\n", contents.gdop, contents.pdop);
    printf("  HDOP: %.1f  VDOP: %.1f\n", contents.hdop, contents.vdop);
  } else if (header.message_type == MessageType::GNSS_SATELLITE) {
    auto& contents = *reinterpret_cast<const GNSSSatelliteMessage*>(payload);
    payload += sizeof(contents);

    double p1_time_sec =
        contents.p1_time.seconds + (contents.p1_time.fraction_ns * 1e-9);

    printf(
        "GNSS satellite message @ P1 time %.3f seconds. [sequence=%u, "
        "size=%zu B, %u svs]\n",
        p1_time_sec, header.sequence_number, message_size,
        contents.num_satellites);

    for (unsigned i = 0; i < contents.num_satellites; ++i) {
      auto& sv = *reinterpret_cast<const SatelliteInfo*>(payload);
      payload += sizeof(sv);

      printf("  %s PRN %u:\n", to_string(sv.system), sv.prn);
      printf("    Elevation/azimuth: (%.1f, %.1f) deg\n", sv.elevation_deg,
             sv.azimuth_deg);
      printf("    In solution: %s\n", sv.usage > 0 ? "yes" : "no");
    }
  } else {
    printf("Received message type %s. [sequence=%u, %zu bytes]\n",
           to_string(header.message_type), header.sequence_number,
           message_size);
  }
}

} // namespace examples
} // namespace fusion_engine
} // namespace point_one
