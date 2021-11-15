from ..messages import MessageHeader, MessagePayload


class FusionEngineEncoder:
    """!
    @brief Helper class for serializing FusionEngine messages.

    This class takes instances of @ref MessagePayload and returns the serialized message content (header + payload) as a
    byte array (`bytes`). It attaches sequence numbers and CRCs automatically to the outbound byte stream.
    """

    def __init__(self):
        """!
        @brief Construct a new encoder instance.
        """
        self.sequence_number = 0

    def encode_message(self, message: MessagePayload, source_identifier: int = 0) -> (bytes):
        """!
        @brief Serialize a message with valid header and payload.

        Construct a header for the specified payload, automatically setting the message type and version from the
        payload object, and populating the message sequence number, source identifier, and CRC. Then serialize both the
        header and payload into a `bytes` object.

        @param message The MessagePayload to serialize.
        @param source_identifier A numeric source identifier to associate with this message (optional).

        @return A `bytes` object containing the serialized message.
        """
        header = MessageHeader(message.get_type())
        header.message_version = message.get_version()
        header.sequence_number = self.sequence_number
        header.source_identifier = source_identifier
        self.sequence_number += 1

        message_data = message.pack()

        return header.pack(payload=message_data)
