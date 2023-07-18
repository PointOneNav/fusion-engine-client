/**************************************************************************/ /**
 * @brief GNSS corrections messages.
 * @file
 ******************************************************************************/

#pragma once

#include "point_one/fusion_engine/messages/defs.h"

namespace point_one {
namespace fusion_engine {
namespace messages {

// Enforce 4-byte alignment and packing of all data structures and values.
// Floating point values are aligned on platforms that require it. This is done
// with a combination of setting struct attributes, and manual alignment
// within the definitions. See the "Message Packing" section of the README.
#pragma pack(push, 1)

/**
 * @defgroup gnss_corrections GNSS Corrections Message Definitions
 * @brief Messages containing GNSS corrections.
 * @ingroup messages
 *
 * See also @ref messages.
 */

/**
 * @brief L-band frame contents (@ref MessageType::LBAND_FRAME, version 1.0).
 * @ingroup gnss_corrections
 */
struct P1_ALIGNAS(4) LBandFrameMessage : public MessagePayload {
  static constexpr MessageType MESSAGE_TYPE = MessageType::LBAND_FRAME;
  static constexpr uint8_t MESSAGE_VERSION = 0;

  /**
   * The system time when the frame was received (in nanoseconds). Note that
   * this is not synchronized to other P1 systems or GNSS.
   */
  int64_t system_time_ns = 0;

  /** Number of bytes in this data payload. */
  uint16_t user_data_size_bytes = 0;

  /** Count of bit errors found in the data frame. */
  uint16_t bit_error_count = 0;

  /** Power of the signal (dB). */
  uint8_t signal_power_db = 0;

  uint8_t reserved[3] = {0};

  /**
   * The offset from the center frequency (Hz). This includes effects from user
   * motion, receiver clock, and satellite clock errors.
   */
  float doppler_hz = 0;

  /**
   * The beginning of the demodulated L-band frame data.
   */
  // uint8_t data_payload[0];
};

#pragma pack(pop)

} // namespace messages
} // namespace fusion_engine
} // namespace point_one
