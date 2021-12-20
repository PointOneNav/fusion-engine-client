/**************************************************************************/ /**
 * @brief FusionEngine message framer.
 * @file
 ******************************************************************************/

#pragma once

#include <cstddef> // For size_t
#include <cstdint>
#include <functional>
#include <memory>

#include "point_one/fusion_engine/common/portability.h" // For p1_ssize_t
#include "point_one/fusion_engine/messages/defs.h"

namespace point_one {
namespace fusion_engine {
namespace parsers {

/**
 * @brief Frame and validate incoming FusionEngine messages.
 *
 * This class locates and validates FusionEngine messages within a stream of
 * binary data. Data may be stored in an internally allocated buffer, or in an
 * external buffer supplied by the user.
 *
 * The callback function provided to @ref SetMessageCallback() will be called
 * each time a complete message is received. Any messages that do not pass the
 * CRC check, or that are too big to be stored in the data buffer, will be
 * discarded.
 *
 * Example usage:
 * ```cpp
 * void MessageReceived(const MessageHeader& header, const void* payload) {
 *   if (header.message_type == MessageType::POSE) {
 *     auto& contents = *static_cast<const PoseMessage*>(payload);
 *     ...
 *   }
 * }
 *
 * FusionEngineFramer framer(1024);
 * framer.SetMessageCallback(MessageReceived);
 * framer.OnData(my_data, my_data_size);
 * ```
 */
class FusionEngineFramer {
public:
  /**
   * @brief Construct a framer instance with no buffer allocated.
   *
   * @note
   * You must call @ref SetBuffer() to assign a buffer, otherwise all incoming
   * data will be discarded.
   */
  FusionEngineFramer() = default;

  /**
   * @brief Construct a framer instance with an internally allocated buffer.
   *
   * @param capacity_bytes The maximum framing buffer capacity (in bytes).
   */
  explicit FusionEngineFramer(size_t capacity_bytes)
      : FusionEngineFramer(nullptr, capacity_bytes) {}

  /**
   * @brief Construct a framer instance with a user-specified buffer.
   *
   * @post
   * `buffer` must exist for the lifetime of this instance.
   *
   * @param buffer The framing buffer to use. Set to `nullptr` to allocate a
   *        buffer internally.
   * @param capacity_bytes The maximum framing buffer capacity (in bytes).
   */
  FusionEngineFramer(void* buffer, size_t capacity_bytes);

  /**
   * @brief Set the buffer to use for message framing.
   *
   * @post
   * `buffer` must exist for the lifetime of this instance.
   *
   * @param buffer The framing buffer to use. Set to `nullptr` to allocate a
   *        buffer internally.
   * @param capacity_bytes The maximum framing buffer capacity (in bytes).
   */
  void SetBuffer(void* buffer, size_t capacity_bytes);

  /**
   * @brief Enable/disable warnings for CRC and "message too large" failures.
   *
   * This is typically used when the incoming stream has multiple types of
   * binary content (e.g., interleaved FusionEngine and RTCM messages), and the
   * FusionEngine message preamble is expected to appear in the non-FusionEngine
   * content occasionally.
   *
   * @param enabled If `true`, issue warnings on errors.
   */
  void WarnOnError(bool enabled) {
    warn_on_error_ = enabled;
  }

  /**
   * @brief Specify a function to be called when a message is framed.
   *
   * @param callback The function to be called with the message header and a
   *        pointer to the message payload.
   */
  void SetMessageCallback(
      std::function<void(const messages::MessageHeader&, const void*)>
          callback) {
    callback_ = callback;
  }

  /**
   * @brief Reset the framer and discard all pending data.
   */
  void Reset();

  /**
   * @brief Process incoming data.
   *
   * @param buffer A buffer containing data to be framed.
   * @param length_bytes The number of bytes to be framed.
   *
   * @return The total size of all valid, complete messages, or 0 if no messages
   *         were completed.
   */
  size_t OnData(const uint8_t* buffer, size_t length_bytes);

 private:
  enum class State {
    SYNC0 = 0,
    SYNC1 = 1,
    HEADER = 2,
    DATA = 3,
  };

  std::function<void(const messages::MessageHeader&, const void*)> callback_;

  bool warn_on_error_ = true;

  std::unique_ptr<uint8_t[]> managed_buffer_;
  uint8_t* buffer_{nullptr};
  size_t capacity_bytes_{0};

  State state_{State::SYNC0};
  size_t next_byte_index_{0};
  size_t current_message_size_{0};

  /**
   * @brief Process a single byte.
   *
   * @pre
   * The byte must be located at `buffer_[next_byte_index_ - 1]`.
   *
   * @param quiet If `true`, suppress failure warning messages.
   *
   * @return The total size of all valid, complete messages, 0 if no messages
   *         were completed, or <0 CRC or "message too large" error.
   */
  p1_ssize_t OnByte(bool quiet);

  /**
   * @brief Perform a resynchronization operation starting at `buffer_[1]`.
   *
   * @return The total size of all valid, complete messages, or 0 if no messages
   *         were completed.
   */
  size_t Resync();
};

} // namespace parsers
} // namespace fusion_engine
} // namespace point_one
