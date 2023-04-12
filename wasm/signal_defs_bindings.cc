/**************************************************************************/ /**
 * @brief Emscripten bindings for structs in configuration.h.
 ******************************************************************************/

#include <emscripten/bind.h>
#include <emscripten/emscripten.h>

#include <point_one/fusion_engine/messages/core.h>

#include "binding_utils.h"

using namespace emscripten;
using namespace point_one::fusion_engine::messages;

/******************************************************************************/

uint32_t ToBitMaskWrapperFrequency(FrequencyBand first) {
  return ToBitMask(first);
}

uint32_t ToBitMaskWrapperSatelliteType(SatelliteType type) {
  return ToBitMask(type);
}

const char* to_string_wrapper_satellite_type(int val) {
  return to_string(static_cast<SatelliteType>(val));
}

const char* to_string_wrapper_frequency_band(int val) {
  return to_string(static_cast<FrequencyBand>(val));
}

EMSCRIPTEN_BINDINGS(signal_defs) {
  enum_<SatelliteType>("SatelliteType")
      .value("UNKNOWN", SatelliteType::UNKNOWN)
      .value("GPS", SatelliteType::GPS)
      .value("GLONASS", SatelliteType::GLONASS)
      .value("LEO", SatelliteType::LEO)
      .value("GALILEO", SatelliteType::GALILEO)
      .value("BEIDOU", SatelliteType::BEIDOU)
      .value("QZSS", SatelliteType::QZSS)
      .value("MIXED", SatelliteType::MIXED)
      .value("SBAS", SatelliteType::SBAS)
      .value("IRNSS", SatelliteType::IRNSS);

  static auto SATELLITE_TYPE_MASK_GPS = SatelliteType::GPS;
  static auto SATELLITE_TYPE_MASK_GLONASS = SatelliteType::GLONASS;
  static auto SATELLITE_TYPE_MASK_LEO = SatelliteType::LEO;
  static auto SATELLITE_TYPE_MASK_GALILEO = SatelliteType::GALILEO;
  static auto SATELLITE_TYPE_MASK_BEIDOU = SatelliteType::BEIDOU;
  static auto SATELLITE_TYPE_MASK_QZSS = SatelliteType::QZSS;
  static auto SATELLITE_TYPE_MASK_MIXED = SatelliteType::MIXED;
  static auto SATELLITE_TYPE_MASK_SBAS = SatelliteType::SBAS;
  static auto SATELLITE_TYPE_MASK_IRNSS = SatelliteType::IRNSS;
  static auto SATELLITE_TYPE_MASK_ALL = 0xFFFFFFFF;

  enum_<FrequencyBand>("FrequencyBand")
      .value("UNKNOWN", FrequencyBand::UNKNOWN)
      .value("L1", FrequencyBand::L1)
      .value("L2", FrequencyBand::L2)
      .value("L5", FrequencyBand::L5)
      .value("L6", FrequencyBand::L6);

  static auto FREQUENCY_BAND_MASK_L1 = FrequencyBand::L1;
  static auto FREQUENCY_BAND_MASK_L2 = FrequencyBand::L2;
  static auto FREQUENCY_BAND_MASK_L5 = FrequencyBand::L5;
  static auto FREQUENCY_BAND_MASK_L6 = FrequencyBand::L6;
  static auto FREQUENCY_BAND_MASK_ALL = 0xFFFFFFFF;

  emscripten::function("ToBitMaskFrequency", &ToBitMaskWrapperFrequency);
  emscripten::function("ToBitMaskSatellite", &ToBitMaskWrapperSatelliteType);
  emscripten::function("to_string_sat", &to_string_wrapper_satellite_type, emscripten::allow_raw_pointers());
  emscripten::function("to_string", &to_string_wrapper_frequency_band, emscripten::allow_raw_pointers());
}
