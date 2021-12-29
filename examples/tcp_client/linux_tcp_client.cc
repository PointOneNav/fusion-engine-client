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

#include <point_one/fusion_engine/parsers/fusion_engine_framer.h>

#include "../common/print_message.h"

using namespace point_one::fusion_engine::examples;
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
  framer.SetMessageCallback(PrintMessage);

  uint8_t buffer[1024];
  size_t total_bytes_read = 0;
  ret = 0;
  while (!shutdown_pending_) {
    ssize_t bytes_read = recv(sock, buffer, sizeof(buffer), 0);
    if (bytes_read == 0) {
      printf("Socket closed remotely.\n");
      break;
    } else if (bytes_read < 0) {
      printf("Error reading from socket: %s (%d)\n", std::strerror(errno),
             errno);
      ret = 4;
      break;
    } else {
      total_bytes_read += bytes_read;
      framer.OnData(buffer, (size_t)bytes_read);
    }
  }

  // Done.
  close(sock);

  printf("Finished. %zu bytes read.\n", total_bytes_read);

  return ret;
}
