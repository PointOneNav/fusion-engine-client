/**************************************************************************/ /**
* @brief Message decode example.
* @file
******************************************************************************/

#include <cstdint>
#include <cstdio>
#include <fstream>

#include <point_one/fusion_engine/messages/core.h>
#include <point_one/fusion_engine/messages/crc.h>

using namespace point_one::fusion_engine::messages;

/******************************************************************************/
bool DecodeMessage(std::ifstream& stream, size_t available_bytes) {
  static uint32_t expected_sequence_number = 0;

  // Enforce a 4-byte aligned address.
  alignas(4) uint8_t storage[4096];
  char* buffer = reinterpret_cast<char*>(storage);

  // Read the message header.
  if (available_bytes < sizeof(MessageHeader)) {
    printf("Not enough data: cannot read header. [%zu bytes < %zu bytes]\n",
           available_bytes, sizeof(MessageHeader));
    return false;
  }

  stream.read(buffer, sizeof(MessageHeader));
  if (!stream) {
    printf("Unexpected error reading header.\n");
    return false;
  }

  available_bytes -= sizeof(MessageHeader);

  auto& header = *reinterpret_cast<MessageHeader*>(buffer);
  buffer += sizeof(MessageHeader);

  // Read the message payload.
  if (available_bytes < header.payload_size_bytes) {
    printf("Not enough data: cannot read payload. [%zu bytes < %u bytes]\n",
           available_bytes, header.payload_size_bytes);
    return false;
  }

  stream.read(buffer, header.payload_size_bytes);
  if (!stream) {
    printf("Unexpected error reading payload.\n");
    return false;
  }

  // Verify the message checksum.
  size_t message_size = sizeof(MessageHeader) + header.payload_size_bytes;
  if (!IsValid(storage)) {
    printf(
        "CRC failure. [type=%s (%u), size=%zu bytes (payload size=%u bytes], "
        "sequence=%u, expected_crc=0x%08x, calculated_crc=0x%08x]\n",
        to_string(header.message_type),
        static_cast<unsigned>(header.message_type), message_size,
        header.payload_size_bytes, header.sequence_number, header.crc,
        CalculateCRC(storage));
    return false;
  }

  // Check that the sequence number increments as expected.
  if (header.sequence_number != expected_sequence_number) {
    printf(
        "Warning: unexpected sequence number. [type=%s (%u), size=%zu bytes "
        "(payload size=%u bytes], crc=0x%08x, expected_sequence=%u, "
        "received_sequence=%u]\n",
        to_string(header.message_type),
        static_cast<unsigned>(header.message_type), message_size,
        header.payload_size_bytes, header.crc, expected_sequence_number,
        header.sequence_number);
  }

  expected_sequence_number = header.sequence_number + 1;

  // Interpret the payload.
  if (header.message_type == MessageType::POSE) {
    auto& contents = *reinterpret_cast<PoseMessage*>(buffer);
    buffer += sizeof(contents);

    double p1_time_sec =
        contents.p1_time.seconds + (contents.p1_time.fraction_ns * 1e-9);

    static constexpr double SEC_PER_WEEK = 7 * 24 * 3600.0;
    double gps_time_sec =
        contents.gps_time.seconds + (contents.gps_time.fraction_ns * 1e-9);
    int gps_week = std::lround(gps_time_sec / SEC_PER_WEEK);
    double gps_tow_sec = gps_time_sec - (gps_week * SEC_PER_WEEK);

    printf("Received pose message @ P1 time %.3f seconds. [sequence=%u, "
           "size=%zu B]\n",
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
    auto& contents = *reinterpret_cast<GNSSInfoMessage*>(buffer);
    buffer += sizeof(contents);

    double p1_time_sec =
        contents.p1_time.seconds + (contents.p1_time.fraction_ns * 1e-9);
    double gps_time_sec =
        contents.gps_time.seconds + (contents.gps_time.fraction_ns * 1e-9);
    double last_diff_time_sec =
        contents.last_differential_time.seconds +
        (contents.last_differential_time.fraction_ns * 1e-9);

    printf(
        "Received GNSS info message @ P1 time %.3f seconds. [sequence=%u, "
        "size=%zu B]\n",
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
    auto& contents = *reinterpret_cast<GNSSSatelliteMessage*>(buffer);
    buffer += sizeof(contents);

    double p1_time_sec =
        contents.p1_time.seconds + (contents.p1_time.fraction_ns * 1e-9);

    printf(
        "Received GNSS satellite message @ P1 time %.3f seconds. [sequence=%u, "
        "size=%zu B, %u svs]\n",
        p1_time_sec, header.sequence_number, message_size,
        contents.num_satellites);

    for (unsigned i = 0; i < contents.num_satellites; ++i) {
      auto& sv = *reinterpret_cast<SatelliteInfo*>(buffer);
      buffer += sizeof(sv);

      printf("  %s PRN %u:\n", to_string(sv.system), sv.prn);
      printf("    Elevation/azimuth: (%.1f, %.1f) deg\n", sv.elevation_deg,
             sv.azimuth_deg);
      printf("    In solution: %s\n", sv.usage > 0 ? "yes" : "no");
    }
  } else {
    printf("Ignoring message type %s. [%u bytes]\n",
           to_string(header.message_type), header.payload_size_bytes);
  }

  return true;
}

/******************************************************************************/
int main(int argc, const char* argv[]) {
  if (argc != 2) {
    printf("Usage: %s FILE\n", argv[0]);
    printf(R"EOF(
Decode platform pose messages from a binary file containing FusionEngine data.
)EOF");
    return 0;
  }

  // Open the file.
  std::ifstream stream(argv[1], std::ifstream::binary);
  if (!stream) {
    printf("Error opening file '%s'.\n", argv[1]);
    return 1;
  }

  // Determine the file size.
  stream.seekg(0, stream.end);
  std::streampos file_size_bytes = stream.tellg();
  stream.seekg(0, stream.beg);

  // Decode all messages in the file.
  int return_code = 0;
  while (stream.tellg() != file_size_bytes) {
    if (!DecodeMessage(stream,
                       static_cast<size_t>(file_size_bytes - stream.tellg()))) {
      return_code = 1;
      break;
    }
  }

  // Close the file.
  stream.close();

  return return_code;
}
