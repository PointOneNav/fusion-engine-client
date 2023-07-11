#include "point_one/fusion_engine/messages/data_version.h"

#include <sstream>

namespace point_one {
namespace fusion_engine {
namespace messages {

p1_ostream& operator<<(p1_ostream& stream, const DataVersion& ver) {
  if (ver.IsValid()) {
    return stream << (int)ver.major_version << "." << ver.minor_version;
  } else {
    return stream << "<invalid>";
  }
}

std::string ToString(const DataVersion& ver) {
  if (ver.IsValid()) {
    return std::to_string(ver.major_version) + "." +
           std::to_string(ver.minor_version);
  } else {
    return "<invalid>";
  }
}

DataVersion FromString(const char* str) {
  char* end_c = nullptr;
  long tmp = 0;
  DataVersion version;

  tmp = strtol(str, &end_c, 10);
  if (end_c == str || tmp > 0xFF || tmp < 0) {
    return INVALID_DATA_VERSION;
  }
  version.major_version = (uint8_t)tmp;

  const char* minor_str = end_c + 1;

  tmp = strtol(minor_str, &end_c, 10);
  if (end_c == minor_str || tmp > 0xFFFF || tmp < 0) {
    return INVALID_DATA_VERSION;
  }
  version.minor_version = (uint16_t)tmp;

  return version;
}

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
