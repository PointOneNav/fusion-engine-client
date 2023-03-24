/**************************************************************************/ /**
* @brief Message encode example.
* @file
******************************************************************************/

#include <cmath>
#include <cstdio>
#include <fstream>

#include <point_one/fusion_engine/messages/core.h>
#include <point_one/fusion_engine/messages/crc.h>

using namespace point_one::fusion_engine::messages;

int main(int argc, const char* argv[]) {
  if (argc != 2) {
    printf("Usage: %s FILE\n", argv[0]);
    printf(R"EOF(
Generate a binary file containing a fixed set of messages.
)EOF");
    return 0;
  }

  std::ofstream stream(argv[1], std::ifstream::binary);
  if (!stream) {
    printf("Error opening file '%s'.\n", argv[1]);
    return 1;
  }

  // Enforce a 4-byte aligned address.
  alignas(4) uint8_t storage[4096];

  //////////////////////////////////////////////////////////////////////////////
  // Write a pose message.
  //////////////////////////////////////////////////////////////////////////////

  uint8_t* buffer = storage;
  auto header = reinterpret_cast<MessageHeader*>(buffer);
  buffer += sizeof(MessageHeader);
  *header = MessageHeader();

  header->sequence_number = 0;
  header->message_type = MessageType::POSE;
  header->payload_size_bytes = sizeof(PoseMessage);

  auto pose_message = reinterpret_cast<PoseMessage*>(buffer);
  *pose_message = PoseMessage();

  pose_message->p1_time.seconds = 123;
  pose_message->p1_time.fraction_ns = 456000000;

  pose_message->gps_time.seconds = 1282677727;
  pose_message->gps_time.fraction_ns = 200000000;

  pose_message->solution_type = SolutionType::RTKFixed;
  pose_message->lla_deg[0] = 37.795137;
  pose_message->lla_deg[1] = -122.402754;
  pose_message->lla_deg[2] = 40.8;

  pose_message->ypr_deg[0] = 190.0;
  pose_message->ypr_deg[1] = 2.1;
  pose_message->ypr_deg[2] = 0.1;

  pose_message->velocity_body_mps[0] = -2.3;
  pose_message->velocity_body_mps[1] = -0.01;
  pose_message->velocity_body_mps[2] = 0.3;

  pose_message->position_std_enu_m[0] = 0.1f;
  pose_message->position_std_enu_m[1] = 0.1f;
  pose_message->position_std_enu_m[2] = 0.1f;

  pose_message->ypr_std_deg[0] = 0.2f;
  pose_message->ypr_std_deg[1] = 0.2f;
  pose_message->ypr_std_deg[2] = 0.2f;

  pose_message->velocity_std_body_mps[0] = 0.3f;
  pose_message->velocity_std_body_mps[1] = 0.3f;
  pose_message->velocity_std_body_mps[2] = 0.3f;

  pose_message->aggregate_protection_level_m = 0.4f;
  pose_message->horizontal_protection_level_m = 0.2f;
  pose_message->vertical_protection_level_m = 0.3f;

  header->crc = CalculateCRC(storage);
  stream.write(reinterpret_cast<char*>(storage),
               sizeof(MessageHeader) + header->payload_size_bytes);

  //////////////////////////////////////////////////////////////////////////////
  // Write a GNSS info message associated with the pose message.
  //////////////////////////////////////////////////////////////////////////////

  buffer = storage;
  header = reinterpret_cast<MessageHeader*>(buffer);
  buffer += sizeof(MessageHeader);

  // Note: Updating contents of existing header to maintain sequence number.
  ++header->sequence_number;
  header->message_type = MessageType::GNSS_INFO;
  header->payload_size_bytes = sizeof(GNSSInfoMessage);

  auto gnss_info_message = reinterpret_cast<GNSSInfoMessage*>(buffer);
  *gnss_info_message = GNSSInfoMessage();

  gnss_info_message->p1_time.seconds = 123;
  gnss_info_message->p1_time.fraction_ns = 456000000;

  gnss_info_message->gps_time.seconds = 1282677727;
  gnss_info_message->gps_time.fraction_ns = 200000000;

  gnss_info_message->leap_second = 18;
  gnss_info_message->num_svs = 22;

  gnss_info_message->corrections_age = (uint16_t)std::lround(1.1 * 10.0);
  gnss_info_message->baseline_distance = (uint16_t)std::lround(10300 / 10.0);
  gnss_info_message->reference_station_id = 4321;

  gnss_info_message->gdop = 1.6f;
  gnss_info_message->pdop = 1.3f;
  gnss_info_message->hdop = 1.2f;
  gnss_info_message->vdop = 1.5f;

  gnss_info_message->gps_time_std_sec = 1e-10f;

  header->crc = CalculateCRC(storage);
  stream.write(reinterpret_cast<char*>(storage),
               sizeof(MessageHeader) + header->payload_size_bytes);

  //////////////////////////////////////////////////////////////////////////////
  // Write a GNSS satellite message associated with the pose message.
  //////////////////////////////////////////////////////////////////////////////

  buffer = storage;
  header = reinterpret_cast<MessageHeader*>(buffer);
  buffer += sizeof(MessageHeader);

  // Note: Updating contents of existing header to maintain sequence number.
  ++header->sequence_number;
  header->message_type = MessageType::GNSS_SATELLITE;
  header->payload_size_bytes =
      sizeof(GNSSSatelliteMessage) + 2 * sizeof(SatelliteInfo);

  auto gnss_satellite_message = reinterpret_cast<GNSSSatelliteMessage*>(buffer);
  buffer += sizeof(GNSSSatelliteMessage);
  *gnss_satellite_message = GNSSSatelliteMessage();

  gnss_satellite_message->p1_time.seconds = 123;
  gnss_satellite_message->p1_time.fraction_ns = 456000000;

  gnss_satellite_message->gps_time.seconds = 1282677727;
  gnss_satellite_message->gps_time.fraction_ns = 200000000;

  gnss_satellite_message->num_satellites = 2;

  auto satellite_info = reinterpret_cast<SatelliteInfo*>(buffer);
  buffer += sizeof(SatelliteInfo);
  *satellite_info = SatelliteInfo();
  satellite_info->system = SatelliteType::GPS;
  satellite_info->prn = 4;
  satellite_info->usage = SatelliteInfo::SATELLITE_USED;
  satellite_info->azimuth_deg = 34.5f;
  satellite_info->elevation_deg = 56.2f;

  satellite_info = reinterpret_cast<SatelliteInfo*>(buffer);
  *satellite_info = SatelliteInfo();
  satellite_info->system = SatelliteType::GALILEO;
  satellite_info->prn = 9;
  satellite_info->usage = SatelliteInfo::SATELLITE_USED;
  satellite_info->azimuth_deg = 79.4f;
  satellite_info->elevation_deg = 16.1f;

  header->crc = CalculateCRC(storage);
  stream.write(reinterpret_cast<char*>(storage),
               sizeof(MessageHeader) + header->payload_size_bytes);

  //////////////////////////////////////////////////////////////////////////////
  // Write another pose message 0.2 seconds later.
  //////////////////////////////////////////////////////////////////////////////

  buffer = storage;
  header = reinterpret_cast<MessageHeader*>(buffer);
  buffer += sizeof(MessageHeader);

  // Note: Updating contents of existing header to maintain sequence number.
  ++header->sequence_number;
  header->message_type = MessageType::POSE;
  header->payload_size_bytes = sizeof(PoseMessage);

  pose_message = reinterpret_cast<PoseMessage*>(buffer);
  *pose_message = PoseMessage();

  pose_message->p1_time.seconds = 123;
  pose_message->p1_time.fraction_ns = 667000000;

  pose_message->gps_time.seconds = 1282677727;
  pose_message->gps_time.fraction_ns = 400000000;

  pose_message->solution_type = SolutionType::RTKFloat;
  pose_message->lla_deg[0] = 37.802369;
  pose_message->lla_deg[1] = -122.405823;
  pose_message->lla_deg[2] = 82.0;

  pose_message->ypr_deg[0] = 37.0;
  pose_message->ypr_deg[1] = 0.0;
  pose_message->ypr_deg[2] = 0.0;

  pose_message->velocity_body_mps[0] = 1.2;
  pose_message->velocity_body_mps[1] = 0.03;
  pose_message->velocity_body_mps[2] = 0.1;

  pose_message->position_std_enu_m[0] = 0.05f;
  pose_message->position_std_enu_m[1] = 0.05f;
  pose_message->position_std_enu_m[2] = 0.05f;

  pose_message->ypr_std_deg[0] = 0.1f;
  pose_message->ypr_std_deg[1] = 0.1f;
  pose_message->ypr_std_deg[2] = 0.1f;

  pose_message->velocity_std_body_mps[0] = 0.15f;
  pose_message->velocity_std_body_mps[1] = 0.15f;
  pose_message->velocity_std_body_mps[2] = 0.15f;

  pose_message->aggregate_protection_level_m = 0.3f;
  pose_message->horizontal_protection_level_m = 0.08f;
  pose_message->vertical_protection_level_m = 0.2f;

  header->crc = CalculateCRC(storage);
  stream.write(reinterpret_cast<char*>(storage),
               sizeof(MessageHeader) + header->payload_size_bytes);

  stream.close();

  return 0;
}
