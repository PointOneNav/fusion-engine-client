from ..messages import MessageHeader, MessagePayload


class FusionEngineEncoder:
    """!
    @brief Helper class for serializing FusionEngine messages.

    @post
    Takes instances of MessagePayload and returns the serialized header+payload
    as a byte array. Increments a sequence_number which it updates in each
    header.
    """

    def __init__(self):
        self.sequence_number = 0

    def encode_message(self, message: MessagePayload, source_identifier=0) -> (bytes):
        """!
        @brief Serialize a message with valid header and payload.

        @post
        The header will set the CRC, message type, sequence number, source
        identifier, and message version. The sequence_number is incremented
        each time this is called.

        @param message The MessagePayload to serialize.

        @return A `bytes` object containing the serialized message.
        """
        header = MessageHeader(message.get_type())
        header.message_version = message.get_version()
        header.sequence_number = self.sequence_number
        header.source_identifier = source_identifier
        self.sequence_number += 1

        message_data = message.pack()

        return header.pack(payload=message_data)
