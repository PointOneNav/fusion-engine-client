#include "point_one/fusion_engine/messages/data_version.h"

#include <sstream>

namespace point_one {
namespace fusion_engine {
namespace messages {

std::ostream& operator<<(std::ostream& stream, const DataVersion& ver) {
  if (ver.IsValid()) {
    return stream << (int)ver.major << "." << ver.minor;
  } else {
    return stream << "<invalid>";
  }
}

std::string ToString(const DataVersion& ver) {
  std::stringstream ss;
  ss << ver;
  return ss.str();
}

DataVersion FromString(const char* str) {
  char* end_c = nullptr;
  long tmp = 0;
  DataVersion version;

  tmp = strtol(str, &end_c, 10);
  if (end_c == str || tmp > 0xFF || tmp < 0) {
    return INVALID_DATA_VERSION;
  }
  version.major = (uint8_t)tmp;

  const char* minor_str = end_c + 1;

  tmp = strtol(minor_str, &end_c, 10);
  if (end_c == minor_str || tmp > 0xFFFF || tmp < 0) {
    return INVALID_DATA_VERSION;
  }
  version.minor = (uint16_t)tmp;

  return version;
}

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
