/**************************************************************************/ /**
 * @brief RTCM 3 message framer.
 * @file
 ******************************************************************************/

#pragma once

#include <cstddef> // For size_t
#include <cstdint>

#include "point_one/fusion_engine/common/portability.h" // For macros.

namespace point_one {
namespace rtcm {

/**
 * @brief Frame and validate incoming RTCM 3 messages.
 *
 * This class locates and validates RTCM 3 messages within a stream of binary
 * data. Data may be stored in an internally allocated buffer, or in an external
 * buffer supplied by the user.
 *
 * The callback function provided to @ref SetMessageCallback() will be called
 * each time a complete message is received. Any messages that do not pass the
 * CRC check, or that are too big to be stored in the data buffer, will be
 * discarded.
 *
 * Example usage:
 * ```cpp
 * void MessageReceived(uint16_t message_type, const void* data, size_t data_len) {
 *   ...
 * }
 *
 * RTCMFramer framer(1024);
 * framer.SetMessageCallback(MessageReceived);
 * framer.OnData(my_data, my_data_size);
 * ```
 */
class P1_EXPORT RTCMFramer {
 public:
  using MessageCallback = void (*)(uint16_t, const void*, size_t);

  /**
   * @brief Construct a framer instance with no buffer allocated.
   *
   * @note
   * You must call @ref SetBuffer() to assign a buffer, otherwise all incoming
   * data will be discarded.
   */
  RTCMFramer() = default;

  /**
   * @brief Construct a framer instance with an internally allocated buffer.
   *
   * @param capacity_bytes The maximum framing buffer capacity (in bytes).
   */
  explicit RTCMFramer(size_t capacity_bytes)
      : RTCMFramer(nullptr, capacity_bytes) {}

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
  RTCMFramer(void* buffer, size_t capacity_bytes);

  ~RTCMFramer();

  // Don't allow copying or moving to avoid issues with managed buffer_.
  RTCMFramer(const RTCMFramer&) = delete; // Copy constructor
  RTCMFramer(RTCMFramer&&) = delete; // Move constructor
  RTCMFramer& operator=(const RTCMFramer&) = delete; // Copy assignment operator
  RTCMFramer& operator=(RTCMFramer&&) = delete; // Move assignment operator

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
   * RTCM message preamble is expected to appear in the non-RTCM content
   * occasionally.
   *
   * @param enabled If `true`, issue warnings on errors.
   */
  void WarnOnError(bool enabled) { warn_on_error_ = enabled; }

  /**
   * @brief Specify a function to be called when a message is framed.
   *
   * @param callback The function to be called with the message header and a
   *        pointer to the message payload.
   */
  void SetMessageCallback(MessageCallback callback) { callback_ = callback; }

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

  /**
   * @brief Get the number of decoded messages.
   *
   * @return The number of RTCM messages successfully decoded.
   */
  uint32_t GetNumDecodedMessages() const { return decoded_msg_count_; }

  /**
   * @brief Get the number of preamble synchronizations that resulted in errors.
   *
   * This is not an accurate count of failed messages since the RTCM preamble is
   * not unique and may appear anywhere in the data stream, but gives an
   * approximate count.
   *
   * @return The number of length or CRC failures found in decoding so far.
   */
  uint32_t GetNumErrors() const { return error_count_; }

 private:
  enum class State {
    SYNC = 0,
    HEADER = 1,
    DATA = 2,
  };

  MessageCallback callback_ = nullptr;

  bool warn_on_error_ = true;
  bool is_buffer_managed_ = false;
  uint8_t* buffer_{nullptr};
  uint32_t capacity_bytes_{0};

  State state_{State::SYNC};
  uint32_t next_byte_index_{0};
  size_t current_message_size_{0};

  uint32_t error_count_{0};
  uint32_t decoded_msg_count_{0};

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

} // namespace rtcm
} // namespace point_one
