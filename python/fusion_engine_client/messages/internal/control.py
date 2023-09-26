from .internal_defs import *
from ..control import EventNotificationMessage


class DiagEventNotificationMessage(EventNotificationMessage):
    """!
    @brief Internal diagnostic event notification.
    """
    MESSAGE_TYPE = MessageType.DIAG_EVENT_NOTIFICATION
    MESSAGE_VERSION = EventNotificationMessage.MESSAGE_VERSION

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
