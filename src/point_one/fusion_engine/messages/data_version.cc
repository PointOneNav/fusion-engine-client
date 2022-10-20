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
  DataVersion version;

  version.major = strtol(str, &end_c, 10);
  if (end_c == str) {
    return INVALID_DATA_VERSION;
  }

  const char* minor_str = end_c + 1;
  version.minor = strtol(minor_str, &end_c, 10);
  if (end_c == minor_str) {
    return INVALID_DATA_VERSION;
  }

  return version;
}

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
