/**************************************************************************/ /**
 * @brief Use the example `TimeProvider` class to convert between P1 and GPS
 *        time.
 * @file
 ******************************************************************************/

#include <point_one/fusion_engine/messages/core.h>

#include "../common/time_provider.h"

using namespace point_one::fusion_engine::examples;
using namespace point_one::fusion_engine::messages;

/******************************************************************************/
void PrintGPSTime(const Timestamp& gps_time) {
  uint16_t week_number = 0;
  double tow_sec = NAN;
  if (gps_time.ToGPSWeekTOW(&week_number, &tow_sec)) {
    printf("Week %u, TOW %.9f sec\n", week_number, tow_sec);
  }
  else {
    printf("<invalid>\n");
  }
}

/******************************************************************************/
void PrintTimes(const Timestamp& p1_time, const Timestamp& gps_time) {
  printf("  P1: %.9f sec\n", p1_time.ToSeconds());
  printf("  GPS: ");
  PrintGPSTime(gps_time);
}

/******************************************************************************/
void PrintIMUMeasurement(const TimeProvider& time_provider,
                         const IMUOutput& imu_message) {
  PrintTimes(imu_message.p1_time, time_provider.P1ToGPS(imu_message.p1_time));
}

/******************************************************************************/
int main(int argc, const char* argv[]) {
  // Define a time provider we'll use to convert between P1 and GPS time.
  TimeProvider time_provider;

  // Step 1: Try to compute GPS time for an incoming IMU measurement. We have
  // not gotten any pose messages yet, so we do not know the P1/GPS time
  // relationship.
  IMUOutput imu1;
  imu1.p1_time = {0, 999'000'000};
  printf("IMU measurement 1:\n");
  PrintIMUMeasurement(time_provider, imu1);

  // Step 2: First pose message received. Update the time provider. After this,
  // we can start converting P1 timestamps to GPS time.
  MessageHeader pose_header;
  pose_header.message_type = MessageType::POSE;
  PoseMessage pose1;
  pose1.p1_time = {1, 0};
  pose1.gps_time = Timestamp::FromGPSTime(2416, 288018.0);
  time_provider.HandleMessage(pose_header, &pose1);
  printf("First pose message:\n");
  PrintTimes(pose1.p1_time, pose1.gps_time);

  printf("IMU measurement 1 again (GPS time available):\n");
  PrintIMUMeasurement(time_provider, imu1);

  // Step 3: Convert the next IMU measurement's P1 time to GPS time.
  IMUOutput imu2;
  imu2.p1_time = {1, 100'000'500};
  printf("IMU measurement 2:\n");
  PrintIMUMeasurement(time_provider, imu2);

  // Step 4: Second pose message received. We now know the difference in rate
  // between P1 and GPS time, and can interpolate to compute GPS time even more
  // accurately.
  //
  // Here, we're simulating that the P1 clock is initially slightly faster than
  // the GPS clock.
  //
  // Note that the rate of P1 time is steered to match GPS time over time. After
  // GPS time has been available for a few seconds, the two rates will be very
  // close and interpolation will only have a very minor effect.
  PoseMessage pose2;
  pose2.p1_time = {1, 100'001'000};
  pose2.gps_time = Timestamp::FromGPSTime(2416, 288018.1);
  time_provider.HandleMessage(pose_header, &pose2);
  printf("Second pose message:\n");
  PrintTimes(pose2.p1_time, pose2.gps_time);

  printf("IMU measurement 2 again (using interpolation):\n");
  PrintIMUMeasurement(time_provider, imu2);

  // Step 5: Convert a 3rd IMU measurement with interpolation applied.
  IMUOutput imu3;
  imu3.p1_time = {1, 100'001'500};
  printf("IMU measurement 3:\n");
  PrintIMUMeasurement(time_provider, imu3);

  return 0;
}
