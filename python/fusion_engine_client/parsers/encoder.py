from ..messages import MessageHeader, MessagePayload

class FusionEngineEncoder:

    def __init__(self):
        self.sequence_number = 0

    def encode_message(self, message: MessagePayload) -> (bytes):

        header = MessageHeader(message.get_type())
        header.sequence_number = self.sequence_number
        self.sequence_number += 1

        message_data = message.pack()

        return header.pack(payload=message_data)
