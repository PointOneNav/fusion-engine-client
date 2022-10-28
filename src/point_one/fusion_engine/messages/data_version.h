#pragma once

#include <iostream>
#include <string>

namespace point_one {
namespace fusion_engine {
namespace messages {

// Enforce 4-byte alignment and packing of all data structures and values.
// Floating point values are aligned on platforms that require it. This is done
// with a combination of setting struct attributes, and manual alignment
// within the definitions. See the "Message Packing" section of the README.
#pragma pack(push, 1)

/**
 * @brief A struct representing the version of a data object.
 *
 * The version is considered invalid if @ref major is 0xFF and @ref minor is
 * 0xFFFF.
 */
struct alignas(4) DataVersion {
  // The reserved bytes must be 0xFF for backward compatibility.
  uint8_t reserved = 0xFF;
  uint8_t major = 0xFF;
  uint16_t minor = 0xFF;

  constexpr DataVersion() = default;
  constexpr DataVersion(uint8_t major, uint16_t minor)
      : major(major), minor(minor) {}

  /**
   * @brief Returns whether the stored version is valid.
   *
   * @return `true` if the version is valid, `false` otherwise.
   */
  bool IsValid() const { return major != 0xFF || minor != 0xFFFF; }
};

#pragma pack(pop)

constexpr DataVersion INVALID_DATA_VERSION;

inline constexpr bool operator==(const DataVersion& a, const DataVersion& b) {
  return a.major == b.major && a.minor == b.minor;
}

inline constexpr bool operator!=(const DataVersion& a, const DataVersion& b) {
  return !(a == b);
}

inline constexpr bool operator<(const DataVersion& a, const DataVersion& b) {
  return a.major < b.major || (a.major == b.major && a.minor < b.minor);
}

inline constexpr bool operator>(const DataVersion& a, const DataVersion& b) {
  return b < a;
}

inline constexpr bool operator<=(const DataVersion& a, const DataVersion& b) {
  return !(a > b);
}

inline constexpr bool operator>=(const DataVersion& a, const DataVersion& b) {
  return !(a < b);
}

/**
 * @brief Helper class for printing out X.Y form of @ref DataVersion.
 *
 * ```cpp
 * DataVersion ver{3, 2};
 * std::cout << "Ver: " << ver;
 * // Ver: 3.2
 * ```
 */
std::ostream& operator<<(std::ostream& stream, const DataVersion& ver);

std::string ToString(const DataVersion& ver);

DataVersion FromString(const char* str);

inline DataVersion FromString(std::string str) {
  return FromString(str.c_str());
}

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
