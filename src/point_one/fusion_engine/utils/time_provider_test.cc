#include "point_one/fusion_engine/utils/time_provider.h"

#include <gtest/gtest.h>

#include "point_one/fusion_engine/messages/core.h"

using namespace point_one::fusion_engine::messages;
using namespace point_one::fusion_engine::utils;

// GPS time for 2026/4/29 08:00:00 UTC (arbitrary reference point).
static constexpr uint32_t GPS_DATE_SEC = 1461484818;

static MessageHeader MakePoseHeader() {
  MessageHeader header;
  header.message_type = MessageType::POSE;
  return header;
}

static PoseMessage MakePose(double p1_sec, double gps_sec) {
  PoseMessage msg;
  msg.p1_time =
      TimeDelta(p1_sec).IsValid()
          ? Timestamp(static_cast<uint32_t>(p1_sec),
                      static_cast<uint32_t>(
                          (p1_sec - static_cast<uint32_t>(p1_sec)) * 1e9))
          : Timestamp();
  msg.gps_time = Timestamp(
      static_cast<uint32_t>(gps_sec),
      static_cast<uint32_t>((gps_sec - static_cast<uint32_t>(gps_sec)) * 1e9));
  return msg;
}

// Feed one pose message into a TimeProvider.
static void Feed(TimeProvider& tp, double p1_sec, double gps_sec) {
  auto header = MakePoseHeader();
  auto msg = MakePose(p1_sec, gps_sec);
  tp.HandleMessage(header, &msg);
}

////////////////////////////////////////////////////////////////////////////////
// HandleMessage
////////////////////////////////////////////////////////////////////////////////

/******************************************************************************/
TEST(HandleMessage, IgnoresNonPoseMessage) {
  TimeProvider tp;
  MessageHeader header;
  header.message_type = MessageType::INVALID;
  PoseMessage msg = MakePose(10.0, GPS_DATE_SEC);
  tp.HandleMessage(header, &msg);
  EXPECT_FALSE(tp.P1ToGPS(Timestamp(10, 0)).IsValid());
}

/******************************************************************************/
TEST(HandleMessage, StoresFirstUpdate) {
  TimeProvider tp;
  Feed(tp, 10.0, GPS_DATE_SEC);
  // A conversion using the stored reference should succeed.
  EXPECT_TRUE(tp.P1ToGPS(Timestamp(10, 0)).IsValid());
}

/******************************************************************************/
TEST(HandleMessage, AdvancesPrevOnSecondUpdate) {
  TimeProvider tp;
  Feed(tp, 10.0, GPS_DATE_SEC);
  Feed(tp, 11.0, GPS_DATE_SEC + 1);
  // With two references, interpolation is active; midpoint should convert.
  Timestamp gps = tp.P1ToGPS(Timestamp(10, 500000000));
  EXPECT_TRUE(gps.IsValid());
  EXPECT_NEAR(gps.ToSeconds(), GPS_DATE_SEC + 0.5, 1e-3);
}

////////////////////////////////////////////////////////////////////////////////
// Backwards / duplicate timestamp handling
////////////////////////////////////////////////////////////////////////////////

/******************************************************************************/
TEST(HandleMessage, BackwardsTimestampResetsState) {
  TimeProvider tp;
  Feed(tp, 10.0, GPS_DATE_SEC);
  Feed(tp, 11.0, GPS_DATE_SEC + 1);
  Feed(tp, 5.0, GPS_DATE_SEC - 5);
  // After reset only the new reference is known; prev is cleared.
  // Conversion at the new reference point should succeed.
  Timestamp gps = tp.P1ToGPS(Timestamp(5, 0));
  EXPECT_TRUE(gps.IsValid());
  EXPECT_NEAR(gps.ToSeconds(), GPS_DATE_SEC - 5.0, 1e-3);
  // A query before the new reference extrapolates from a single point.
  Timestamp gps2 = tp.P1ToGPS(Timestamp(7, 0));
  EXPECT_TRUE(gps2.IsValid());
  EXPECT_NEAR(gps2.ToSeconds(), GPS_DATE_SEC - 3.0, 1e-3);
}

/******************************************************************************/
TEST(HandleMessage, BackwardsTimestampClearsPrev) {
  TimeProvider tp;
  Feed(tp, 10.0, GPS_DATE_SEC);
  Feed(tp, 11.0, GPS_DATE_SEC + 1);
  Feed(tp, 5.0, GPS_DATE_SEC - 5);
  // No prev means GPSToP1 falls back to single-reference mode.
  Timestamp p1 = tp.GPSToP1(Timestamp(GPS_DATE_SEC - 5, 0));
  EXPECT_TRUE(p1.IsValid());
  EXPECT_NEAR(p1.ToSeconds(), 5.0, 1e-3);
}

/******************************************************************************/
TEST(HandleMessage, ExactDuplicateIsIgnored) {
  TimeProvider tp;
  Feed(tp, 10.0, GPS_DATE_SEC);
  // Feed the same P1 time again; should be silently dropped.
  Feed(tp, 10.0, GPS_DATE_SEC);
  // State should reflect only a single reference (no prev).
  // Conversion should still work using the first reference.
  Timestamp gps = tp.P1ToGPS(Timestamp(12, 0));
  EXPECT_TRUE(gps.IsValid());
  EXPECT_NEAR(gps.ToSeconds(), GPS_DATE_SEC + 2.0, 1e-3);
}

/******************************************************************************/
TEST(HandleMessage, NearDuplicateBelowThresholdIsIgnored) {
  // 0.5 ms forward jump — below the 1 ms duplicate threshold.
  TimeProvider tp;
  Feed(tp, 10.0, GPS_DATE_SEC);
  Feed(tp, 10.0005, GPS_DATE_SEC + 0.0005);
  // Prev should still be invalid (second message was dropped).
  // Single-reference conversion should still be correct.
  Timestamp gps = tp.P1ToGPS(Timestamp(12, 0));
  EXPECT_TRUE(gps.IsValid());
  EXPECT_NEAR(gps.ToSeconds(), GPS_DATE_SEC + 2.0, 1e-3);
}

/******************************************************************************/
TEST(HandleMessage, NearDuplicateAboveThresholdIsAccepted) {
  // 2 ms forward jump — above the 1 ms threshold, should be stored.
  TimeProvider tp;
  Feed(tp, 10.0, GPS_DATE_SEC);
  Feed(tp, 10.002, GPS_DATE_SEC + 0.002);
  // With two references the midpoint should interpolate correctly.
  Timestamp gps = tp.P1ToGPS(Timestamp(10, 1000000));
  EXPECT_TRUE(gps.IsValid());
  EXPECT_NEAR(gps.ToSeconds(), GPS_DATE_SEC + 0.001, 1e-4);
}

////////////////////////////////////////////////////////////////////////////////
// P1ToGPS
////////////////////////////////////////////////////////////////////////////////

/******************************************************************************/
TEST(P1ToGPS, InvalidP1ReturnsInvalid) {
  TimeProvider tp;
  Feed(tp, 10.0, GPS_DATE_SEC);
  EXPECT_FALSE(tp.P1ToGPS(Timestamp()).IsValid());
}

/******************************************************************************/
TEST(P1ToGPS, NoReferenceReturnsInvalid) {
  TimeProvider tp;
  EXPECT_FALSE(tp.P1ToGPS(Timestamp(10, 0)).IsValid());
}

/******************************************************************************/
TEST(P1ToGPS, SingleReferenceStraightOffset) {
  TimeProvider tp;
  Feed(tp, 10.0, GPS_DATE_SEC);
  Timestamp gps = tp.P1ToGPS(Timestamp(12, 0));
  EXPECT_TRUE(gps.IsValid());
  EXPECT_NEAR(gps.ToSeconds(), GPS_DATE_SEC + 2.0, 1e-6);
}

/******************************************************************************/
TEST(P1ToGPS, TwoReferencesInterpolation) {
  TimeProvider tp;
  Feed(tp, 10.0, GPS_DATE_SEC);
  Feed(tp, 20.0, GPS_DATE_SEC + 10);
  Timestamp gps = tp.P1ToGPS(Timestamp(15, 0));
  EXPECT_TRUE(gps.IsValid());
  EXPECT_NEAR(gps.ToSeconds(), GPS_DATE_SEC + 5.0, 1e-3);
}

/******************************************************************************/
TEST(P1ToGPS, TwoReferencesExtrapolation) {
  TimeProvider tp;
  Feed(tp, 10.0, GPS_DATE_SEC);
  Feed(tp, 20.0, GPS_DATE_SEC + 10);
  Timestamp gps = tp.P1ToGPS(Timestamp(25, 0));
  EXPECT_TRUE(gps.IsValid());
  EXPECT_NEAR(gps.ToSeconds(), GPS_DATE_SEC + 15.0, 1e-3);
}

/******************************************************************************/
TEST(P1ToGPS, InterpolationWithDrift) {
  // P1 runs slightly fast: 10 P1-sec == 10.001 GPS-sec.
  TimeProvider tp;
  Feed(tp, 10.0, GPS_DATE_SEC);
  Feed(tp, 20.0, GPS_DATE_SEC + 10.001);
  Timestamp gps = tp.P1ToGPS(Timestamp(15, 0));
  EXPECT_TRUE(gps.IsValid());
  EXPECT_NEAR(gps.ToSeconds(), GPS_DATE_SEC + 5.0005, 1e-3);
}

////////////////////////////////////////////////////////////////////////////////
// GPSToP1
////////////////////////////////////////////////////////////////////////////////

/******************************************************************************/
TEST(GPSToP1, InvalidGPSReturnsInvalid) {
  TimeProvider tp;
  Feed(tp, 10.0, GPS_DATE_SEC);
  EXPECT_FALSE(tp.GPSToP1(Timestamp()).IsValid());
}

/******************************************************************************/
TEST(GPSToP1, NoReferenceReturnsInvalid) {
  TimeProvider tp;
  EXPECT_FALSE(tp.GPSToP1(Timestamp(GPS_DATE_SEC, 0)).IsValid());
}

/******************************************************************************/
TEST(GPSToP1, SingleReferenceStraightOffset) {
  TimeProvider tp;
  Feed(tp, 10.0, GPS_DATE_SEC);
  Timestamp p1 = tp.GPSToP1(Timestamp(GPS_DATE_SEC + 2, 0));
  EXPECT_TRUE(p1.IsValid());
  EXPECT_NEAR(p1.ToSeconds(), 12.0, 1e-6);
}

/******************************************************************************/
TEST(GPSToP1, TwoReferencesInterpolation) {
  TimeProvider tp;
  Feed(tp, 10.0, GPS_DATE_SEC);
  Feed(tp, 20.0, GPS_DATE_SEC + 10);
  Timestamp p1 = tp.GPSToP1(Timestamp(GPS_DATE_SEC + 5, 0));
  EXPECT_TRUE(p1.IsValid());
  EXPECT_NEAR(p1.ToSeconds(), 15.0, 1e-3);
}

/******************************************************************************/
TEST(GPSToP1, TwoReferencesExtrapolation) {
  TimeProvider tp;
  Feed(tp, 10.0, GPS_DATE_SEC);
  Feed(tp, 20.0, GPS_DATE_SEC + 10);
  Timestamp p1 = tp.GPSToP1(Timestamp(GPS_DATE_SEC + 15, 0));
  EXPECT_TRUE(p1.IsValid());
  EXPECT_NEAR(p1.ToSeconds(), 25.0, 1e-3);
}

/******************************************************************************/
TEST(GPSToP1, RoundtripP1ToGPSToP1) {
  TimeProvider tp;
  Feed(tp, 10.0, GPS_DATE_SEC);
  Feed(tp, 20.0, GPS_DATE_SEC + 10);
  Timestamp original(14, 500000000);
  Timestamp gps = tp.P1ToGPS(original);
  ASSERT_TRUE(gps.IsValid());
  Timestamp recovered = tp.GPSToP1(gps);
  ASSERT_TRUE(recovered.IsValid());
  EXPECT_NEAR(recovered.ToSeconds(), original.ToSeconds(), 1e-6);
}

////////////////////////////////////////////////////////////////////////////////
// Reset
////////////////////////////////////////////////////////////////////////////////

/******************************************************************************/
TEST(Reset, ClearsAllState) {
  TimeProvider tp;
  Feed(tp, 10.0, GPS_DATE_SEC);
  Feed(tp, 20.0, GPS_DATE_SEC + 10);
  tp.Reset();
  EXPECT_FALSE(tp.P1ToGPS(Timestamp(10, 0)).IsValid());
  EXPECT_FALSE(tp.GPSToP1(Timestamp(GPS_DATE_SEC, 0)).IsValid());
}

/******************************************************************************/
TEST(Reset, AllowsReuse) {
  TimeProvider tp;
  Feed(tp, 10.0, GPS_DATE_SEC);
  tp.Reset();
  Feed(tp, 5.0, GPS_DATE_SEC + 100);
  Timestamp gps = tp.P1ToGPS(Timestamp(7, 0));
  EXPECT_TRUE(gps.IsValid());
  EXPECT_NEAR(gps.ToSeconds(), GPS_DATE_SEC + 102.0, 1e-3);
}
