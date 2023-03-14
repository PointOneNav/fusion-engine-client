from datetime import datetime, timezone

from gpstime import gpstime
import numpy as np
import pytest

from fusion_engine_client.analysis.data_loader import DataLoader, MessageData, TimeAlignmentMode
from fusion_engine_client.messages import *
from fusion_engine_client.parsers import FusionEngineEncoder, MixedLogReader
from fusion_engine_client.utils.time_range import TimeRange


def encode_generated_data(messages, data_path=None, return_dict=True):
    if data_path is not None:
        encoder = FusionEngineEncoder()
        with open(data_path, 'wb') as f:
            for message in messages:
                if isinstance(message, bytes):
                    f.write(message)
                else:
                    f.write(encoder.encode_message(message))

    if return_dict:
        return message_list_to_dict(messages)
    else:
        return [m for m in messages if not isinstance(m, bytes)]


def generate_data(data_path=None, include_binary=False, return_dict=True):
    messages = []

    if include_binary:
        messages.append(b'12345')

    message = EventNotificationMessage()
    message.system_time_ns = 1000000000
    messages.append(message)

    message = PoseMessage()
    message.p1_time = Timestamp(1.0)
    message.velocity_body_mps = np.array([1.0, 2.0, 3.0])
    messages.append(message)

    if include_binary:
        messages.append(b'12345')

    message = PoseMessage()
    message.p1_time = Timestamp(2.0)
    message.velocity_body_mps = np.array([4.0, 5.0, 6.0])
    messages.append(message)

    message = PoseAuxMessage()
    message.p1_time = Timestamp(2.0)
    message.velocity_enu_mps = np.array([14.0, 15.0, 16.0])
    messages.append(message)

    message = GNSSInfoMessage()
    message.p1_time = Timestamp(2.0)
    message.gdop = 5.0
    messages.append(message)

    if include_binary:
        messages.append(b'12345')

    message = EventNotificationMessage()
    message.system_time_ns = 3000000000
    messages.append(message)

    message = PoseAuxMessage()
    message.p1_time = Timestamp(3.0)
    message.velocity_enu_mps = np.array([17.0, 18.0, 19.0])
    messages.append(message)

    if include_binary:
        messages.append(b'12345')

    message = GNSSInfoMessage()
    message.p1_time = Timestamp(3.0)
    message.gdop = 6.0
    messages.append(message)

    message = EventNotificationMessage()
    message.system_time_ns = 4000000000
    messages.append(message)

    if include_binary:
        messages.append(b'12345')

    return encode_generated_data(messages, data_path=data_path, return_dict=return_dict)


def message_list_to_dict(messages):
    result = {}
    for message in messages:
        if isinstance(message, bytes):
            continue

        if message.get_type() not in result:
            result[message.get_type()] = MessageData(message.get_type(), None)
        result[message.get_type()].messages.append(message)
    return result


def message_list_to_messagedata(messages):
    result = MessageData(None, None)
    result.messages = messages
    return result


def filter_by_time(messages, time_range: TimeRange):
    result = [m for m in messages if time_range.is_in_range(m)]
    time_range.restart()
    return result


class TestReader:
    @pytest.fixture
    def data_path(self, tmpdir):
        data_path = tmpdir.join('test_file.p1log')
        yield data_path

    def _check_message(self, message, expected_message):
        assert message.get_type() == expected_message.get_type()

        expected_p1_time = expected_message.get_p1_time()
        if expected_p1_time is not None:
            assert float(message.get_p1_time()) == pytest.approx(expected_p1_time, 1e-6)

        expected_system_time_sec = expected_message.get_system_time_sec()
        if expected_system_time_sec is not None:
            assert float(message.get_system_time_sec()) == pytest.approx(expected_system_time_sec, 1e-6)

    def _check_dict_results(self, results: dict, expected_results: dict):
        expected_types = list(expected_results.keys())
        for message_type, message_data in results.items():
            if message_type in expected_types:
                expected_data = expected_results[message_type]
                self._check_messagedata_results(message_data, expected_data)
            else:
                assert len(message_data.messages) == 0

    def _check_messagedata_results(self, results: MessageData, expected_results: MessageData):
        assert len(results.messages) == len(expected_results.messages)
        for message, expected_message in zip(results.messages, expected_results.messages):
            self._check_message(message, expected_message)

    def _check_results(self, results, expected_results):
        if isinstance(results, MessageData):
            self._check_messagedata_results(results, expected_results)
        else:
            self._check_dict_results(results, expected_results)

    def test_read_all(self, data_path):
        expected_messages = generate_data(data_path=str(data_path), include_binary=False, return_dict=False)
        expected_result = message_list_to_dict(expected_messages)

        # Construct a reader. This will attempt to set t0 immediately by scanning the data file. If an index file
        # exists, the reader will use the index file to find t0 quickly. If not, it'll read the file directly, but will
        # _not_ attempt to generate an index (which requires reading the entire data file).
        reader = DataLoader(path=str(data_path))
        assert reader.t0 is not None
        assert reader.system_t0 is not None
        assert not reader.reader.have_index()

        # Now read the data itself. This _will_ generate an index file.
        result = reader.read()
        self._check_results(result, expected_result)
        assert reader.reader.have_index()
        assert len(reader.reader._original_index) == len(expected_messages)
        assert len(reader.reader.index) == len(expected_messages)

    def test_read_all_with_index(self, data_path):
        expected_messages = generate_data(data_path=str(data_path), include_binary=False, return_dict=False)
        expected_result = message_list_to_dict(expected_messages)

        MixedLogReader.generate_index_file(str(data_path))

        # Construct a reader. We have an index file, so this should use that.
        reader = DataLoader(path=str(data_path))
        assert reader.t0 is not None
        assert reader.system_t0 is not None
        assert reader.reader.have_index()

        # Now read the data itself. This will use the index file.
        result = reader.read()
        self._check_results(result, expected_result)

    def test_read_pose(self, data_path):
        messages = generate_data(data_path=str(data_path), include_binary=False, return_dict=False)
        expected_messages = [m for m in messages if isinstance(m, PoseMessage)]
        expected_result = message_list_to_dict(expected_messages)

        # Read just pose messages. This should generate an index for the entire file.
        reader = DataLoader(path=str(data_path))
        result = reader.read(message_types=PoseMessage)
        self._check_results(result, expected_result)
        assert reader.reader.have_index()
        assert len(reader.reader._original_index) == len(messages)
        assert len(reader.reader.index) == len(expected_messages)

    def test_read_pose_with_index(self, data_path):
        messages = generate_data(data_path=str(data_path), include_binary=False, return_dict=False)
        expected_messages = [m for m in messages if isinstance(m, PoseMessage)]
        expected_result = message_list_to_dict(expected_messages)

        MixedLogReader.generate_index_file(str(data_path))

        # Just read pose messages. The index file already exists, so we should use that to do the read.
        reader = DataLoader(path=str(data_path))
        assert reader.reader.have_index()
        result = reader.read(message_types=PoseMessage)
        self._check_results(result, expected_result)

    def test_read_pose_mixed_binary(self, data_path):
        messages = generate_data(data_path=str(data_path), include_binary=True, return_dict=False)
        expected_messages = [m for m in messages if isinstance(m, PoseMessage)]
        expected_result = message_list_to_dict(expected_messages)

        # Read just pose messages. This should generate an index for the entire file.
        reader = DataLoader(path=str(data_path))
        result = reader.read(message_types=PoseMessage)
        self._check_results(result, expected_result)
        assert reader.reader.have_index()
        assert len(reader.reader._original_index) == len(messages)
        assert len(reader.reader.index) == len(expected_messages)

    def test_read_no_generate_index(self, data_path):
        expected_result = generate_data(data_path=str(data_path), include_binary=False)

        # Construct a reader with index generation disabled. This never generates an index, but the read() call below
        # would if we did not set this.
        reader = DataLoader(path=str(data_path), generate_index=False)
        assert reader.t0 is not None
        assert reader.system_t0 is not None
        assert not reader.reader.have_index()

        # Now read the data itself. This will _not_ generate an index file.
        result = reader.read()
        self._check_results(result, expected_result)
        assert not reader.reader.have_index()

        # Do the same but this time using the disable argument to read().
        reader = DataLoader(path=str(data_path))
        result = reader.read(disable_index_generation=True)
        self._check_results(result, expected_result)
        assert not reader.reader.have_index()

    def test_read_in_order(self, data_path):
        messages = generate_data(data_path=str(data_path), include_binary=False, return_dict=False)
        expected_messages = [m for m in messages if m.get_type() in (MessageType.POSE, MessageType.EVENT_NOTIFICATION)]
        expected_result = message_list_to_messagedata(expected_messages)

        reader = DataLoader(path=str(data_path))
        assert not reader.reader.have_index()

        result = reader.read(message_types=[PoseMessage, EventNotificationMessage], return_in_order=True)
        self._check_results(result, expected_result)
        assert reader.reader.have_index()

    def test_read_in_order_with_index(self, data_path):
        messages = generate_data(data_path=str(data_path), include_binary=False, return_dict=False)
        expected_messages = [m for m in messages if m.get_type() in (MessageType.POSE, MessageType.EVENT_NOTIFICATION)]
        expected_result = message_list_to_messagedata(expected_messages)

        MixedLogReader.generate_index_file(str(data_path))

        reader = DataLoader(path=str(data_path))
        assert reader.reader.have_index()

        result = reader.read(message_types=[PoseMessage, EventNotificationMessage], return_in_order=True)
        self._check_results(result, expected_result)

    # Note: TimeRange objects keep internal state, so we can't use them here since the state will remain across multiple
    # calls for different use_index values. Instead we store range strings and parse them on each call.
    @pytest.mark.parametrize("time_range", [
        '1.0::rel',
        ':2.0:rel',
        '1.0:2.0:rel',
        '1.0::abs',
        ':2.0:abs',
        '1.0:2.0:abs',
    ])
    @pytest.mark.parametrize("use_index", [False, True])
    def test_time_range(self, data_path, time_range, use_index):
        time_range = TimeRange.parse(time_range)
        messages = generate_data(data_path=str(data_path), include_binary=False, return_dict=False)
        expected_messages = filter_by_time(messages, time_range)
        expected_result = message_list_to_dict(expected_messages)
        if use_index:
            MixedLogReader.generate_index_file(str(data_path))
        reader = DataLoader(path=str(data_path))
        result = reader.read(time_range=time_range)
        self._check_results(result, expected_result)

    @pytest.mark.parametrize("max_messages", [1, 3, -1, -1])
    @pytest.mark.parametrize("use_index", [False, True])
    def test_max_messages(self, data_path, max_messages, use_index):
        messages = generate_data(data_path=str(data_path), include_binary=False, return_dict=False)

        if use_index:
            MixedLogReader.generate_index_file(str(data_path))

        # First, try reading for all message types.
        if max_messages >= 0:
            expected_messages = messages[:max_messages]
        else:
            expected_messages = messages[max_messages:]
        expected_result = message_list_to_dict(expected_messages)
        reader = DataLoader(path=str(data_path))
        result = reader.read(max_messages=max_messages)
        self._check_results(result, expected_result)

        # Now, try reading just specific message types.
        message_types = (PoseMessage, PoseAuxMessage)
        messages = [m for m in messages if isinstance(m, message_types)]
        if max_messages >= 0:
            expected_messages = messages[:max_messages]
        else:
            expected_messages = messages[max_messages:]
        expected_result = message_list_to_dict(expected_messages)
        reader = DataLoader(path=str(data_path))
        result = reader.read(max_messages=max_messages, message_types=message_types)
        self._check_results(result, expected_result)


class TestTimeAlignment:
    @pytest.fixture
    def data(self):
        return generate_data()

    def test_drop(self, data):
        DataLoader.time_align_data(data, TimeAlignmentMode.DROP)
        assert len(data[PoseMessage.MESSAGE_TYPE].messages) == 1
        assert float(data[PoseMessage.MESSAGE_TYPE].messages[0].p1_time) == 2.0
        assert len(data[PoseAuxMessage.MESSAGE_TYPE].messages) == 1
        assert float(data[PoseAuxMessage.MESSAGE_TYPE].messages[0].p1_time) == 2.0
        assert len(data[GNSSInfoMessage.MESSAGE_TYPE].messages) == 1
        assert float(data[GNSSInfoMessage.MESSAGE_TYPE].messages[0].p1_time) == 2.0

    def test_insert(self, data):
        DataLoader.time_align_data(data, TimeAlignmentMode.INSERT)

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

        assert len(data[GNSSInfoMessage.MESSAGE_TYPE].messages) == 3
        assert float(data[GNSSInfoMessage.MESSAGE_TYPE].messages[0].p1_time) == 1.0
        assert float(data[GNSSInfoMessage.MESSAGE_TYPE].messages[1].p1_time) == 2.0
        assert float(data[GNSSInfoMessage.MESSAGE_TYPE].messages[2].p1_time) == 3.0
        assert np.isnan(data[GNSSInfoMessage.MESSAGE_TYPE].messages[0].gdop)
        assert data[GNSSInfoMessage.MESSAGE_TYPE].messages[1].gdop == 5.0
        assert data[GNSSInfoMessage.MESSAGE_TYPE].messages[2].gdop == 6.0

    def test_specific(self, data):
        DataLoader.time_align_data(data, TimeAlignmentMode.DROP,
                                   message_types=[PoseMessage.MESSAGE_TYPE, GNSSInfoMessage.MESSAGE_TYPE])
        assert len(data[PoseMessage.MESSAGE_TYPE].messages) == 1
        assert float(data[PoseMessage.MESSAGE_TYPE].messages[0].p1_time) == 2.0
        assert len(data[PoseAuxMessage.MESSAGE_TYPE].messages) == 2
        assert float(data[PoseAuxMessage.MESSAGE_TYPE].messages[0].p1_time) == 2.0
        assert float(data[PoseAuxMessage.MESSAGE_TYPE].messages[1].p1_time) == 3.0
        assert len(data[GNSSInfoMessage.MESSAGE_TYPE].messages) == 1
        assert float(data[GNSSInfoMessage.MESSAGE_TYPE].messages[0].p1_time) == 2.0


class TestTimeConversion:
    @pytest.fixture
    def data_path(self, tmpdir):
        data_path = tmpdir.join('test_file.p1log')
        yield data_path

    @classmethod
    def _generate_data(cls, data_path):
        messages = []
        for i in range(1, 20):
            message = PoseMessage()
            message.p1_time = Timestamp(50.0 + i)
            message.gps_time = message.p1_time + Y2K_GPS_SEC
            messages.append(message)
        return encode_generated_data(messages, data_path=data_path)

    def test_p1_to_p1(self, data_path):
        self._generate_data(data_path=str(data_path))
        loader = DataLoader(path=str(data_path))
        assert loader.convert_to_p1_time(49.1) == pytest.approx(49.1) # Out of range, but P1 so untouched
        assert loader.convert_to_p1_time(53.0) == pytest.approx(53.0) # Exact message value
        assert loader.convert_to_p1_time(53.7) == pytest.approx(53.7) # Between messages, return as is
        assert loader.convert_to_p1_time(80.7) == pytest.approx(80.7) # Out of range, but P1 so untouched

    def test_gps_to_p1(self, data_path):
        self._generate_data(data_path=str(data_path))
        loader = DataLoader(path=str(data_path))
        assert loader.convert_to_p1_time(Y2K_GPS_SEC + 49.1) == pytest.approx(49.1) # Out of range, extrapolate
        assert loader.convert_to_p1_time(Y2K_GPS_SEC + 53.0) == pytest.approx(53.0) # Exact message value
        assert loader.convert_to_p1_time(Y2K_GPS_SEC + 53.7) == pytest.approx(53.7) # Between messages, interpolate
        assert loader.convert_to_p1_time(Y2K_GPS_SEC + 80.7) == pytest.approx(80.7) # Out of range, extrapolate

    def test_gpstime_to_p1(self, data_path):
        self._generate_data(data_path=str(data_path))
        loader = DataLoader(path=str(data_path))
        gps_time = gpstime.fromgps(Y2K_GPS_SEC + 53.7)
        assert loader.convert_to_p1_time(gps_time) == pytest.approx(53.7)
        assert loader.convert_to_p1_time(gps_time.gps()) == pytest.approx(53.7)

    def test_utc_to_p1(self, data_path):
        self._generate_data(data_path=str(data_path))
        loader = DataLoader(path=str(data_path))

        utc_time = datetime.fromtimestamp(Y2K_POSIX_SEC + 53.7, tz=timezone.utc)
        assert loader.convert_to_p1_time(utc_time) == pytest.approx(53.7)
        assert loader.convert_to_p1_time(utc_time.timestamp(), assume_utc=True) == pytest.approx(53.7)

        utc_time_no_tz = utc_time.replace(tzinfo=None)
        assert loader.convert_to_p1_time(utc_time_no_tz, assume_utc=True) == pytest.approx(53.7)

        current_tz = datetime.utcnow().astimezone().tzinfo
        if current_tz != timezone.utc:
            utc_time_no_tz = utc_time.replace(tzinfo=None)
            assert loader.convert_to_p1_time(utc_time_no_tz, assume_utc=False) != pytest.approx(53.7)

        local_time = datetime.fromtimestamp(Y2K_POSIX_SEC + 53.7, tz=None)
        assert loader.convert_to_p1_time(local_time) == pytest.approx(53.7)

    def test_timestamp_to_p1(self, data_path):
        self._generate_data(data_path=str(data_path))
        loader = DataLoader(path=str(data_path))
        assert loader.convert_to_p1_time(Timestamp(53.7)) == pytest.approx(53.7) # P1 time
        assert loader.convert_to_p1_time(Timestamp(Y2K_GPS_SEC + 53.7)) == pytest.approx(53.7) # GPS

    def test_list_to_p1(self, data_path):
        self._generate_data(data_path=str(data_path))
        loader = DataLoader(path=str(data_path))
        times = [
            53.7,
            Y2K_GPS_SEC + 53.7,
            gpstime.fromgps(Y2K_GPS_SEC + 53.7),
            datetime.fromtimestamp(Y2K_POSIX_SEC + 53.7, tz=timezone.utc),
            Timestamp(53.7),
            Timestamp(Y2K_GPS_SEC + 53.7)
        ]
        assert np.allclose(loader.convert_to_p1_time(times), [53.7] * len(times))

    def test_ndarray_to_p1(self, data_path):
        self._generate_data(data_path=str(data_path))
        loader = DataLoader(path=str(data_path))
        times = np.array((53.7, Y2K_GPS_SEC + 53.7))
        assert np.allclose(loader.convert_to_p1_time(times), [53.7] * len(times))
        times = np.array((53.7, Y2K_POSIX_SEC + 53.7))
        assert np.allclose(loader.convert_to_p1_time(times, assume_utc=True), [53.7] * len(times))
