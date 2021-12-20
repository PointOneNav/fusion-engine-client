import pytest


from fusion_engine_client.messages.configuration import ConfigurationSource, DeviceCourseOrientationConfig
from fusion_engine_client.messages import (SetConfigMessage,
                                           Uart1BaudConfig,
                                           ConfigType,
                                           Direction,
                                           ConfigDataMessage,
                                           GnssLeverArmConfig,
                                           InvalidConfig)


import logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger('point_one').setLevel(logging.DEBUG)


def test_set_config():
    BASE_SIZE = 8

    set_msg = SetConfigMessage(DeviceCourseOrientationConfig(Direction.BACKWARD, Direction.DOWN))
    assert len(set_msg.pack()) == BASE_SIZE + 4

    set_msg = SetConfigMessage(GnssLeverArmConfig(1, 2, 3))
    assert len(set_msg.pack()) == BASE_SIZE + 12

    set_msg = SetConfigMessage()
    set_msg.config_object = Uart1BaudConfig(9600)
    uart_data = set_msg.pack()
    assert len(uart_data) == BASE_SIZE + 4

    set_msg = SetConfigMessage()
    set_msg.unpack(uart_data)
    assert isinstance(set_msg.config_object, Uart1BaudConfig)
    assert set_msg.config_object.GetType() == ConfigType.UART1_BAUD
    assert set_msg.config_object.value == 9600


def test_bad_set_config():
    BASE_SIZE = 8
    set_msg = SetConfigMessage()
    with pytest.raises(TypeError):
        set_msg.pack()

    set_msg = SetConfigMessage()
    set_msg.config_object = "Dummy"
    with pytest.raises(TypeError):
        set_msg.pack()

    set_msg = SetConfigMessage()
    set_msg.config_object = InvalidConfig()
    uart_data = set_msg.pack()
    assert len(uart_data) == BASE_SIZE

    set_msg = SetConfigMessage()
    set_msg.unpack(uart_data)
    assert isinstance(set_msg.config_object, InvalidConfig)
    assert set_msg.config_object.GetType() == ConfigType.INVALID


def test_config_data():
    BASE_SIZE = 12
    data_msg = ConfigDataMessage()
    data_msg.config_object = GnssLeverArmConfig(1, 2, 3)
    assert len(data_msg.pack()) == BASE_SIZE + 12

    data_msg = ConfigDataMessage()
    data_msg.config_object = Uart1BaudConfig(9600)
    data_msg.config_source = ConfigurationSource.SAVED
    uart_data = data_msg.pack()
    assert len(uart_data) == BASE_SIZE + 4

    data_msg = ConfigDataMessage()
    data_msg.unpack(uart_data)
    assert isinstance(data_msg.config_object, Uart1BaudConfig)
    assert data_msg.config_object.GetType() == ConfigType.UART1_BAUD
    assert data_msg.config_object.value == 9600
    assert data_msg.config_source == ConfigurationSource.SAVED
