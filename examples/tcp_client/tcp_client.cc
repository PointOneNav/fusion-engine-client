/**************************************************************************/ /**
 * @brief Simple Linux TCP client example.
 * @file
 *
 * @note
 * This is a minimal TCP client implementation, meant as an example of how to
 * connect to a device and decode incoming data. It is not robust to network
 * outages, socket reconnects, or other typical network errors. Production
 * implementations must check for and handle these cases appropriately (by
 * checking expected `errno` values, etc.).
 ******************************************************************************/

#include <cerrno>
#include <cmath> // For lround()
#include <csignal> // For signal()
#include <cstdio> // For fprintf()
#include <cstring> // For memcpy()
#include <string> // For stoi() and strerror()

#include <netdb.h> // For gethostbyname() and hostent
#include <netinet/in.h> // For IPPROTO_* macros and htons()
#include <sys/socket.h> // For socket support.
#include <unistd.h> // For close()

#include <point_one/fusion_engine/messages/core.h>
#include <point_one/fusion_engine/parsers/fusion_engine_framer.h>

using namespace point_one::fusion_engine::messages;
using namespace point_one::fusion_engine::parsers;

static bool shutdown_pending_ = false;

/******************************************************************************/
void HandleSignal(int signal) {
  if (signal == SIGINT || signal == SIGTERM) {
    std::signal(signal, SIG_DFL);
    shutdown_pending_ = true;
  }
}

/******************************************************************************/
void HandleMessage(const MessageHeader& header, const void* payload) {
  if (header.message_type == MessageType::POSE) {
    auto& contents = *static_cast<const PoseMessage*>(payload);

    double p1_time_sec =
        contents.p1_time.seconds + (contents.p1_time.fraction_ns * 1e-9);

    static constexpr double SEC_PER_WEEK = 7 * 24 * 3600.0;
    double gps_time_sec =
        contents.gps_time.seconds + (contents.gps_time.fraction_ns * 1e-9);
    int gps_week = std::lround(gps_time_sec / SEC_PER_WEEK);
    double gps_tow_sec = gps_time_sec - (gps_week * SEC_PER_WEEK);

    printf(
        "Received pose message @ P1 time %.3f seconds. [sequence=%u, "
        "size=%zu B]\n",
        p1_time_sec, header.sequence_number,
        sizeof(MessageHeader) + header.payload_size_bytes);
    printf("  GPS Time: %d:%.3f (%.3f seconds)\n", gps_week, gps_tow_sec,
           gps_time_sec);
    printf("  Position (LLA): %.6f, %.6f, %.3f (deg, deg, m)\n",
           contents.lla_deg[0], contents.lla_deg[1], contents.lla_deg[2]);
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
  }
}

/******************************************************************************/
int main(int argc, const char* argv[]) {
  // Parse arguments.
  if (argc < 2 || argc > 3) {
    printf(R"EOF(
Usage: %s HOSTNAME [PORT]

Connect to an Atlas device over TCP and print out the incoming message
contents.
)EOF",
           argv[0]);
    return 0;
  }

  const char* hostname = argv[1];
  int port = argc > 2 ? std::stoi(argv[2]) : 30201;

  // Perform a hostname lookup/translate the string IP address.
  hostent* host_info = gethostbyname(hostname);
  if (host_info == NULL) {
    printf("Error: IP address lookup failed for hostname '%s'.\n", hostname);
    return 1;
  }

  sockaddr_in addr;
  addr.sin_family = AF_INET;
  addr.sin_port = htons(port);
  memcpy(&addr.sin_addr, host_info->h_addr_list[0], host_info->h_length);

  // Connect the socket.
  int sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
  if (sock < 0) {
    printf("Error creating socket.\n");
    return 2;
  }

  int ret = connect(sock, (sockaddr*)&addr, sizeof(addr));
  if (ret < 0) {
    printf("Error connecting to target device: %s (%d)\n", std::strerror(errno),
           errno);
    close(sock);
    return 3;
  }

  // Listen for SIGINT (Ctrl-C) or SIGTERM and shutdown gracefully.
  std::signal(SIGINT, HandleSignal);
  std::signal(SIGTERM, HandleSignal);

  // Receive incoming data.
  FusionEngineFramer framer(1024);
  framer.SetMessageCallback(HandleMessage);

  uint8_t buffer[1024];
  size_t total_bytes_read = 0;
  ret = 0;
  while (!shutdown_pending_) {
    ssize_t bytes_read = recv(sock, buffer, sizeof(buffer), 0);
    if (bytes_read == 0) {
      printf("Socket closed remotely.\n");
      break;
    }
    else if (bytes_read < 0) {
      printf("Error reading from socket: %s (%d)\n", std::strerror(errno),
             errno);
      ret = 4;
      break;
    }
    else {
      total_bytes_read += bytes_read;
      framer.OnData(buffer, (size_t)bytes_read);
    }
  }

  // Done.
  close(sock);

  printf("Finished. %zu bytes read.\n", total_bytes_read);

  return ret;
}
