/**************************************************************************/ /**
 * @brief Common print function used by example applications.
 * @file
 ******************************************************************************/

#pragma once

#include <point_one/fusion_engine/messages/core.h>

namespace point_one {
namespace fusion_engine {
namespace examples {

/**
 * @brief Print the contents of a received FusionEngine message.
 *
 * @param header The message header.
 * @param payload The message payload.
 */
void PrintMessage(const fusion_engine::messages::MessageHeader& header,
                  const void* payload);

} // namespace examples
} // namespace fusion_engine
} // namespace point_one
