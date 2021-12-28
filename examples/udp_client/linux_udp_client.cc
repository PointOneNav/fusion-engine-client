/**************************************************************************/ /**
 * @brief Simple Linux UDP client example.
 * @file
 *
 * @note
 * This is a minimal UDP client implementation, meant as an example of how to
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

#include <iostream>
#include <fstream>
#include <arpa/inet.h>

#include <point_one/fusion_engine/parsers/fusion_engine_framer.h>

#include "../common/print_message.h"

#define DEBUG_ON 0

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

void * get_in_addr(struct sockaddr * sa) {
    if (sa->sa_family == AF_INET) {
        return &(((struct sockaddr_in *)sa)->sin_addr);
    }
    return &(((struct sockaddr_in6 *)sa)->sin6_addr);
}
/******************************************************************************/

int main(int argc, const char* argv[]) {
  // Parse arguments.
  if (argc > 2) {
    printf(R"EOF(
Usage: %s [PORT]

Connect to an Atlas device over UDP and print out the incoming message
contents.
)EOF", 
        argv[0]);
    return 0;
  }

  int port = (argc == 2) ? std::stoi(argv[1]) : 12345;

  // create UDP socket.
  int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
  if (sock < 0) {
    printf("Error creating socket.\n");
    return 2;
  }

  // bind socket to port
  sockaddr_in addr;
  addr.sin_family = AF_INET;
  addr.sin_port = htons(port);
  addr.sin_addr.s_addr = INADDR_ANY; // any local address
  int ret = bind(sock, (struct sockaddr *) &addr, sizeof(addr));
  if(ret < 0) {
    close(sock);
    printf("Error binding.\n");
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
  struct sockaddr_storage their_addr; // address of recieved packet
  socklen_t addr_len = sizeof(their_addr);
  ret = 0;
  char their_ip[INET6_ADDRSTRLEN];
  while (!shutdown_pending_) {
    ssize_t bytes_read = recvfrom(sock, buffer, sizeof(buffer), 0,
        (struct sockaddr *)&their_addr, &addr_len);

    if (bytes_read < 0) {
      printf("Error reading from socket: %s (%d)\n", std::strerror(errno),
             errno);
      ret = 4;
      break;
    }
    else if (bytes_read == 0) {
      printf("Socket closed remotely.\n");
      break;
    }


    inet_ntop(their_addr.ss_family, get_in_addr((struct sockaddr *)&their_addr), their_ip, sizeof(their_ip));
    buffer[bytes_read] = '\0';
    if(DEBUG_ON) {
      printf("lister: received packet [%s] from %s\n", buffer, their_ip);
    }

    total_bytes_read += bytes_read;
    framer.OnData(buffer, (size_t)bytes_read);
  }

  // Done.
  close(sock);

  printf("Finished. %zu bytes read.\n", total_bytes_read);

  return ret;
}
