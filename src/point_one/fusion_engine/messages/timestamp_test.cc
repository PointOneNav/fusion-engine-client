#include "point_one/fusion_engine/messages/timestamp.h"

#include <cmath>
#include <limits>

#include <gtest/gtest.h>

using namespace point_one::fusion_engine::messages;

// GPS time for 2026/4/29 08:00:00 UTC (arbitrary reference point).
static constexpr uint32_t GPS_DATE_SEC = 1461484818;
static constexpr uint16_t GPS_DATE_WEEK = GPS_DATE_SEC / 604800;
static constexpr double GPS_DATE_TOW = GPS_DATE_SEC - GPS_DATE_WEEK * 604800.0;

////////////////////////////////////////////////////////////////////////////////
// Timestamp
////////////////////////////////////////////////////////////////////////////////

/******************************************************************************/
TEST(TimestampConstruction, DefaultIsInvalid) {
  Timestamp ts;
  EXPECT_FALSE(ts.IsValid());
  EXPECT_FALSE(static_cast<bool>(ts));
}

/******************************************************************************/
TEST(TimestampConstruction, ExplicitSecondsAndNs) {
  Timestamp ts(10, 500000000);
  EXPECT_TRUE(ts.IsValid());
  EXPECT_EQ(ts.seconds, 10u);
  EXPECT_EQ(ts.fraction_ns, 500000000u);
}

/******************************************************************************/
TEST(TimestampConstruction, ZeroIsValid) {
  Timestamp ts(0, 0);
  EXPECT_TRUE(ts.IsValid());
}

/******************************************************************************/
TEST(TimestampToSeconds, InvalidReturnsNaN) {
  EXPECT_TRUE(std::isnan(Timestamp().ToSeconds()));
}

/******************************************************************************/
TEST(TimestampToSeconds, WholeSeconds) {
  EXPECT_DOUBLE_EQ(Timestamp(10, 0).ToSeconds(), 10.0);
}

/******************************************************************************/
TEST(TimestampToSeconds, FractionalSeconds) {
  EXPECT_NEAR(Timestamp(10, 500000000).ToSeconds(), 10.5, 1e-9);
}

/******************************************************************************/
TEST(TimestampToGPSWeekTOW, InvalidReturnsFalse) {
  uint16_t week;
  double tow;
  EXPECT_FALSE(Timestamp().ToGPSWeekTOW(&week, &tow));
}

/******************************************************************************/
TEST(TimestampToGPSWeekTOW, CorrectWeekAndTow) {
  uint16_t week;
  double tow;
  ASSERT_TRUE(Timestamp(GPS_DATE_SEC, 0).ToGPSWeekTOW(&week, &tow));
  EXPECT_EQ(week, GPS_DATE_WEEK);
  EXPECT_NEAR(tow, GPS_DATE_TOW, 1e-9);
}

/******************************************************************************/
TEST(TimestampToGPSWeekTOW, FractionalTow) {
  uint16_t week;
  double tow;
  ASSERT_TRUE(Timestamp(GPS_DATE_SEC, 123000000).ToGPSWeekTOW(&week, &tow));
  EXPECT_NEAR(tow, GPS_DATE_TOW + 0.123, 1e-6);
}

/******************************************************************************/
TEST(TimestampToGPSWeekTOW, NullOutParams) {
  // Should not crash when output pointers are null.
  EXPECT_TRUE(Timestamp(GPS_DATE_SEC, 0).ToGPSWeekTOW(nullptr, nullptr));
}

/******************************************************************************/
TEST(TimestampFromGPSTime, BasicConversion) {
  Timestamp ts = Timestamp::FromGPSTime(GPS_DATE_WEEK, GPS_DATE_TOW);
  EXPECT_TRUE(ts.IsValid());
  EXPECT_EQ(ts.seconds, GPS_DATE_SEC);
  EXPECT_EQ(ts.fraction_ns, 0u);
}

/******************************************************************************/
TEST(TimestampFromGPSTime, RoundtripWithToGPSWeekTOW) {
  uint16_t week;
  double tow;
  ASSERT_TRUE(Timestamp(GPS_DATE_SEC, 0).ToGPSWeekTOW(&week, &tow));
  Timestamp result = Timestamp::FromGPSTime(week, tow);
  EXPECT_EQ(result.seconds, GPS_DATE_SEC);
}

/******************************************************************************/
TEST(TimestampFromGPSTime, FractionalTowPreserved) {
  Timestamp ts = Timestamp::FromGPSTime(GPS_DATE_WEEK, GPS_DATE_TOW + 0.5);
  EXPECT_TRUE(ts.IsValid());
  EXPECT_NEAR(ts.ToSeconds(), GPS_DATE_SEC + 0.5, 1e-6);
}

/******************************************************************************/
TEST(TimestampFromGPSTime, NaNTowReturnsInvalid) {
  EXPECT_FALSE(Timestamp::FromGPSTime(GPS_DATE_WEEK, NAN).IsValid());
}

/******************************************************************************/
TEST(TimestampFromGPSTime, InfiniteTowReturnsInvalid) {
  EXPECT_FALSE(Timestamp::FromGPSTime(GPS_DATE_WEEK,
                                      std::numeric_limits<double>::infinity())
                   .IsValid());
}

/******************************************************************************/
TEST(TimestampFromGPSTime, ZeroTowIsValid) {
  Timestamp ts = Timestamp::FromGPSTime(GPS_DATE_WEEK, 0.0);
  EXPECT_TRUE(ts.IsValid());
  EXPECT_EQ(ts.seconds, GPS_DATE_WEEK * 604800u);
  EXPECT_EQ(ts.fraction_ns, 0u);
}

/******************************************************************************/
TEST(TimestampFromGPSTime, NsRolloverNormalized) {
  // tow with fractional part that rounds to exactly 1,000,000,000 ns should
  // carry into seconds without leaving fraction_ns >= 1e9.
  Timestamp ts = Timestamp::FromGPSTime(0, 1.9999999995);
  EXPECT_TRUE(ts.IsValid());
  EXPECT_LT(ts.fraction_ns, 1000000000u);
}

/******************************************************************************/
TEST(TimestampSubtract, BothValidReturnsDelta) {
  Timestamp a(10, 0);
  Timestamp b(3, 0);
  TimeDelta d = a - b;
  EXPECT_TRUE(d.IsValid());
  EXPECT_NEAR(d.ToSeconds(), 7.0, 1e-9);
}

/******************************************************************************/
TEST(TimestampSubtract, InvalidOperandReturnInvalidDelta) {
  EXPECT_FALSE((Timestamp(10, 0) - Timestamp()).IsValid());
  EXPECT_FALSE((Timestamp() - Timestamp(10, 0)).IsValid());
}

/******************************************************************************/
TEST(TimestampAddDelta, PositiveDelta) {
  Timestamp ts(10, 0);
  TimeDelta d(5.5);
  Timestamp result = ts + d;
  EXPECT_TRUE(result.IsValid());
  EXPECT_EQ(result.seconds, 15u);
  EXPECT_EQ(result.fraction_ns, 500000000u);
}

/******************************************************************************/
TEST(TimestampAddDelta, NegativeDelta) {
  Timestamp ts(10, 0);
  TimeDelta d(-5.5);
  Timestamp result = ts + d;
  EXPECT_TRUE(result.IsValid());
  EXPECT_EQ(result.seconds, 4u);
  EXPECT_EQ(result.fraction_ns, 500000000u);
}

/******************************************************************************/
TEST(TimestampAddDelta, InvalidTimestampReturnsInvalid) {
  EXPECT_FALSE((Timestamp() + TimeDelta(1, 0)).IsValid());
}

/******************************************************************************/
TEST(TimestampAddDelta, InvalidDeltaReturnsInvalid) {
  EXPECT_FALSE((Timestamp(10, 0) + TimeDelta()).IsValid());
}

/******************************************************************************/
TEST(TimestampSubtractDelta, PositiveDelta) {
  Timestamp ts(10, 0);
  TimeDelta d(5.5);
  Timestamp result = ts - d;
  EXPECT_TRUE(result.IsValid());
  EXPECT_EQ(result.seconds, 4u);
  EXPECT_EQ(result.fraction_ns, 500000000u);
}

/******************************************************************************/
TEST(TimestampSubtractDelta, NegativeDelta) {
  Timestamp ts(10, 0);
  TimeDelta d(-5.5);
  Timestamp result = ts - d;
  EXPECT_TRUE(result.IsValid());
  EXPECT_EQ(result.seconds, 15u);
  EXPECT_EQ(result.fraction_ns, 500000000u);
}

/******************************************************************************/
TEST(TimestampSubtractDelta, InvalidDeltaReturnsInvalid) {
  EXPECT_FALSE((Timestamp(10, 0) - TimeDelta()).IsValid());
}

////////////////////////////////////////////////////////////////////////////////
// TimeDelta
////////////////////////////////////////////////////////////////////////////////

/******************************************************************************/
TEST(TimeDeltaConstruction, DefaultIsInvalid) {
  TimeDelta d;
  EXPECT_FALSE(d.IsValid());
  EXPECT_FALSE(static_cast<bool>(d));
}

/******************************************************************************/
TEST(TimeDeltaConstruction, SecondsAndNs) {
  TimeDelta d(5, 500000000);
  EXPECT_TRUE(d.IsValid());
  EXPECT_EQ(d.seconds, 5);
  EXPECT_EQ(d.fraction_ns, 500000000);
}

/******************************************************************************/
TEST(TimeDeltaConstruction, NegativeSecondsAndNs) {
  TimeDelta d(-5, -500000000);
  EXPECT_TRUE(d.IsValid());
  EXPECT_EQ(d.seconds, -5);
  EXPECT_EQ(d.fraction_ns, -500000000);
}

/******************************************************************************/
TEST(TimeDeltaConstruction, FromDouble) {
  TimeDelta d(1.5);
  EXPECT_TRUE(d.IsValid());
  EXPECT_EQ(d.seconds, 1);
  EXPECT_EQ(d.fraction_ns, 500000000);
}

/******************************************************************************/
TEST(TimeDeltaConstruction, FromNegativeDouble) {
  TimeDelta d(-1.5);
  EXPECT_TRUE(d.IsValid());
  EXPECT_EQ(d.seconds, -1);
  EXPECT_EQ(d.fraction_ns, -500000000);
}

/******************************************************************************/
TEST(TimeDeltaConstruction, FromNaNIsInvalid) {
  EXPECT_FALSE(TimeDelta(NAN).IsValid());
}

/******************************************************************************/
TEST(TimeDeltaToSeconds, InvalidReturnsNaN) {
  EXPECT_TRUE(std::isnan(TimeDelta().ToSeconds()));
}

/******************************************************************************/
TEST(TimeDeltaToSeconds, PositiveValue) {
  EXPECT_NEAR(TimeDelta(3, 250000000).ToSeconds(), 3.25, 1e-9);
}

/******************************************************************************/
TEST(TimeDeltaToSeconds, NegativeValue) {
  EXPECT_NEAR(TimeDelta(-2, -500000000).ToSeconds(), -2.5, 1e-9);
}

/******************************************************************************/
TEST(TimeDeltaNormalize, OverflowNsCarriesIntoSeconds) {
  TimeDelta d(0, 1500000000);
  EXPECT_EQ(d.seconds, 1);
  EXPECT_EQ(d.fraction_ns, 500000000);
}

/******************************************************************************/
TEST(TimeDeltaNormalize, NegativeOverflowNsCarriesIntoSeconds) {
  TimeDelta d(0, -1500000000);
  EXPECT_EQ(d.seconds, -1);
  EXPECT_EQ(d.fraction_ns, -500000000);
}

/******************************************************************************/
TEST(TimeDeltaNormalize, MixedSignAligned) {
  // {1, -200000000} → {0, 800000000}
  TimeDelta d(1, -200000000);
  EXPECT_EQ(d.seconds, 0);
  EXPECT_EQ(d.fraction_ns, 800000000);
}

/******************************************************************************/
TEST(TimeDeltaNormalize, NegativeMixedSignAligned) {
  // {-1, 200000000} → {0, -800000000}
  TimeDelta d(-1, 200000000);
  EXPECT_EQ(d.seconds, 0);
  EXPECT_EQ(d.fraction_ns, -800000000);
}

/******************************************************************************/
TEST(TimeDeltaArithmetic, AddTwoDeltas) {
  TimeDelta a(1, 500000000);
  TimeDelta b(2, 600000000);
  TimeDelta result = a + b;
  EXPECT_TRUE(result.IsValid());
  EXPECT_EQ(result.seconds, 4);
  EXPECT_EQ(result.fraction_ns, 100000000);
}

/******************************************************************************/
TEST(TimeDeltaArithmetic, SubtractTwoDeltas) {
  TimeDelta a(5, 0);
  TimeDelta b(3, 0);
  TimeDelta result = a - b;
  EXPECT_TRUE(result.IsValid());
  EXPECT_EQ(result.seconds, 2);
  EXPECT_EQ(result.fraction_ns, 0);
}

/******************************************************************************/
TEST(TimeDeltaArithmetic, AddInvalidReturnsInvalid) {
  TimeDelta valid(1, 0);
  TimeDelta invalid;
  EXPECT_FALSE((valid + invalid).IsValid());
  EXPECT_FALSE((invalid + valid).IsValid());
}

/******************************************************************************/
TEST(TimeDeltaArithmetic, SubtractInvalidReturnsInvalid) {
  TimeDelta valid(1, 0);
  TimeDelta invalid;
  EXPECT_FALSE((valid - invalid).IsValid());
}

/******************************************************************************/
TEST(TimeDeltaArithmetic, CompoundAddAssign) {
  TimeDelta d(1, 0);
  d += TimeDelta(2, 0);
  EXPECT_EQ(d.seconds, 3);
}

/******************************************************************************/
TEST(TimeDeltaArithmetic, CompoundSubtractAssign) {
  TimeDelta d(5, 0);
  d -= TimeDelta(2, 0);
  EXPECT_EQ(d.seconds, 3);
}
