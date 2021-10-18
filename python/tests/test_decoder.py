from fusion_engine_client.messages import PoseMessage, PoseAuxMessage
from fusion_engine_client.messages.defs import MessageHeader, MessageType
from fusion_engine_client.parsers import FusionEngineDecoder

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger('point_one').setLevel(logging.DEBUG)


P1_POSE_MESSAGE1 = b".1\x00\x00\xb3\x9a\xf0\x7f\x02\x00\x10'\x00\x00\x00\x00\x8c\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x80\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\x00\x00\x00\x00\xf0?\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x08@\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f"
P1_POSE_MESSAGE2 = b".1\x00\x00\x02O\xd6\xef\x02\x00\x10'\x01\x00\x00\x00\x8c\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x80\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\x00\x00\x00\x00\xf0?\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x08@\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f"
P1_POSE_AUX_MESSAGE3 = b".1\x00\x00z\x90\x98t\x02\x00\x13'\x02\x00\x00\x00\xa0\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\x00\x00\x00\x00\xf8\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f\x00\x00\xc0\x7f"


def test_good_message_at_once():
  decoder = FusionEngineDecoder()
  ret = decoder.on_data(P1_POSE_MESSAGE1)
  assert len(ret) == 1
  assert ret[0][0].message_type == PoseMessage.MESSAGE_TYPE

def test_good_message_byte_by_byte():
  decoder = FusionEngineDecoder()
  for byte in P1_POSE_MESSAGE1[:-1]:
    ret = decoder.on_data(byte)
    assert len(ret) == 0
  ret = decoder.on_data(P1_POSE_MESSAGE1[-1])
  assert len(ret) == 1
  assert ret[0][0].message_type == PoseMessage.MESSAGE_TYPE

def test_multiple_good():
  test_bytes = P1_POSE_MESSAGE1 + P1_POSE_MESSAGE2
  decoder = FusionEngineDecoder()
  ret = decoder.on_data(test_bytes)
  assert len(ret) == 2
  assert ret[0][0].message_type == PoseMessage.MESSAGE_TYPE
  assert ret[0][0].sequence_number == 0
  assert ret[1][0].message_type == PoseMessage.MESSAGE_TYPE
  assert ret[1][0].sequence_number == 1

def test_sync():
  # Bad preamble
  test_bytes = bytearray() + P1_POSE_MESSAGE1 + P1_POSE_MESSAGE2
  test_bytes[0] = 1
  decoder = FusionEngineDecoder()
  ret = decoder.on_data(test_bytes)
  assert len(ret) == 1
  assert ret[0][0].sequence_number == 1

  # CRC failure
  test_bytes = bytearray() + P1_POSE_MESSAGE1 + P1_POSE_MESSAGE2
  test_bytes[25] = 1
  decoder = FusionEngineDecoder()
  ret = decoder.on_data(test_bytes)
  assert len(ret) == 1
  assert ret[0][0].sequence_number == 1

def test_unknown_message():
  header = MessageHeader()
  payload = b"1234"
  header.message_type = MessageType.RESERVED
  test_bytes = header.pack(payload=payload)
  decoder = FusionEngineDecoder()
  ret = decoder.on_data(test_bytes)
  assert len(ret) == 1
  assert ret[0][1] == payload

def test_callbacks():
  counters = [0, 0, 0, 0]

  def func_helper(header, payload, idx):
    counters[idx] += 1
  func1 = lambda header, payload: func_helper(header, payload, 0)
  func2 = lambda header, payload: func_helper(header, payload, 1)
  func3 = lambda header, payload: func_helper(header, payload, 2)
  func4 = lambda header, payload: func_helper(header, payload, 3)

  test_bytes = P1_POSE_MESSAGE1 + P1_POSE_MESSAGE2 + P1_POSE_AUX_MESSAGE3
  decoder = FusionEngineDecoder()
  decoder.add_callback(PoseMessage.MESSAGE_TYPE, func1)
  decoder.add_callback(PoseAuxMessage.MESSAGE_TYPE, func2)
  decoder.add_callback(None, func3)
  decoder.add_callback(PoseMessage.MESSAGE_TYPE, func4)
  decoder.add_callback(None, func4)

  decoder.on_data(test_bytes)

  assert counters[0] == 2
  assert counters[1] == 1
  assert counters[2] == 3
  assert counters[3] == 5
