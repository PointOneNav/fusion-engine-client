from fusion_engine_client.parsers import FusionEngineDecoder

from fusion_engine_client.messages.internal import ResetCommandMessage

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger('point_one').setLevel(logging.DEBUG)

# reset message
P1_RESET_MESSAGE = b'.1\x00\x00\xb4l\xd0T\x02\x00`N\x00\x00\x00\x00\x04\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\x00'

def test_good_message_at_once():
  decoder = FusionEngineDecoder()
  ret = decoder.on_data(P1_RESET_MESSAGE)
  assert len(ret) == 1
  assert ret[0][0].message_type == ResetCommandMessage.MESSAGE_TYPE

def test_good_message_byte_by_byte():
  decoder = FusionEngineDecoder()
  for byte in P1_RESET_MESSAGE[:-1]:
    ret = decoder.on_data(byte)
    assert len(ret) == 0
  ret = decoder.on_data(P1_RESET_MESSAGE[-1])
  assert len(ret) == 1
  assert ret[0][0].message_type == ResetCommandMessage.MESSAGE_TYPE

def test_multiple_good():
  test_bytes = P1_RESET_MESSAGE + P1_RESET_MESSAGE
  decoder = FusionEngineDecoder()
  ret = decoder.on_data(test_bytes)
  assert len(ret) == 2
  assert ret[1][0].message_type == ResetCommandMessage.MESSAGE_TYPE

def test_sync():
  # Bad preamble
  test_bytes = bytearray() + P1_RESET_MESSAGE + P1_RESET_MESSAGE
  test_bytes[0] = 1
  decoder = FusionEngineDecoder()
  ret = decoder.on_data(P1_RESET_MESSAGE)
  assert len(ret) == 1
  assert ret[0][0].message_type == ResetCommandMessage.MESSAGE_TYPE

  # CRC failure
  test_bytes = bytearray() + P1_RESET_MESSAGE + P1_RESET_MESSAGE
  test_bytes[25] = 1
  decoder = FusionEngineDecoder()
  ret = decoder.on_data(P1_RESET_MESSAGE)
  assert len(ret) == 1
  assert ret[0][0].message_type == ResetCommandMessage.MESSAGE_TYPE
