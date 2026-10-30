from typing import Dict, Type, Union

import numpy as np

from ..messages import MessageHeader, MessagePayload


class MessageBatch(object):
    """!
    @brief A set of FusionEngine messages from a file, read all at once into numpy arrays.

    A batch is returned by @ref MixedLogReader.read_batch(). It holds the header of every message as numpy arrays, one
    entry per message in file order. Payloads are read from the file only on request: one message at a time with
    @ref get_payload(), or the fields of every message at once with @ref unpack_array().

    Use numpy indexing to select messages, e.g., `batch[batch.message_type == MessageType.POSE]`.
    """

    # The number of messages to gather at once. Gathering builds a temporary array of one 8-byte offset per byte read,
    # so this bounds its size.
    _GATHER_CHUNK_SIZE = 1 << 18

    def __init__(self, buffer: np.ndarray, offset: np.ndarray, headers: np.ndarray, p1_time: np.ndarray,
                 message_index: np.ndarray):
        """!
        @brief Construct a batch from data already read by @ref MixedLogReader.read_batch().

        @param buffer The contents of the data file, as a `uint8` array.
        @param offset The file offset of each message (in bytes).
        @param headers The header of each message, as an array of @ref MessageHeader._NUMPY_DTYPE.
        @param p1_time The P1 time of each message (in seconds), or `NaN` if the message has none.
        @param message_index The 0-based index of each message within the file.
        """
        self._buffer = buffer
        self._headers = headers
        self.offset = offset
        self.p1_time = p1_time
        self.message_index = message_index

    @classmethod
    def _read_headers(cls, buffer: np.ndarray, offset: np.ndarray) -> np.ndarray:
        """!
        @brief Read the header of every message at the specified offsets.

        @param buffer The contents of the data file, as a `uint8` array.
        @param offset The file offset of each message (in bytes).

        @return An array of @ref MessageHeader._NUMPY_DTYPE, one entry per message.
        """
        return cls._gather(buffer, offset, MessageHeader._NUMPY_DTYPE)

    @property
    def message_type(self) -> np.ndarray:
        return self._headers['message_type']

    @property
    def message_version(self) -> np.ndarray:
        return self._headers['message_version']

    @property
    def sequence_number(self) -> np.ndarray:
        return self._headers['sequence_number']

    @property
    def source_identifier(self) -> np.ndarray:
        return self._headers['source_identifier']

    @property
    def payload_size_bytes(self) -> np.ndarray:
        return self._headers['payload_size_bytes']

    @property
    def size_bytes(self) -> np.ndarray:
        """!
        @brief Get the size of each complete message, header included (in bytes).
        """
        return MessageHeader.calcsize() + self.payload_size_bytes.astype(np.int64)

    def get_bytes(self, i: int) -> memoryview:
        """!
        @brief Get one complete serialized message, header included, without copying it.

        @param i The index of the message within this batch.

        @return A `memoryview` of the message.
        """
        start = int(self.offset[i])
        return memoryview(self._buffer[start:start + int(self.size_bytes[i])])

    def get_payload(self, i: int) -> memoryview:
        """!
        @brief Get the serialized payload of one message without copying it.

        @param i The index of the message within this batch.

        @return A `memoryview` of the payload.
        """
        start = int(self.offset[i]) + MessageHeader.calcsize()
        return memoryview(self._buffer[start:start + int(self.payload_size_bytes[i])])

    def get_payload_fields(self, dtype: Union[np.dtype, list]) -> np.ndarray:
        """!
        @brief Read fixed-size fields from the start of every message's payload at once.

        This is intended for use by @ref MessagePayload.unpack_array() implementations.

        @param dtype A numpy structured type describing the fields at the start of the payload.

        @return An array of `dtype`, one entry per message.
        """
        dtype = np.dtype(dtype)
        if np.any(self.payload_size_bytes < dtype.itemsize):
            raise ValueError('Payload too small for the requested fields. [size=%d B, min=%d B]' %
                             (np.min(self.payload_size_bytes), dtype.itemsize))
        return self._gather(self._buffer, self.offset + MessageHeader.calcsize(), dtype)

    def unpack_array(self, cls: Type[MessagePayload]) -> Dict[str, np.ndarray]:
        """!
        @brief Deserialize the fields of every message in the batch at once.

        See @ref MessagePayload.unpack_array().

        @param cls The @ref MessagePayload class of the messages. Every message in the batch must be of this type.

        @return A `dict` mapping field names to numpy arrays, one entry per message.
        """
        if np.any(self.message_type != int(cls.get_type())):
            raise ValueError('Batch contains messages other than %s. Select them first, e.g., '
                             'batch[batch.message_type == %s].' % (cls.__name__, cls.get_type()))
        return cls.unpack_array(self)

    def __len__(self):
        return len(self.offset)

    def __getitem__(self, key) -> 'MessageBatch':
        """!
        @brief Select a subset of the messages using numpy indexing (a boolean mask, indices, or a slice).

        @param key The numpy index.

        @return A new @ref MessageBatch containing the selected messages.
        """
        return MessageBatch(buffer=self._buffer, offset=self.offset[key], headers=self._headers[key],
                            p1_time=self.p1_time[key], message_index=self.message_index[key])

    @classmethod
    def _gather(cls, buffer: np.ndarray, offset: np.ndarray, dtype: np.dtype) -> np.ndarray:
        result = np.empty(len(offset), dtype=dtype)
        byte_offsets = np.arange(dtype.itemsize)
        for start in range(0, len(offset), cls._GATHER_CHUNK_SIZE):
            chunk = offset[start:start + cls._GATHER_CHUNK_SIZE].astype(np.int64)
            result[start:start + len(chunk)] = buffer[chunk[:, None] + byte_offsets].view(dtype).reshape(-1)
        return result
