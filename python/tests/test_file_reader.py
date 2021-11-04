import numpy as np

from fusion_engine_client.analysis.file_reader import FileReader, MessageData, TimeAlignmentMode
from fusion_engine_client.messages import PoseMessage, PoseAuxMessage, Timestamp


def setup():
    data = {
        PoseMessage.MESSAGE_TYPE: MessageData(PoseMessage.MESSAGE_TYPE, None),
        PoseAuxMessage.MESSAGE_TYPE: MessageData(PoseAuxMessage.MESSAGE_TYPE, None),
    }

    message = PoseMessage()
    message.p1_time = Timestamp(1.0)
    message.velocity_body_mps = np.array([1.0, 2.0, 3.0])
    data[PoseMessage.MESSAGE_TYPE].messages.append(message)

    message = PoseMessage()
    message.p1_time = Timestamp(2.0)
    message.velocity_body_mps = np.array([4.0, 5.0, 6.0])
    data[PoseMessage.MESSAGE_TYPE].messages.append(message)

    message = PoseAuxMessage()
    message.p1_time = Timestamp(2.0)
    message.velocity_enu_mps = np.array([14.0, 15.0, 16.0])
    data[PoseAuxMessage.MESSAGE_TYPE].messages.append(message)

    message = PoseAuxMessage()
    message.p1_time = Timestamp(3.0)
    message.velocity_enu_mps = np.array([17.0, 18.0, 19.0])
    data[PoseAuxMessage.MESSAGE_TYPE].messages.append(message)

    return data


def test_time_align_drop():
    data = setup()
    FileReader.time_align_data(data, TimeAlignmentMode.DROP)
    assert len(data[PoseMessage.MESSAGE_TYPE].messages) == 1
    assert float(data[PoseMessage.MESSAGE_TYPE].messages[0].p1_time) == 2.0
    assert len(data[PoseAuxMessage.MESSAGE_TYPE].messages) == 1
    assert float(data[PoseAuxMessage.MESSAGE_TYPE].messages[0].p1_time) == 2.0


def test_time_align_insert():
    data = setup()
    FileReader.time_align_data(data, TimeAlignmentMode.INSERT)

    assert len(data[PoseMessage.MESSAGE_TYPE].messages) == 3
    assert float(data[PoseMessage.MESSAGE_TYPE].messages[0].p1_time) == 1.0
    assert float(data[PoseMessage.MESSAGE_TYPE].messages[1].p1_time) == 2.0
    assert float(data[PoseMessage.MESSAGE_TYPE].messages[2].p1_time) == 3.0
    assert data[PoseMessage.MESSAGE_TYPE].messages[0].velocity_body_mps[0] == 1.0
    assert data[PoseMessage.MESSAGE_TYPE].messages[1].velocity_body_mps[0] == 4.0
    assert np.isnan(data[PoseMessage.MESSAGE_TYPE].messages[2].velocity_body_mps[0])

    assert len(data[PoseAuxMessage.MESSAGE_TYPE].messages) == 3
    assert float(data[PoseAuxMessage.MESSAGE_TYPE].messages[0].p1_time) == 1.0
    assert float(data[PoseAuxMessage.MESSAGE_TYPE].messages[1].p1_time) == 2.0
    assert float(data[PoseAuxMessage.MESSAGE_TYPE].messages[2].p1_time) == 3.0
    assert np.isnan(data[PoseAuxMessage.MESSAGE_TYPE].messages[0].velocity_enu_mps[0])
    assert data[PoseAuxMessage.MESSAGE_TYPE].messages[1].velocity_enu_mps[0] == 14.0
    assert data[PoseAuxMessage.MESSAGE_TYPE].messages[2].velocity_enu_mps[0] == 17.0
