/**************************************************************************/ /**
* @brief Simple example of linking against the fusion-engine-client library
*        using CMake.
*
* This application does not do anything very interesting. It is meant only as an
* example of how to import fusion-engine-client in CMake using FetchContent. See
* the accompanying CMakeLists.txt file.
*
* @file
******************************************************************************/

#include <cstdio>

#include <point_one/fusion_engine/messages/core.h>

using namespace point_one::fusion_engine::messages;

int main(int argc, const char* argv[]) {
  // Populate a pose message with some content.
  PoseMessage pose_message;

  pose_message.p1_time.seconds = 123;
  pose_message.p1_time.fraction_ns = 456000000;

  pose_message.gps_time.seconds = 1282677727;
  pose_message.gps_time.fraction_ns = 200000000;

  pose_message.solution_type = SolutionType::RTKFixed;
  pose_message.lla_deg[0] = 37.795137;
  pose_message.lla_deg[1] = -122.402754;
  pose_message.lla_deg[2] = 40.8;

  // Print out the LLA position.
  printf("LLA: %.6f, %.6f, %.2f\n", pose_message.lla_deg[0],
         pose_message.lla_deg[1], pose_message.lla_deg[2]);

  return 0;
}
