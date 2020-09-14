/**************************************************************************/ /**
* @brief Message decode example.
******************************************************************************/

#include <cstdint>
#include <cstdio>
#include <fstream>

#include <point_one/fusion_engine/messages/core.h>
#include <point_one/fusion_engine/messages/crc.h>

using namespace point_one::fusion_engine::messages;

/******************************************************************************/
bool DecodeMessage(std::ifstream& stream, size_t available_bytes) {
  // Enforce a 4-byte aligned address.
  uint8_t storage[4096];
  size_t alignment_offset = reinterpret_cast<size_t>(storage) % 4;
  char* const buffer_start =
      reinterpret_cast<char*>(storage + alignment_offset);
  char* buffer = buffer_start;

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

  MessageHeader& header = *reinterpret_cast<MessageHeader*>(buffer);
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
  if (!IsValid(buffer_start)) {
    printf(
        "CRC failure. [type=%s (%u), size=%zu bytes (payload size=%u bytes], "
        "expected_crc=0x%08x, calculated_crc=0x%08x]\n",
        to_string(header.message_type).c_str(),
        static_cast<unsigned>(header.message_type),
        sizeof(MessageHeader) + header.payload_size_bytes,
        header.payload_size_bytes, header.crc, CalculateCRC(buffer_start));
    return false;
  }

  // Interpret the payload.
  if (header.message_type == MessageType::POSE) {
    PoseMessage& contents = *reinterpret_cast<PoseMessage*>(buffer);
    buffer += sizeof(contents);

    double p1_time_sec =
        contents.p1_time.seconds + (contents.p1_time.fraction_ns * 1e-9);

    printf("Received pose message @ P1 time %.3f seconds:\n", p1_time_sec);
    printf("  Position (LLA): %.6f, %.6f, %.3f (deg, deg, m)\n",
           contents.lla_deg[0], contents.lla_deg[1], contents.lla_deg[2]);
    printf("  Attitude (YPR): %.2f, %.2f, %.2f (deg, deg, deg)\n",
           contents.ypr_deg[0], contents.ypr_deg[1], contents.ypr_deg[2]);
  } else if (header.message_type == MessageType::GNSS_INFO) {
    GNSSInfoMessage& contents = *reinterpret_cast<GNSSInfoMessage*>(buffer);
    buffer += sizeof(contents);

    double p1_time_sec =
        contents.p1_time.seconds + (contents.p1_time.fraction_ns * 1e-9);

    printf("Received GNSS info message @ P1 time %.3f seconds. [%u svs]\n",
           p1_time_sec, contents.num_satellites);

    for (unsigned i = 0; i < contents.num_satellites; ++i) {
      SatelliteInfo& sv = *reinterpret_cast<SatelliteInfo*>(buffer);
      buffer += sizeof(sv);

      printf("  %s PRN %u:\n", to_string(sv.system).c_str(), sv.prn);
      printf("    Elevation/azimuth: (%.1f, %.1f) deg\n", sv.elevation_deg,
             sv.azimuth_deg);
      printf("    In solution: %s\n", sv.used_in_solution ? "yes" : "no");
    }
  } else {
    printf("Ignoring message type %s. [%u bytes]\n",
           to_string(header.message_type).c_str(), header.payload_size_bytes);
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
  ssize_t file_size_bytes = stream.tellg();
  stream.seekg(0, stream.beg);

  // Decode all messages in the file.
  while (stream.tellg() != file_size_bytes) {
    if (!DecodeMessage(stream, file_size_bytes - stream.tellg())) {
      break;
    }
  }

  // Close the file.
  stream.close();

  return 0;
}
