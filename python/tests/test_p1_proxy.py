import argparse
import sys
import time

import numpy as np
import pytest

from fusion_engine_client.applications import p1_proxy
from fusion_engine_client.applications.p1_proxy import build_input_message, parse_message_types, parse_vec3
from fusion_engine_client.messages import (
    EventNotificationMessage,
    ExternalPoseInput,
    GearType,
    IMUInput,
    MessageRate,
    MessageType,
    PoseMessage,
    RawIMUOutput,
    RawVehicleSpeedOutput,
    RawWheelSpeedOutput,
    SensorDataSource,
    SolutionType,
    SystemTimeSource,
    Timestamp,
    VehicleSpeedInput,
    WheelSpeedInput,
)
from fusion_engine_client.parsers import FusionEngineDecoder, FusionEngineEncoder
from fusion_engine_client.utils.time_provider import TimeProvider

ALL_TYPES = {MessageType.RAW_WHEEL_SPEED_OUTPUT, MessageType.RAW_VEHICLE_SPEED_OUTPUT, MessageType.RAW_IMU_OUTPUT,
             MessageType.POSE}


class TestParseMessageTypes:
    def test_full_names(self):
        assert parse_message_types('WheelSpeedOutput,IMUOutput') == \
            {MessageType.RAW_WHEEL_SPEED_OUTPUT, MessageType.RAW_IMU_OUTPUT}

    def test_shorthands(self):
        assert parse_message_types('wheel,vehicle,imu,pose') == ALL_TYPES

    def test_case_insensitive_and_whitespace(self):
        assert parse_message_types(' WHEEL , imuoutput ') == \
            {MessageType.RAW_WHEEL_SPEED_OUTPUT, MessageType.RAW_IMU_OUTPUT}

    def test_mixed_full_and_shorthand(self):
        assert parse_message_types('Pose,wheel') == {MessageType.POSE, MessageType.RAW_WHEEL_SPEED_OUTPUT}

    @pytest.mark.parametrize('value', ['all', 'ALL', ''])
    def test_all(self, value):
        assert parse_message_types(value) == ALL_TYPES

    @pytest.mark.parametrize('value', ['bogus', 'wheel,bogus', 'wheel,,imu'])
    def test_invalid(self, value):
        with pytest.raises(argparse.ArgumentTypeError):
            parse_message_types(value)


class TestParseVec3:
    def test_valid(self):
        np.testing.assert_array_equal(parse_vec3('1.0,-2,3.5'), [1.0, -2.0, 3.5])

    @pytest.mark.parametrize('value', ['1,2', '1,2,3,4', '1,a,3', ''])
    def test_invalid(self, value):
        with pytest.raises(argparse.ArgumentTypeError):
            parse_vec3(value)


def _make_wheel_speed(p1_sec=10.0):
    message = RawWheelSpeedOutput()
    message.details.p1_time = Timestamp(p1_sec)
    message.details.data_source = SensorDataSource.CAN
    message.front_left_speed_mps = 1.0
    message.front_right_speed_mps = 2.0
    message.rear_left_speed_mps = 3.0
    message.rear_right_speed_mps = 4.0
    message.gear = GearType.FORWARD
    message.flags = 0x1
    return message


def _make_time_provider(p1_sec, gps_sec):
    pose = PoseMessage()
    pose.p1_time = Timestamp(p1_sec)
    pose.gps_time = Timestamp(gps_sec)
    time_provider = TimeProvider()
    time_provider.handle_message(pose)
    return time_provider


def _options(**overrides):
    options = argparse.Namespace(use_gps_time=False, source_lever_arm=np.zeros(3), target_lever_arm=np.zeros(3),
                                 target_rotation=np.zeros(3), target_translation=np.zeros(3))
    for key, value in overrides.items():
        setattr(options, key, value)
    return options


class TestBuildInputMessage:
    def test_wheel_speed_fields_copied(self):
        result = build_input_message(_make_wheel_speed(), _options(use_gps_time=False), TimeProvider())
        assert isinstance(result, WheelSpeedInput)
        assert result.front_left_speed_mps == 1.0
        assert result.front_right_speed_mps == 2.0
        assert result.rear_left_speed_mps == 3.0
        assert result.rear_right_speed_mps == 4.0
        assert result.gear == GearType.FORWARD
        assert result.flags == 0x1
        assert result.details.data_source == SensorDataSource.CAN

    def test_vehicle_speed_fields_copied(self):
        message = RawVehicleSpeedOutput()
        message.vehicle_speed_mps = 5.0
        message.gear = GearType.REVERSE
        result = build_input_message(message, _options(use_gps_time=False), TimeProvider())
        assert isinstance(result, VehicleSpeedInput)
        assert result.vehicle_speed_mps == 5.0
        assert result.gear == GearType.REVERSE

    def test_imu_fields_copied(self):
        message = RawIMUOutput()
        message.temperature_degc = 25.0
        message.accel_mps2 = np.array([0.1, 0.2, 9.8])
        message.gyro_rps = np.array([0.01, 0.02, 0.03])
        result = build_input_message(message, _options(use_gps_time=False), TimeProvider())
        assert isinstance(result, IMUInput)
        assert result.temperature_degc == 25.0
        np.testing.assert_array_equal(result.accel_mps2, message.accel_mps2)
        np.testing.assert_array_equal(result.gyro_rps, message.gyro_rps)

    def test_unsupported_type_returns_none(self):
        assert build_input_message(EventNotificationMessage(), _options(), TimeProvider()) is None

    def test_pose_transformed_without_reset_by_default(self):
        result = build_input_message(_make_pose(100.0, 1000.0), _options(), TimeProvider())
        assert isinstance(result, ExternalPoseInput)
        assert result.flags == 0
        assert float(result.details.measurement_time) == pytest.approx(1000.0)

    def test_pose_reset_requested(self):
        result = build_input_message(_make_pose(100.0, 1000.0), _options(), TimeProvider(), reset_engine_position=True)
        assert result.flags == ExternalPoseInput.FLAG_RESET_POSITION_DATA

    def test_no_gps_time_leaves_timestamp_to_target(self):
        time_provider = _make_time_provider(p1_sec=10.0, gps_sec=1000.0)
        result = build_input_message(_make_wheel_speed(), _options(use_gps_time=False), time_provider)
        assert result.details.measurement_time_source == SystemTimeSource.INVALID

    def test_gps_time_converted_from_p1(self):
        time_provider = _make_time_provider(p1_sec=10.0, gps_sec=1000.0)
        result = build_input_message(_make_wheel_speed(p1_sec=12.5), _options(use_gps_time=True), time_provider)
        assert result.details.measurement_time_source == SystemTimeSource.GPS_TIME
        assert float(result.details.measurement_time) == pytest.approx(1002.5)

    def test_gps_time_passed_through_from_source(self):
        message = _make_wheel_speed()
        message.details.measurement_time = Timestamp(2000.0)
        message.details.measurement_time_source = SystemTimeSource.GPS_TIME
        result = build_input_message(message, _options(use_gps_time=True), TimeProvider())
        assert result.details.measurement_time_source == SystemTimeSource.GPS_TIME
        assert float(result.details.measurement_time) == pytest.approx(2000.0)

    def test_gps_time_unavailable_falls_back_to_reception(self):
        result = build_input_message(_make_wheel_speed(), _options(use_gps_time=True), TimeProvider())
        assert result.details.measurement_time_source == SystemTimeSource.INVALID


SOURCE = 'tcp://source:30202'
TARGETS = ['tcp://target1:30201', 'tcp://target2:30201', 'tcp://:30303']


class _FakeTransport:
    """!
    @brief Stand-in for a transport that records everything sent to it.
    """
    def __init__(self):
        self.sent = []
        self.closed = False

    def send(self, data):
        self.sent.append(bytes(data))

    def close(self):
        self.closed = True

    def decode_sent(self):
        return [message for _, message in FusionEngineDecoder().on_data(b''.join(self.sent))]


def _make_pose(p1_sec, gps_sec):
    pose = PoseMessage()
    pose.p1_time = Timestamp(p1_sec)
    pose.gps_time = Timestamp(gps_sec)
    pose.solution_type = SolutionType.RTKFixed
    pose.lla_deg = np.array([37.7749, -122.4194, 10.0])
    pose.position_std_enu_m = np.array([0.1, 0.1, 0.2])
    pose.ypr_deg = np.array([90.0, 0.0, 0.0])
    pose.ypr_std_deg = np.array([0.5, 0.1, 0.1])
    return pose


def _make_source_stream():
    imu = RawIMUOutput()
    imu.details.p1_time = Timestamp(10.06)
    encoder = FusionEngineEncoder()
    messages = [
        _make_pose(p1_sec=10.0, gps_sec=1000.0),
        _make_wheel_speed(p1_sec=10.05),
        imu,
        # Not a forwardable type -- should be ignored.
        EventNotificationMessage(),
        _make_pose(p1_sec=10.1, gps_sec=1000.1),
    ]
    return b''.join(encoder.encode_message(m) for m in messages)


def _run_proxy(monkeypatch, extra_args=(), targets=TARGETS):
    source = _FakeTransport()
    target_transports = {}

    def fake_create_transport(descriptor, **kwargs):
        if descriptor == SOURCE:
            return source
        target_transports[descriptor] = _FakeTransport()
        return target_transports[descriptor]

    # Deliver the whole source stream in one read, then stop the proxy as if the user hit Ctrl-C.
    chunks = [_make_source_stream()]

    def fake_recv_from_transport(transport, size):
        if chunks:
            return chunks.pop(0)
        raise KeyboardInterrupt

    monkeypatch.setattr(p1_proxy, 'create_transport', fake_create_transport)
    monkeypatch.setattr(p1_proxy, 'recv_from_transport', fake_recv_from_transport)
    monkeypatch.setattr(sys, 'argv', ['p1_proxy', SOURCE, *targets, *extra_args])
    p1_proxy.main()
    return source, target_transports


def _requested_rates(source):
    return {MessageType(m.message_id): m.rate for m in source.decode_sent()}


class TestMain:
    def test_forwards_to_every_target(self, monkeypatch):
        source, targets = _run_proxy(monkeypatch)

        assert list(targets.keys()) == TARGETS
        first = targets[TARGETS[0]]
        for target in targets.values():
            assert target.sent == first.sent
            assert target.closed
        assert source.closed

        forwarded = first.decode_sent()
        assert [m.get_type() for m in forwarded] == [
            MessageType.EXTERNAL_POSE_INPUT,
            MessageType.WHEEL_SPEED_INPUT,
            MessageType.IMU_INPUT,
            MessageType.EXTERNAL_POSE_INPUT,
        ]

    def test_pose_does_not_reset_target_by_default(self, monkeypatch):
        _, targets = _run_proxy(monkeypatch, extra_args=['-m', 'pose'])
        poses = targets[TARGETS[0]].decode_sent()
        assert [p.flags for p in poses] == [0, 0]

    def test_only_first_pose_resets_target_when_requested(self, monkeypatch):
        _, targets = _run_proxy(monkeypatch, extra_args=['-m', 'pose', '--reset-target-position'])
        for target in targets.values():
            assert [p.flags for p in target.decode_sent()] == [ExternalPoseInput.FLAG_RESET_POSITION_DATA, 0]

    def test_requests_rates_from_source(self, monkeypatch):
        source, _ = _run_proxy(monkeypatch)
        assert _requested_rates(source) == {
            MessageType.RAW_WHEEL_SPEED_OUTPUT: MessageRate.ON_CHANGE,
            MessageType.RAW_VEHICLE_SPEED_OUTPUT: MessageRate.ON_CHANGE,
            MessageType.RAW_IMU_OUTPUT: MessageRate.ON_CHANGE,
            MessageType.POSE: MessageRate.INTERVAL_100_MS,
        }

    def test_pose_rate_100hz(self, monkeypatch):
        source, _ = _run_proxy(monkeypatch, extra_args=['--pose-rate=100hz'])
        assert _requested_rates(source)[MessageType.POSE] == MessageRate.INTERVAL_10_MS

    def test_message_type_filter(self, monkeypatch):
        source, targets = _run_proxy(monkeypatch, extra_args=['-m', 'wheel', '-m', 'Pose'])

        assert set(_requested_rates(source).keys()) == {MessageType.RAW_WHEEL_SPEED_OUTPUT, MessageType.POSE}
        for target in targets.values():
            assert [m.get_type() for m in target.decode_sent()] == [
                MessageType.EXTERNAL_POSE_INPUT,
                MessageType.WHEEL_SPEED_INPUT,
                MessageType.EXTERNAL_POSE_INPUT,
            ]

    def test_target_connection_failure_does_not_stop_proxy(self, monkeypatch):
        source = _FakeTransport()
        good = _FakeTransport()

        def fake_create_transport(descriptor, **kwargs):
            if descriptor == SOURCE:
                return source
            elif descriptor == TARGETS[0]:
                raise ConnectionRefusedError('refused')
            else:
                return good

        chunks = [_make_source_stream()]

        def fake_recv_from_transport(transport, size):
            if chunks:
                return chunks.pop(0)
            raise KeyboardInterrupt

        monkeypatch.setattr(p1_proxy, 'create_transport', fake_create_transport)
        monkeypatch.setattr(p1_proxy, 'recv_from_transport', fake_recv_from_transport)
        monkeypatch.setattr(sys, 'argv', ['p1_proxy', SOURCE, TARGETS[0], TARGETS[1]])
        p1_proxy.main()
        assert len(good.decode_sent()) == 4


class _FailingTransport(_FakeTransport):
    def __init__(self):
        super().__init__()
        self.fail = False

    def send(self, data):
        if self.fail:
            raise BrokenPipeError('gone')
        super().send(data)


class TestTarget:
    @pytest.fixture(autouse=True)
    def fast_retry(self, monkeypatch):
        monkeypatch.setattr(p1_proxy.Target, '_RETRY_INTERVAL_SEC', 0.01)

    @staticmethod
    def _wait_until(condition, timeout_sec=2.0):
        end = time.time() + timeout_sec
        while not condition() and time.time() < end:
            time.sleep(0.005)
        assert condition()

    def test_failed_send_drops_target_and_reconnects(self, monkeypatch):
        transports = []

        def fake_create_transport(descriptor, **kwargs):
            transports.append(_FailingTransport())
            return transports[-1]

        monkeypatch.setattr(p1_proxy, 'create_transport', fake_create_transport)
        target = p1_proxy.Target('tcp://x:1', 1.0)
        target.start()
        try:
            assert target.send(b'a')
            assert target.send(b'b')
            assert transports[0].sent == [b'a', b'b']

            transports[0].fail = True
            assert not target.send(b'c')
            assert not target.connected
            assert transports[0].closed

            self._wait_until(lambda: target.connected)
            assert len(transports) == 2
            assert target.send(b'd')
            assert transports[1].sent == [b'd']
        finally:
            target.close()

    def test_initial_failure_is_retried(self, monkeypatch):
        attempts = []

        def fake_create_transport(descriptor, **kwargs):
            attempts.append(1)
            if len(attempts) < 3:
                raise ConnectionRefusedError('refused')
            return _FakeTransport()

        monkeypatch.setattr(p1_proxy, 'create_transport', fake_create_transport)
        target = p1_proxy.Target('tcp://x:1', 1.0)
        target.start()
        try:
            assert not target.send(b'a')
            self._wait_until(lambda: target.connected)
        finally:
            target.close()
