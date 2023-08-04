/**************************************************************************/ /**
 * @brief RTCM 3 message framer.
 * @file
 ******************************************************************************/

#define P1_VMODULE_NAME rtcm_framer

#include "rtcm_framer.h"

#include <cstring> // For memmove()
#if P1_HAVE_STD_OSTREAM
#  include <iomanip>
#  include <ostream>
#  include <type_traits>
#endif

#include "point_one/fusion_engine/common/logging.h"

using namespace point_one::rtcm;

static constexpr uint8_t RTCM3_PREAMBLE = 0xD3;

/**
 * Transport header:
 *   Preamble = 8 bits
 *   Reserved = 6 bits
 *   Message Length = 10 bits
 *   Variable Length Data Message (not counted)
 */
static constexpr size_t RTCM_HEADER_BYTES = 3;
/** Qualcomm 24-bit CRC */
static constexpr size_t RTCM_CRC_BYTES = 3;

static constexpr size_t RTCM_OVERHEAD_BYTES =
    RTCM_HEADER_BYTES + RTCM_CRC_BYTES;

static constexpr size_t RTCM_MAX_SIZE_BYTES =
    RTCM_HEADER_BYTES + 1023 + RTCM_CRC_BYTES;

static constexpr uint32_t RTCM_CRC24Q[256] = {
    0x000000, 0x864CFB, 0x8AD50D, 0x0C99F6, 0x93E6E1, 0x15AA1A, 0x1933EC,
    0x9F7F17, 0xA18139, 0x27CDC2, 0x2B5434, 0xAD18CF, 0x3267D8, 0xB42B23,
    0xB8B2D5, 0x3EFE2E, 0xC54E89, 0x430272, 0x4F9B84, 0xC9D77F, 0x56A868,
    0xD0E493, 0xDC7D65, 0x5A319E, 0x64CFB0, 0xE2834B, 0xEE1ABD, 0x685646,
    0xF72951, 0x7165AA, 0x7DFC5C, 0xFBB0A7, 0x0CD1E9, 0x8A9D12, 0x8604E4,
    0x00481F, 0x9F3708, 0x197BF3, 0x15E205, 0x93AEFE, 0xAD50D0, 0x2B1C2B,
    0x2785DD, 0xA1C926, 0x3EB631, 0xB8FACA, 0xB4633C, 0x322FC7, 0xC99F60,
    0x4FD39B, 0x434A6D, 0xC50696, 0x5A7981, 0xDC357A, 0xD0AC8C, 0x56E077,
    0x681E59, 0xEE52A2, 0xE2CB54, 0x6487AF, 0xFBF8B8, 0x7DB443, 0x712DB5,
    0xF7614E, 0x19A3D2, 0x9FEF29, 0x9376DF, 0x153A24, 0x8A4533, 0x0C09C8,
    0x00903E, 0x86DCC5, 0xB822EB, 0x3E6E10, 0x32F7E6, 0xB4BB1D, 0x2BC40A,
    0xAD88F1, 0xA11107, 0x275DFC, 0xDCED5B, 0x5AA1A0, 0x563856, 0xD074AD,
    0x4F0BBA, 0xC94741, 0xC5DEB7, 0x43924C, 0x7D6C62, 0xFB2099, 0xF7B96F,
    0x71F594, 0xEE8A83, 0x68C678, 0x645F8E, 0xE21375, 0x15723B, 0x933EC0,
    0x9FA736, 0x19EBCD, 0x8694DA, 0x00D821, 0x0C41D7, 0x8A0D2C, 0xB4F302,
    0x32BFF9, 0x3E260F, 0xB86AF4, 0x2715E3, 0xA15918, 0xADC0EE, 0x2B8C15,
    0xD03CB2, 0x567049, 0x5AE9BF, 0xDCA544, 0x43DA53, 0xC596A8, 0xC90F5E,
    0x4F43A5, 0x71BD8B, 0xF7F170, 0xFB6886, 0x7D247D, 0xE25B6A, 0x641791,
    0x688E67, 0xEEC29C, 0x3347A4, 0xB50B5F, 0xB992A9, 0x3FDE52, 0xA0A145,
    0x26EDBE, 0x2A7448, 0xAC38B3, 0x92C69D, 0x148A66, 0x181390, 0x9E5F6B,
    0x01207C, 0x876C87, 0x8BF571, 0x0DB98A, 0xF6092D, 0x7045D6, 0x7CDC20,
    0xFA90DB, 0x65EFCC, 0xE3A337, 0xEF3AC1, 0x69763A, 0x578814, 0xD1C4EF,
    0xDD5D19, 0x5B11E2, 0xC46EF5, 0x42220E, 0x4EBBF8, 0xC8F703, 0x3F964D,
    0xB9DAB6, 0xB54340, 0x330FBB, 0xAC70AC, 0x2A3C57, 0x26A5A1, 0xA0E95A,
    0x9E1774, 0x185B8F, 0x14C279, 0x928E82, 0x0DF195, 0x8BBD6E, 0x872498,
    0x016863, 0xFAD8C4, 0x7C943F, 0x700DC9, 0xF64132, 0x693E25, 0xEF72DE,
    0xE3EB28, 0x65A7D3, 0x5B59FD, 0xDD1506, 0xD18CF0, 0x57C00B, 0xC8BF1C,
    0x4EF3E7, 0x426A11, 0xC426EA, 0x2AE476, 0xACA88D, 0xA0317B, 0x267D80,
    0xB90297, 0x3F4E6C, 0x33D79A, 0xB59B61, 0x8B654F, 0x0D29B4, 0x01B042,
    0x87FCB9, 0x1883AE, 0x9ECF55, 0x9256A3, 0x141A58, 0xEFAAFF, 0x69E604,
    0x657FF2, 0xE33309, 0x7C4C1E, 0xFA00E5, 0xF69913, 0x70D5E8, 0x4E2BC6,
    0xC8673D, 0xC4FECB, 0x42B230, 0xDDCD27, 0x5B81DC, 0x57182A, 0xD154D1,
    0x26359F, 0xA07964, 0xACE092, 0x2AAC69, 0xB5D37E, 0x339F85, 0x3F0673,
    0xB94A88, 0x87B4A6, 0x01F85D, 0x0D61AB, 0x8B2D50, 0x145247, 0x921EBC,
    0x9E874A, 0x18CBB1, 0xE37B16, 0x6537ED, 0x69AE1B, 0xEFE2E0, 0x709DF7,
    0xF6D10C, 0xFA48FA, 0x7C0401, 0x42FA2F, 0xC4B6D4, 0xC82F22, 0x4E63D9,
    0xD11CCE, 0x575035, 0x5BC9C3, 0xDD8538};

/******************************************************************************/
static uint32_t CRC24Hash(const uint8_t* data, size_t len) {
  size_t i;
  unsigned crc = 0;

  for (i = 0; i < len; i++) {
    crc = (crc << 8) ^ RTCM_CRC24Q[data[i] ^ (unsigned char)(crc >> 16)];
  }

  crc = (crc & 0x00ffffff);
  return crc;
}

// Note: Assuming we're on a little endian system.

/******************************************************************************/
static constexpr uint16_t EndianSwap16(const uint8_t* num_ptr) {
  return (num_ptr[0] << 8) | (num_ptr[1] << 0);
}

/******************************************************************************/
static constexpr uint32_t EndianSwap24(const uint8_t* num_ptr) {
  return (num_ptr[0] << 16) | (num_ptr[1] << 8) | (num_ptr[2] << 0);
}

/******************************************************************************/
template <typename T>
class HexPrintableIntegerInst {
 public:
  HexPrintableIntegerInst(T value) : value_(value) {}

  template <typename U> // all instantiations of this template are my friends
  friend p1_ostream& operator<<(p1_ostream&, const HexPrintableIntegerInst<U>&);

 private:
  const T value_;
};

/******************************************************************************/
template <typename T>
p1_ostream& operator<<(p1_ostream& stream,
                       const HexPrintableIntegerInst<T>& obj) {
#if P1_HAVE_STD_OSTREAM
  static_assert(std::is_integral<T>::value, "Integer required.");

  stream << "0x" << std::hex << std::setfill('0') << std::setw(sizeof(obj) * 2);

  if (sizeof(T) == 1) {
    stream << (((unsigned)obj.value_) & 0xFF);
  } else {
    stream << obj.value_;
  }

  stream << std::dec;

  if (sizeof(obj) == 1) {
    if (obj.value_ >= 0x20 && obj.value_ <= 0x7E) {
      stream << " ('" << (char)obj.value_ << "')";
    } else {
      stream << " (---)";
    }
  }
#endif
  return stream;
}

/**
 * @brief Wrap an integer so it will be output to a stream as its hex
 *        representation.
 *
 * For example:
 *
 * ```cpp
 * std::cout << HexPrintableValue((int16_t)-255) << std::endl;
 * std::cout << HexPrintableValue((uint32_t)255) << std::endl;
 * std::cout << HexPrintableValue((uint8_t)48) << std::endl;
 * ```
 *
 * generates the following output:
 *
 * ```
 * 0xff01
 * 0x000000ff
 * 0x30 ('0')
 * ```
 *
 * @tparam T The type of the value parameter (inferred implicitly).
 * @param value The integer value to wrap.
 *
 * @return The wrapped integer that can be used in an @ref p1_ostream.
 */
template <typename T>
HexPrintableIntegerInst<T> HexPrintableInteger(T value) {
  return HexPrintableIntegerInst<T>(value);
}

/******************************************************************************/
RTCMFramer::RTCMFramer(void* buffer, size_t capacity_bytes) {
  // Allocate a buffer internally.
  if (buffer == nullptr) {
    // We enforce 4B alignment, so we need to allocate 3 extra bytes to
    // guarantee that the buffer has at least the requested capacity.
    SetBuffer(nullptr, capacity_bytes + 3);
  }
  // Use user-provided storage.
  else {
    SetBuffer(buffer, capacity_bytes);
  }
}

/******************************************************************************/
RTCMFramer::~RTCMFramer() { ClearManagedBuffer(); }

/******************************************************************************/
void RTCMFramer::SetBuffer(void* buffer, size_t capacity_bytes) {
  if (capacity_bytes < RTCM_OVERHEAD_BYTES) {
    LOG(ERROR) << "RTCM framing buffer too small. [capacity=" << capacity_bytes
               << " B, min=" << RTCM_OVERHEAD_BYTES << " B]";
    return;
  }
  // Restrict the buffer capacity to 2^31 bytes. We don't expect to ever have a
  // single message anywhere near that large, and don't expect users to ever
  // pass in a buffer that size. Using uint32_t instead of size_t internally
  // makes it easier to guarantee behavior between 64b and 32b architectures. We
  // do 2^31, not 2^32, so we can use int32_t for return values internally.
  else if (capacity_bytes > 0x7FFFFFFF) {
    LOG(WARNING) << "Limiting buffer capacity to 2^31 B. [original_capacity="
                 << capacity_bytes << " B]";
    capacity_bytes = 0x7FFFFFFF;
  }

  ClearManagedBuffer();
  if (buffer == nullptr) {
    buffer = new uint8_t[capacity_bytes];
    is_buffer_managed_ = true;
  }

  // Enforce 4B alignment at the beginning of the buffer.
  uint8_t* buffer_unaligned = static_cast<uint8_t*>(buffer);
  buffer_ = reinterpret_cast<uint8_t*>(
      (reinterpret_cast<size_t>(buffer_unaligned) + 3) &
      ~(static_cast<size_t>(3)));
  capacity_bytes_ =
      static_cast<uint32_t>(capacity_bytes - (buffer_ - buffer_unaligned));

  Reset();
}

/******************************************************************************/
void RTCMFramer::Reset() {
  state_ = State::SYNC;
  next_byte_index_ = 0;
  current_message_size_ = 0;
  error_count_ = 0;
  decoded_msg_count_ = 0;
}

/******************************************************************************/
size_t RTCMFramer::OnData(const uint8_t* buffer, size_t length_bytes) {
  // Process each byte. If the user-supplied buffer was too small, we can't
  // parse messages.
  if (buffer_ != nullptr) {
    VLOG(2) << "Received " << length_bytes << " bytes.";
    size_t total_dispatched_bytes = 0;
    for (size_t idx = 0; idx < length_bytes; ++idx) {
      uint8_t byte = buffer[idx];
      buffer_[next_byte_index_++] = byte;
      int32_t dispatched_message_size = OnByte(false);
      if (dispatched_message_size == 0) {
        // Waiting for more data. Nothing to do.
      } else if (dispatched_message_size > 0) {
        // Message framed successfully. Reset for the next one.
        next_byte_index_ = 0;
        total_dispatched_bytes += (size_t)dispatched_message_size;
      } else if (next_byte_index_ > 0) {
        // If OnByte() indicated an error (size < 0) and there is still data in
        // the buffer, either the CRC failed or the payload was too big to fit
        // in the buffer.
        //
        // In either case, it is possible we found what looked like the preamble
        // somewhere within the data stream but it wasn't actually a valid
        // message. In that case, the data we processed may contain the start of
        // a valid message, or even one or more complete messages, starting
        // somewhere after byte 0. Perform a resync operation to find valid
        // messages.
        total_dispatched_bytes += Resync();
      } else {
        // OnByte() caught an unrecoverable error and reset the buffer. Nothing
        // to do.
      }
    }
    return total_dispatched_bytes;
  } else {
    return 0;
  }
}

/******************************************************************************/
int32_t RTCMFramer::OnByte(bool quiet) {
  // User-supplied buffer was too small. Can't parse messages.
  if (buffer_ == nullptr) {
    return 0;
  }

  // If warnings are disabled, run in quiet mode.
  if (!warn_on_error_) {
    quiet = true;
  }

  // Pull out the byte being processed.
  if (next_byte_index_ == 0) {
    LOG(ERROR) << "Byte not found in buffer.";
    return 0;
  }

  uint8_t byte = buffer_[next_byte_index_ - 1];

  // Look for the first sync byte.
  //
  // Note that we always put the first byte at offset 0 in the buffer, and the
  // buffer is guaranteed to be 4B-aligned by the constructor, so the framed
  // message will always be 4B aligned.
  bool crc_check_needed = false;
  if (state_ == State::SYNC) {
    VLOG(4) << "Searching for sync byte. [byte=" << HexPrintableInteger(byte)
            << "]";
    if (byte == RTCM3_PREAMBLE) {
      VLOG(4) << "Found sync byte 0.";
      state_ = State::HEADER;
    } else {
      --next_byte_index_;
    }
  }
  // Search for a message header.
  else if (state_ == State::HEADER) {
    VLOG(4) << "Received " << next_byte_index_ << "/" << RTCM_HEADER_BYTES
            << " header bytes. [byte=" << HexPrintableInteger(byte) << "]";

    // Check if the header is complete.
    if (next_byte_index_ == RTCM_HEADER_BYTES) {
      // Compute the full message size. If the message is too large to fit in
      // the buffer, we cannot parse it. Otherwise, start collecting the
      // message payload.
      //
      // Note that while we compute the current_message_size_ here, we
      // intentionally do the "too big" check below with the payload size. That
      // way we implicitly handle cases where the payload is large enough to
      // cause current_message_size_ to overflow. Normally, this won't happen
      // for legit packets that are just too big for the user's buffer, but it
      // could happen on a bogus header if we find the preamble randomly in an
      // incoming byte stream. The buffer capacity is always
      // >=RTCM_OVERHEAD_BYTES, so the subtraction will never be negative.
      /**
       * Transport header (big endian):
       *   Preamble = 8 bits
       *   Reserved = 6 bits
       *   Message Length = 10 bits
       */
      uint16_t header_byte_1_2_le = EndianSwap16(buffer_ + 1);
      uint16_t payload_size_bytes = header_byte_1_2_le & 0x3FF;
      current_message_size_ = payload_size_bytes + RTCM_OVERHEAD_BYTES;
      VLOG(3) << "Header complete. Waiting for payload. [payload_size="
              << payload_size_bytes << " B]";
      if (current_message_size_ <= capacity_bytes_ &&
          current_message_size_ <= RTCM_MAX_SIZE_BYTES) {
        state_ = State::DATA;
      } else {
        error_count_++;
        if (quiet) {
          VLOG(2) << "Message too large for buffer. [size="
                  << current_message_size_
                  << " B (payload=" << payload_size_bytes
                  << " B), buffer_capacity=" << capacity_bytes_
                  << " B (max_payload=" << capacity_bytes_ - RTCM_OVERHEAD_BYTES
                  << " B)]";
        } else {
          LOG(WARNING) << "Message too large for buffer. [size="
                       << current_message_size_
                       << " B (payload=" << payload_size_bytes
                       << " B), buffer_capacity=" << capacity_bytes_
                       << " B (max_payload="
                       << capacity_bytes_ - RTCM_OVERHEAD_BYTES << " B)]";
        }

        state_ = State::SYNC;
        return -1;
      }
    }
  }
  // Collect the message payload and CRC.
  else if (state_ == State::DATA) {
    VLOG(4) << "Received " << next_byte_index_ << "/" << current_message_size_
            << " message bytes (" << next_byte_index_ << "/"
            << current_message_size_
            << " payload bytes). [byte=" << HexPrintableInteger(byte) << "]";

    // If we received the full payload, check the CRC and dispatch it.
    if (next_byte_index_ == current_message_size_) {
      VLOG(3) << "Payload complete. Checking CRC.";
      crc_check_needed = true;
    }
  }
  // Illegal state.
  else {
    LOG(ERROR) << "Impossible parsing state.";
    Reset();
    return -1;
  }

  // Payload complete (or message has no payload). Check the CRC.
  if (crc_check_needed) {
    size_t check_size = current_message_size_ - RTCM_CRC_BYTES;
    uint16_t header_byte_3_4_le = EndianSwap16(buffer_ + RTCM_HEADER_BYTES);
    uint16_t message_type = header_byte_3_4_le >> 4;
    uint32_t calculated_crc = CRC24Hash(buffer_, check_size);
    uint32_t crc_expected = EndianSwap24(buffer_ + check_size);
    if (calculated_crc == crc_expected) {
      decoded_msg_count_++;
      VLOG(1) << "CRC passed. Dispatching message. [message=" << message_type
              << ", size=" << current_message_size_
              << " B, crc=" << HexPrintableInteger(crc_expected) << "]";
      if (callback_) {
        callback_(message_type, buffer_, current_message_size_);
      }
      state_ = State::SYNC;
      return static_cast<int32_t>(current_message_size_);
    } else {
      error_count_++;
      if (quiet) {
        VLOG(2) << "CRC check failed. [message=" << message_type
                << ", size=" << current_message_size_
                << " B, crc=" << HexPrintableInteger(calculated_crc)
                << ", expected_crc=" << HexPrintableInteger(crc_expected)
                << "]";
      } else {
        LOG(WARNING) << "CRC check failed. [message=" << message_type
                     << ", size=" << current_message_size_
                     << " B, crc=" << HexPrintableInteger(calculated_crc)
                     << ", expected_crc=" << HexPrintableInteger(crc_expected)
                     << "]";
      }
      state_ = State::SYNC;
      return -1;
    }
  }

  // No messages completed.
  return 0;
}

/******************************************************************************/
uint32_t RTCMFramer::Resync() {
  // If the message preamble shows up randomly somewhere in the data stream, we
  // may sync to it and try to parse a message starting at that arbitrary
  // location. We will eventually detect the bad sync either by CRC failure or
  // because the payload size we extract from the bogus message header is too
  // large.
  //
  // In either case, the bytes we collected - both the bogus header and the
  // payload bytes based on the size in the header - may contain the start of a
  // valid message, or even one or more complete messages. We need to resync and
  // try to find those messages. Any of the following scenarios is possible:
  //   ...validvalidval       <-- Contiguous valid messages
  //   ...valid...valid...val <-- Multiple valid messages, separated by invalid
  //   ...valid...valid...    <-- Similar, but ending with invalid
  //   ...val                 <-- Start of a valid message, no complete messages
  //   ...                    <-- No valid content
  //
  // Ideally, we would search for these messages in-place and avoid shifting the
  // data around in the buffer. However, since we need the messages to be
  // 4B-aligned and there's only a 1-in-4 chance of that happening naturally,
  // we'd have to shift the data 75% of the time regardless.
  //
  // Given that, we simply shift all data left in the buffer and process one
  // message at a time. This is not as efficient, but it's the simplest option.
  uint32_t available_bytes = next_byte_index_;
  VLOG(1) << "Attempting resynchronization. [" << available_bytes - 1
          << " candidate bytes]";
  uint32_t total_message_size = 0;
  state_ = State::SYNC;
  next_byte_index_ = 0;
  for (uint32_t offset = 1; offset < available_bytes; ++offset) {
    uint8_t current_byte = buffer_[offset];

    // Skip forward until we see a SYNC0.
    if (state_ == State::SYNC) {
      if (current_byte == RTCM3_PREAMBLE) {
        VLOG(1) << "Candidate message start found @ offset " << offset << "/"
                << available_bytes << ".";
        // Shift all of the data left in the buffer.
        available_bytes -= offset;
        std::memmove(buffer_, buffer_ + offset, available_bytes);
        offset = 0;
      } else {
        VLOG(4) << "Skipping non-sync byte 0 @ offset " << offset << "/"
                << available_bytes
                << ". [byte=" << HexPrintableInteger(current_byte) << "]";
        continue;
      }
    }

    // Process this byte. If we end up back in the SYNC0 state, either A) the
    // SYNC0 we found was a valid message and got dispatched, or B) was not the
    // start of a valid message.
    //
    // In (A), message_size > 0 indicating there was a valid message, so we know
    // we can just keep going with the rest of the data in the buffer.
    //
    // In (B), message_size == 0. In that case we'll rewind back to the byte
    // just after we located the SYNC0 and see if there's another one.
    //
    // Note that next_byte_index_ always points to the next open slot, i.e.,
    // one byte _after_ the current byte.
    next_byte_index_ = offset + 1;
    int32_t message_size = OnByte(true);

    if (state_ == State::SYNC) {
      // Note that offset will be incremented when we loop around, so we set it
      // to N-1, where N is wherever we want to start searching next.
      if (message_size > 0) {
        total_message_size += message_size;
        offset = message_size - 1;
        VLOG(1)
            << "Resync found a complete message. Continuing search @ offset "
            << offset + 1 << "/" << available_bytes
            << ". [message_size=" << message_size << ", "
            << (available_bytes - message_size - 1)
            << " candidate bytes remaining]";
      } else {
        size_t prev_offset = offset;
        offset = 0;
        VLOG(1) << "Candidate message rejected after " << prev_offset
                << " bytes. Restarting search @ offset " << offset + 1 << "/"
                << available_bytes << ". [" << available_bytes - 1
                << " candidate bytes remaining]";
      }

      next_byte_index_ = 0;
    }
  }

  VLOG(1) << "Resynchronization finished. " << next_byte_index_
          << " bytes remaining in buffer.";

  return total_message_size;
}

/******************************************************************************/
void RTCMFramer::ClearManagedBuffer() {
  if (is_buffer_managed_ && buffer_ != nullptr) {
    delete[] buffer_;
    is_buffer_managed_ = false;
    buffer_ = nullptr;
  }
}
