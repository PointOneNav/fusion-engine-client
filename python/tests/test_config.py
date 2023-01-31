from fusion_engine_client.utils import trace as logging

import pytest
from fusion_engine_client.messages import (ConfigResponseMessage, ConfigType,
                                           Direction, GnssLeverArmConfig,
                                           InvalidConfig, MessageRateResponse,
                                           SetConfigMessage, Uart1BaudConfig,
                                           VehicleModel)
from fusion_engine_client.messages.configuration import (
    AppliedSpeedType, ConfigurationSource, DeviceCourseOrientationConfig,
    HardwareTickConfig, MessageRate, RateResponseEntry, SteeringType,
    TickDirection, TickMode, VehicleDetailsConfig, WheelConfig,
    WheelSensorType, _RateResponseEntryConstructRaw)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger('point_one').setLevel(logging.DEBUG)


def test_set_config():
    BASE_SIZE = 8

    set_msg = SetConfigMessage(DeviceCourseOrientationConfig(Direction.BACKWARD, Direction.DOWN))
    assert len(set_msg.pack()) == BASE_SIZE + 4

    set_msg = SetConfigMessage(VehicleDetailsConfig(VehicleModel.LEXUS_CT200H, 1, 2, 3))
    assert len(set_msg.pack()) == BASE_SIZE + 24

    set_msg = SetConfigMessage(WheelConfig(WheelSensorType.NONE, AppliedSpeedType.NONE,
                                           SteeringType.UNKNOWN, 1., 2., 3., 4., 1000, False, True))
    assert len(set_msg.pack()) == BASE_SIZE + 28

    set_msg = SetConfigMessage(HardwareTickConfig(TickMode.OFF, TickDirection.OFF, 0.1))
    assert len(set_msg.pack()) == BASE_SIZE + 8

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
    data_msg = ConfigResponseMessage()
    data_msg.config_object = GnssLeverArmConfig(1, 2, 3)
    assert len(data_msg.pack()) == BASE_SIZE + 12

    data_msg = ConfigResponseMessage()
    data_msg.config_object = Uart1BaudConfig(9600)
    data_msg.config_source = ConfigurationSource.SAVED
    uart_data = data_msg.pack()
    assert len(uart_data) == BASE_SIZE + 4

    data_msg = ConfigResponseMessage()
    data_msg.unpack(uart_data)
    assert isinstance(data_msg.config_object, Uart1BaudConfig)
    assert data_msg.config_object.GetType() == ConfigType.UART1_BAUD
    assert data_msg.config_object.value == 9600
    assert data_msg.config_source == ConfigurationSource.SAVED


def test_msg_rate_data():
    data_msg = MessageRateResponse()
    data_msg.rates = [
        RateResponseEntry()
    ]
    packed_data = data_msg.pack()
    assert len(packed_data) == 8 + _RateResponseEntryConstructRaw.sizeof()

    data_msg = MessageRateResponse()
    data_msg.rates = [
        RateResponseEntry(),
        RateResponseEntry(configured_rate=MessageRate.INTERVAL_1_S)
    ]
    packed_data = data_msg.pack()
    assert len(packed_data) == 8 + _RateResponseEntryConstructRaw.sizeof() * 2

    data_msg = MessageRateResponse()
    data_msg.unpack(packed_data)
    assert data_msg.rates[1].configured_rate == MessageRate.INTERVAL_1_S
