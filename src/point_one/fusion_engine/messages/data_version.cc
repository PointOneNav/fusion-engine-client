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

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
