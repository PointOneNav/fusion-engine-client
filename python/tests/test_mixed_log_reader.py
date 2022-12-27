import math
import os

import pytest

from fusion_engine_client.analysis.file_index import FileIndex
from fusion_engine_client.messages import *
from fusion_engine_client.parsers import FusionEngineEncoder, MixedLogReader
from fusion_engine_client.utils.time_range import TimeRange


class TestClass:
    _messages = []

    @pytest.fixture
    def data_path(self, tmpdir):
        data_path = tmpdir.join('test_file.p1log')
        yield data_path

    def _generate_data(self, data_path, message_types):
        self._messages = []
        prev_p1_time_sec = None
        prev_system_time_sec = None
        for message_cls, time_sec in message_types:
            if isinstance(message_cls, bytes):
                self._messages.append(message_cls)
                continue

            message = message_cls()
            if hasattr(message, 'p1_time'):
                if time_sec is None:
                    if prev_p1_time_sec is None:
                        message.p1_time = Timestamp()
                    else:
                        message.p1_time = Timestamp(prev_p1_time_sec)
                else:
                    message.p1_time = Timestamp(time_sec)
                    if prev_p1_time_sec is not None:
                        dt_sec = time_sec - prev_p1_time_sec
                        prev_system_time_sec += dt_sec
                    prev_p1_time_sec = time_sec
            elif hasattr(message, 'system_time_ns'):
                if time_sec is None:
                    if prev_system_time_sec is None:
                        message.system_time_ns = 0
                    else:
                        message.system_time_ns = int(prev_system_time_sec * 1e9)
                else:
                    message.system_time_ns = int(time_sec * 1e9)
                    if prev_system_time_sec is not None:
                        dt_sec = time_sec - prev_system_time_sec
                        prev_p1_time_sec += dt_sec
                    prev_system_time_sec = time_sec
            self._messages.append(message)

        encoder = FusionEngineEncoder()
        with open(data_path, 'wb') as f:
            for message in self._messages:
                if isinstance(message, bytes):
                    f.write(message)
                else:
                    f.write(encoder.encode_message(message))

        return [m for m in self._messages if not isinstance(m, bytes)]

    def _generate_mixed_data(self, data_path):
        messages = self._generate_data(data_path, message_types=[
            (EventNotificationMessage, 0.0),
            (PoseMessage, 1.0),
            (PoseMessage, 2.0),
            (EventNotificationMessage, 2.0),
            (PoseMessage, 3.0),
            (PoseMessage, 4.0),
            (EventNotificationMessage, 4.0),
        ])
        return messages

    def _generate_mixed_data_with_binary(self, data_path):
        messages = self._generate_data(data_path, message_types=[
            (b'1234', None),
            (EventNotificationMessage, 0.0),
            (PoseMessage, 1.0),
            (b'1234', None),
            (PoseMessage, 2.0),
            (b'1234', None),
            (EventNotificationMessage, 2.0),
            (PoseMessage, 3.0),
            (b'1234', None),
            (PoseMessage, 4.0),
            (EventNotificationMessage, 4.0),
            (b'1234', None),
        ])
        return messages

    def _check_message(self, message, expected_message):
        assert message.get_type() == expected_message.get_type()

        expected_p1_time = expected_message.get_p1_time()
        if expected_p1_time is not None:
            assert float(message.get_p1_time()) == pytest.approx(expected_p1_time, 1e-6)

        expected_system_time_sec = expected_message.get_system_time_sec()
        if expected_system_time_sec is not None:
            assert float(message.get_system_time_sec()) == pytest.approx(expected_system_time_sec, 1e-6)

    def _check_results(self, reader, expected_messages):
        num_matches = 0
        for header, payload in reader:
            assert num_matches < len(expected_messages)
            expected_message = expected_messages[num_matches]
            self._check_message(payload, expected_message)
            num_matches += 1
        assert num_matches == len(expected_messages)

    def _filter_by_time(self, messages, time_range: TimeRange):
        # Important: For relative time ranges, TimeRange.is_in_range() treats P1 and system times independently. For
        # example, consider the following log:
        #   Event (system time 0)
        #   Pose (P1 time 1)
        #   Pose (P1 time 2)
        #   Event (system time 2)
        #   Pose (P1 time 3)
        #   Pose (P1 time 4)
        #   Event (system time 4)
        #
        # Say we specify a relative time range ending after 2 seconds (inclusive). Since the first P1 timestamp is 1.0,
        # the results will include the pose message at time 3.0 (1.0 + 2), even though the first _system_ time was 0.0.
        #
        # Separately, for absolute time ranges, system time messages occurring before the first _included_ P1 timestamp
        # will be omitted (P1 and system time are not correlated, so we ignore anything outside the P1 time range).
        # Here, for an absolute time range ending at P1 time 2.0, the results should include just the event at system
        # time 2.0, but not 0.0 or 4.0.
        result = [m for m in messages if time_range.is_in_range(m)]
        time_range.restart()
        return result

    def test_read_all(self, data_path):
        messages = self._generate_mixed_data(data_path)

        reader = MixedLogReader(str(data_path))
        assert reader.index is None
        self._check_results(reader, messages)

        # Verify that we successfully generated an index file.
        assert reader.index is not None and len(reader.index) == len(messages)

    def test_read_pose(self, data_path):
        messages = self._generate_mixed_data(data_path)
        expected_messages = [m for m in messages if isinstance(m, PoseMessage)]

        reader = MixedLogReader(str(data_path))
        assert reader.index is None
        reader.filter_in_place((PoseMessage,))
        self._check_results(reader, expected_messages)

        # Verify that we successfully generated an index file, _and_ that the index was filtered to just pose messages.
        assert reader.index is not None and len(reader.index) == len(expected_messages)
        assert len(reader._original_index) == len(messages)

    def test_read_pose_constructor(self, data_path):
        messages = self._generate_mixed_data(data_path)
        expected_messages = [m for m in messages if isinstance(m, PoseMessage)]

        reader = MixedLogReader(str(data_path), message_types=(PoseMessage,))
        self._check_results(reader, expected_messages)

    def test_read_pose_mixed_binary(self, data_path):
        messages = self._generate_mixed_data_with_binary(data_path)
        expected_messages = [m for m in messages if isinstance(m, PoseMessage)]

        reader = MixedLogReader(str(data_path))
        assert reader.index is None
        reader.filter_in_place((PoseMessage,))
        self._check_results(reader, expected_messages)

        # Verify that we successfully generated an index file, _and_ that the index was filtered to just pose messages.
        assert reader.index is not None and len(reader.index) == len(expected_messages)
        assert len(reader._original_index) == len(messages)

    def test_read_events(self, data_path):
        messages = self._generate_mixed_data(data_path)
        expected_messages = [m for m in messages if isinstance(m, EventNotificationMessage)]

        reader = MixedLogReader(str(data_path))
        reader.filter_in_place((EventNotificationMessage,))
        self._check_results(reader, expected_messages)

    def test_read_no_generate_index(self, data_path):
        messages = self._generate_mixed_data(data_path)
        expected_messages = [m for m in messages if isinstance(m, PoseMessage)]

        reader = MixedLogReader(str(data_path), generate_index=False)
        assert reader.index is None
        reader.filter_in_place((PoseMessage,))
        self._check_results(reader, expected_messages)
        assert reader.index is None

    def test_read_with_index(self, data_path):
        messages = self._generate_mixed_data(data_path)
        expected_messages = [m for m in messages if isinstance(m, PoseMessage)]

        MixedLogReader.generate_index_file(str(data_path))
        assert os.path.exists(FileIndex.get_path(data_path))
        reader = MixedLogReader(str(data_path))
        reader.filter_in_place((PoseMessage,))
        assert reader.index is not None and len(reader.index) == len(expected_messages)

        self._check_results(reader, expected_messages)

    def test_read_mixed_binary_with_index(self, data_path):
        messages = self._generate_mixed_data_with_binary(data_path)
        expected_messages = [m for m in messages if isinstance(m, PoseMessage)]

        MixedLogReader.generate_index_file(str(data_path))
        assert os.path.exists(FileIndex.get_path(data_path))
        reader = MixedLogReader(str(data_path))
        reader.filter_in_place((PoseMessage,))
        assert reader.index is not None and len(reader.index) == len(expected_messages)

        self._check_results(reader, expected_messages)

    def test_read_overwrite_index(self, data_path):
        messages = self._generate_mixed_data(data_path)
        expected_messages = [m for m in messages if isinstance(m, PoseMessage)]

        MixedLogReader.generate_index_file(str(data_path))
        reader = MixedLogReader(str(data_path), ignore_index=True)

        # By default, we will be generating an index file, overwriting the existing one, so the reader should have
        # deleted the existing one.
        assert reader.index is None
        assert not os.path.exists(reader.index_path)

        reader.filter_in_place((PoseMessage,))
        self._check_results(reader, expected_messages)

        # Check that we generated a new index.
        assert os.path.exists(reader.index_path)
        assert reader.index is not None and len(reader.index) == len(expected_messages)
        assert len(reader._original_index) == len(messages)

    def test_read_ignore_index(self, data_path):
        messages = self._generate_mixed_data(data_path)
        expected_messages = [m for m in messages if isinstance(m, PoseMessage)]

        MixedLogReader.generate_index_file(str(data_path))
        reader = MixedLogReader(str(data_path), ignore_index=True, generate_index=False)
        assert reader.index is None

        # This time, we are not generating an index so we do _not_ delete the existing file and leave it intact.
        assert reader.index is None
        assert os.path.exists(reader.index_path)

        reader.filter_in_place((PoseMessage,))
        self._check_results(reader, expected_messages)

        assert reader.index is None

    def test_time_range_rel_start(self, data_path):
        messages = self._generate_mixed_data(data_path)
        time_range = TimeRange(end=1.0, absolute=False)
        expected_messages = self._filter_by_time(messages, time_range)

        reader = MixedLogReader(str(data_path), time_range=time_range)
        self._check_results(reader, expected_messages)

    def test_time_range_rel_end(self, data_path):
        messages = self._generate_mixed_data(data_path)
        time_range = TimeRange(end=2.0, absolute=False)
        expected_messages = self._filter_by_time(messages, time_range)

        reader = MixedLogReader(str(data_path), time_range=time_range)
        self._check_results(reader, expected_messages)

    def test_time_range_rel_both(self, data_path):
        messages = self._generate_mixed_data(data_path)
        time_range = TimeRange(start=1.0, end=2.0, absolute=False)
        expected_messages = self._filter_by_time(messages, time_range)

        reader = MixedLogReader(str(data_path), time_range=time_range)
        self._check_results(reader, expected_messages)

    def test_time_range_abs_start(self, data_path):
        messages = self._generate_mixed_data(data_path)
        time_range = TimeRange(start=2.0, absolute=True)
        expected_messages = self._filter_by_time(messages, time_range)

        reader = MixedLogReader(str(data_path), time_range=time_range)
        self._check_results(reader, expected_messages)

    def test_time_range_abs_end(self, data_path):
        messages = self._generate_mixed_data(data_path)
        time_range = TimeRange(end=2.0, absolute=True)
        expected_messages = self._filter_by_time(messages, time_range)

        reader = MixedLogReader(str(data_path), time_range=time_range)
        self._check_results(reader, expected_messages)

    def test_time_range_abs_both(self, data_path):
        messages = self._generate_mixed_data(data_path)
        time_range = TimeRange(start=1.0, end=2.0, absolute=True)
        expected_messages = self._filter_by_time(messages, time_range)

        reader = MixedLogReader(str(data_path), time_range=time_range)
        self._check_results(reader, expected_messages)
