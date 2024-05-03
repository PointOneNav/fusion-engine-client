/**************************************************************************/ /**
 * @brief FusionEngine message framer.
 * @file
 ******************************************************************************/

#pragma once

#include "point_one/fusion_engine/common/portability.h"

#include <cstddef> // For size_t
#include <cstdint>
#if P1_HAVE_STD_FUNCTION
#  include <functional>
#endif // P1_HAVE_STD_FUNCTION

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
#if P1_HAVE_STD_FUNCTION
  using MessageCallback =
      std::function<void(const messages::MessageHeader&, const void*)>;
#endif // P1_HAVE_STD_FUNCTION
  using RawMessageCallback = void (*)(void* context,
                                      const messages::MessageHeader& header,
                                      const void* payload);

  /**
   * @brief Construct a framer instance with no buffer allocated.
   *
   * @note
   * You must call @ref SetBuffer() to assign a buffer, otherwise all incoming
   * data will be discarded.
   */
  P1_EXPORT FusionEngineFramer() = default;

  /**
   * @brief Construct a framer instance with an internally allocated buffer.
   *
   * @param capacity_bytes The maximum framing buffer capacity (in bytes).
   */
  P1_EXPORT explicit FusionEngineFramer(size_t capacity_bytes)
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
  P1_EXPORT FusionEngineFramer(void* buffer, size_t capacity_bytes);

  P1_EXPORT ~FusionEngineFramer();

  // Don't allow copying or moving to avoid issues with managed buffer_.
  FusionEngineFramer(const FusionEngineFramer&) = delete; // Copy constructor
  FusionEngineFramer(FusionEngineFramer&&) = delete; // Move constructor
  FusionEngineFramer& operator=(const FusionEngineFramer&) =
      delete; // Copy assignment operator
  FusionEngineFramer& operator=(FusionEngineFramer&&) =
      delete; // Move assignment operator

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
  P1_EXPORT void SetBuffer(void* buffer, size_t capacity_bytes);

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
  P1_EXPORT void WarnOnError(bool enabled) { warn_on_error_ = enabled; }

#if P1_HAVE_STD_FUNCTION
  /**
   * @brief Specify a function to be called when a message is framed.
   *
   * @param callback The function to be called with the message header and a
   *        pointer to the message payload.
   */
  P1_EXPORT void SetMessageCallback(MessageCallback callback) {
    callback_ = callback;
  }
#endif // P1_HAVE_STD_FUNCTION

  /**
   * @brief Specify a function to be called when a message is framed.
   *
   * @param callback The function to be called with the supplied context
   *        variable, the message header, and a pointer to the message payload.
   * @param context A context value that will be passed to the callback.
   */
  P1_EXPORT void SetMessageCallback(RawMessageCallback callback,
                                    void* context) {
    raw_callback_ = callback;
    raw_callback_context_ = context;
  }

  /**
   * @brief Reset the framer and discard all pending data.
   */
  P1_EXPORT void Reset();

  /**
   * @brief Process incoming data.
   *
   * @param buffer A buffer containing data to be framed.
   * @param length_bytes The number of bytes to be framed.
   *
   * @return The total size of all valid, complete messages, or 0 if no messages
   *         were completed.
   */
  P1_EXPORT size_t OnData(const uint8_t* buffer, size_t length_bytes);

 private:
  enum class State {
    SYNC0 = 0,
    SYNC1 = 1,
    HEADER = 2,
    DATA = 3,
  };

#if P1_HAVE_STD_FUNCTION
  MessageCallback callback_;
#endif // P1_HAVE_STD_FUNCTION
  RawMessageCallback raw_callback_ = nullptr;
  void* raw_callback_context_ = nullptr;

  bool warn_on_error_ = true;
  bool is_buffer_managed_ = false;
  uint8_t* buffer_{nullptr};
  uint32_t capacity_bytes_{0};

  State state_{State::SYNC0};
  uint32_t next_byte_index_{0};
  uint32_t current_message_size_{0};

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
  int32_t OnByte(bool quiet);

  /**
   * @brief Perform a resynchronization operation starting at `buffer_[1]`.
   *
   * @return The total size of all valid, complete messages, or 0 if no messages
   *         were completed.
   */
  uint32_t Resync();

  /**
   * @brief Free the @ref buffer_ if it's being managed internally.
   */
  void ClearManagedBuffer();
};

} // namespace parsers
} // namespace fusion_engine
} // namespace point_one
