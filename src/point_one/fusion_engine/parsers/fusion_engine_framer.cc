/**************************************************************************/ /**
 * @brief FusionEngine message framer.
 * @file
 ******************************************************************************/

#define P1_VMODULE_NAME fusion_engine_framer

#include "point_one/fusion_engine/parsers/fusion_engine_framer.h"

#include <cstring> // For memmove()
#include <iomanip>
#include <ostream>

#include "point_one/fusion_engine/common/logging.h"
#include "point_one/fusion_engine/messages/crc.h"

using namespace point_one::fusion_engine::messages;
using namespace point_one::fusion_engine::parsers;

/******************************************************************************/
class PrintableByte {
 public:
  uint8_t byte_;

  PrintableByte(uint8_t byte) : byte_(byte) {}

  friend std::ostream& operator<<(std::ostream& stream,
                                  const PrintableByte& obj) {
    stream << "0x" << std::hex << std::setfill('0') << std::setw(2)
           << (unsigned)obj.byte_ << std::dec;
    if (obj.byte_ >= 0x20 && obj.byte_ <= 0x7E) {
      stream << " ('" << (char)obj.byte_ << "')";
    } else {
      stream << " (---)";
    }
    return stream;
  }
};

/******************************************************************************/
FusionEngineFramer::FusionEngineFramer(void* buffer, size_t capacity_bytes) {
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
void FusionEngineFramer::SetBuffer(void* buffer, size_t capacity_bytes) {
  if (capacity_bytes < sizeof(MessageHeader)) {
    LOG(ERROR) << "FusionEngine framing buffer too small. [capacity="
               << capacity_bytes << " B, min=" << sizeof(MessageHeader)
               << " B]";
    return;
  }

  if (buffer == nullptr) {
    managed_buffer_.reset(new uint8_t[capacity_bytes]);
    buffer = managed_buffer_.get();
  } else if (buffer != managed_buffer_.get()) {
    managed_buffer_.reset(nullptr);
  }

  // Enforce 4B alignment at the beginning of the buffer.
  uint8_t* buffer_unaligned = static_cast<uint8_t*>(buffer);
  buffer_ = reinterpret_cast<uint8_t*>(
      (reinterpret_cast<size_t>(buffer_unaligned) + 3) &
      ~(static_cast<size_t>(3)));
  capacity_bytes_ = capacity_bytes - (buffer_ - buffer_unaligned);

  Reset();
}

/******************************************************************************/
void FusionEngineFramer::Reset() {
  state_ = State::SYNC0;
  next_byte_index_ = 0;
  current_message_size_ = 0;
}

/******************************************************************************/
size_t FusionEngineFramer::OnData(const uint8_t* buffer, size_t length_bytes) {
  // Process each byte. If the user-supplied buffer was too small, we can't
  // parse messages.
  if (buffer_ != nullptr) {
    VLOG(2) << "Received " << length_bytes << " bytes.";
    size_t total_dispatched_bytes = 0;
    for (size_t idx = 0; idx < length_bytes; ++idx) {
      uint8_t byte = buffer[idx];
      buffer_[next_byte_index_++] = byte;
      p1_ssize_t dispatched_message_size = OnByte(false);
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
p1_ssize_t FusionEngineFramer::OnByte(bool quiet) {
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
  if (state_ == State::SYNC0) {
    VLOG(4) << "Searching for sync byte 0. [byte=" << PrintableByte(byte)
            << "]";
    if (byte == MessageHeader::SYNC0) {
      VLOG(4) << "Found sync byte 0.";
      state_ = State::SYNC1;
    } else {
      --next_byte_index_;
    }
  }
  // Look for the second sync byte.
  else if (state_ == State::SYNC1) {
    VLOG(4) << "Searching for sync byte 1. [byte=" << PrintableByte(byte)
            << "]";
    if (byte == MessageHeader::SYNC0) {
      VLOG(4) << "Found duplicate sync byte 0.";
      state_ = State::SYNC1;
      --next_byte_index_;
    } else if (byte == MessageHeader::SYNC1) {
      VLOG(3) << "Preamble found. Waiting for header.";
      state_ = State::HEADER;
    } else {
      VLOG(4) << "Did not find sync byte 1. Resetting. [byte="
              << PrintableByte(byte) << "]";
      state_ = State::SYNC0;
      next_byte_index_ = 0;
      current_message_size_ = 0;
    }
  }
  // Search for a message header.
  else if (state_ == State::HEADER) {
    VLOG(4) << "Received " << next_byte_index_ << "/" << sizeof(MessageHeader)
            << " header bytes. [byte=" << PrintableByte(byte) << "]";

    // Check if the header is complete.
    if (next_byte_index_ == sizeof(MessageHeader)) {
      // Compute the full message size. If the message is too large to fit in
      // the buffer, we cannot parse it. Otherwise, start collecting the
      // message payload.
      auto* header = reinterpret_cast<MessageHeader*>(buffer_);
      current_message_size_ =
          sizeof(MessageHeader) + header->payload_size_bytes;
      VLOG(3) << "Header complete. Waiting for payload. [message="
              << header->message_type << " (" << (unsigned)header->message_type
              << "), seq=" << header->sequence_number
              << ", payload_size=" << header->payload_size_bytes << " B]";
      if (current_message_size_ <= capacity_bytes_) {
        // If there's no payload, do the CRC check now.
        if (header->payload_size_bytes == 0) {
          VLOG(3) << "Message has no payload. Checking CRC.";
          crc_check_needed = true;
        }
        // Otherwise, collect the payload, then do the CRC check.
        else {
          state_ = State::DATA;
        }
      } else {
        if (quiet) {
          VLOG(2) << "Message too large for buffer. [size="
                  << current_message_size_
                  << " B, buffer_capacity=" << capacity_bytes_ << " B]";
        } else {
          LOG(WARNING) << "Message too large for buffer. [size="
                       << current_message_size_
                       << " B, buffer_capacity=" << capacity_bytes_ << " B]";
        }

        state_ = State::SYNC0;
        return -1;
      }
    }
  }
  // Collect the message payload.
  else if (state_ == State::DATA) {
    VLOG(4) << "Received " << next_byte_index_ << "/" << current_message_size_
            << " message bytes (" << next_byte_index_ - sizeof(MessageHeader)
            << "/" << current_message_size_ - sizeof(MessageHeader)
            << " payload bytes). [byte=" << PrintableByte(byte) << "]";

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
    uint32_t crc = CalculateCRC(buffer_);
    auto* header = reinterpret_cast<MessageHeader*>(buffer_);
    if (crc == header->crc) {
      VLOG(1) << "CRC passed. Dispatching message. [message="
              << header->message_type << " (" << (unsigned)header->message_type
              << "), seq=" << header->sequence_number
              << ", size=" << current_message_size_ << " B, crc=0x" << std::hex
              << std::setfill('0') << std::setw(8) << crc << "]";
      if (callback_) {
        auto* payload = reinterpret_cast<uint8_t*>(header + 1);
        callback_(*header, payload);
      }
      state_ = State::SYNC0;
      return static_cast<p1_ssize_t>(current_message_size_);
    } else {
      if (quiet) {
        VLOG(2) << "CRC check failed. [message=" << header->message_type << " ("
                << (unsigned)header->message_type
                << "), seq=" << header->sequence_number
                << ", size=" << current_message_size_ << " B, crc=0x"
                << std::hex << std::setfill('0') << std::setw(8) << crc
                << ", expected_crc=0x" << std::setw(8) << header->crc << "]";
      } else {
        LOG(WARNING) << "CRC check failed. [message=" << header->message_type
                     << " (" << (unsigned)header->message_type
                     << "), seq=" << header->sequence_number
                     << ", size=" << current_message_size_ << " B, crc=0x"
                     << std::hex << std::setfill('0') << std::setw(8) << crc
                     << ", expected_crc=0x" << std::setw(8) << header->crc
                     << "]";
      }
      state_ = State::SYNC0;
      return -1;
    }
  }

  // No messages completed.
  return 0;
}

/******************************************************************************/
size_t FusionEngineFramer::Resync() {
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
  size_t available_bytes = next_byte_index_;
  VLOG(1) << "Attempting resynchronization. [" << available_bytes - 1
          << " candidate bytes]";
  size_t total_message_size = 0;
  state_ = State::SYNC0;
  next_byte_index_ = 0;
  for (size_t offset = 1; offset < available_bytes; ++offset) {
    uint8_t current_byte = buffer_[offset];

    // Skip forward until we see a SYNC0.
    if (state_ == State::SYNC0) {
      if (current_byte == MessageHeader::SYNC0) {
        VLOG(1) << "Candidate message start found @ offset " << offset << "/"
                << available_bytes << ".";
        // Shift all of the data left in the buffer.
        available_bytes -= offset;
        std::memmove(buffer_, buffer_ + offset, available_bytes);
        offset = 0;
      } else {
        VLOG(4) << "Skipping non-sync byte 0 @ offset " << offset << "/"
                << available_bytes << ". [byte=" << PrintableByte(current_byte)
                << "]";
        continue;
      }
    }

    // Process this byte. If we end up back in the SYNC0 state, either A) the
    // SYNC0 we found was a valid message and got dispatched, or B) was not the
    // start of a valid message.
    //
    // In (A), valid_message == true, so we know we can just keep going.
    //
    // In (B), valid_message == false. In that case we'll go back to the next
    // byte after we located the sync and see if there's another one.
    //
    // Note that next_byte_index_ always points to the next open slot, i.e.,
    // one byte _after_ the current byte.
    next_byte_index_ = offset + 1;
    p1_ssize_t message_size = OnByte(true);

    if (state_ == State::SYNC0) {
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
        --available_bytes;
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
