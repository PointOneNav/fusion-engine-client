/**************************************************************************/ /**
 * @brief Utility functions.
 ******************************************************************************/

#pragma once

#include <string>

#include "point_one/common/portability.h"
#include "point_one/messages/defs.h"

namespace point_one {
namespace messages {

/**
 * @brief Get the string name for the specified message type.
 *
 * @param type The desired message type.
 *
 * @return The name of the message.
 */
P1_EXPORT std::string GetMessageTypeName(MessageType type);

/**
 * @brief Get the GNSS constellation name for the specified type enumeration.
 *
 * @param type The desired constellation.
 *
 * @return The name of the specified constellation.
 */
P1_EXPORT std::string GetSatelliteTypeName(SatelliteType type);

} // namespace point_one
} // namespace messages
