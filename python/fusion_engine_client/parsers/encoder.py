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

    def encode_message(self, message: MessagePayload) -> (bytes):
        """!
        @brief Generate a header with valid CRC and sequence number and generate
               a bytes with the serialized header and payload.

        @post
        The sequence_number is incremented each time this is called.

        @param message The MessagePayload to serialize.

        @return A `bytes` object containing the serialized message.
        """
        header = MessageHeader(message.get_type())
        header.sequence_number = self.sequence_number
        self.sequence_number += 1

        message_data = message.pack()

        return header.pack(payload=message_data)
