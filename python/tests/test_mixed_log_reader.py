import math
import os

import pytest

from fusion_engine_client.messages import *
from fusion_engine_client.parsers import FusionEngineEncoder, MixedLogReader, FileIndex
from fusion_engine_client.utils.time_range import TimeRange


class TestClass:
    @pytest.fixture
    def data_path(self, tmpdir):
        data_path = tmpdir.join('test_file.p1log')
        yield data_path

    def _generate_data(self, data_path, message_types):
        messages = []
        prev_p1_time_sec = None
        prev_system_time_sec = None
        for i, (message_cls, time_sec) in enumerate(message_types):
            if isinstance(message_cls, bytes):
                messages.append(message_cls)
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

            setattr(message, '_message_index', i)

            messages.append(message)

        encoder = FusionEngineEncoder()
        with open(data_path, 'wb') as f:
            for message in messages:
                if isinstance(message, bytes):
                    f.write(message)
                else:
                    f.write(encoder.encode_message(message))

        return [m for m in messages if not isinstance(m, bytes)]

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
            # Include one bogus binary message that starts with an FE preamble.
            (MessageHeader.SYNC + b'34', None),
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
            assert float(message.get_p1_time()) == pytest.approx(expected_p1_time, 1e-6), "P1 time mismatch."

        expected_system_time_sec = expected_message.get_system_time_sec()
        if expected_system_time_sec is not None:
            assert float(message.get_system_time_sec()) == pytest.approx(expected_system_time_sec, 1e-6), \
                   "System time mismatch."

    def _check_results(self, reader, expected_messages, check_message_index=False):
        num_matches = 0
        for entry in reader:
            if check_message_index:
                header, payload, message_index = entry
            else:
                header, payload = entry

            assert num_matches < len(expected_messages), "Number of returned messages exceeds expected."
            expected_message = expected_messages[num_matches]
            if check_message_index:
                assert message_index == expected_message._message_index
            self._check_message(payload, expected_message)
            num_matches += 1
        assert num_matches == len(expected_messages), "Number of returned messages does not match expected."

    def _filter_by_time(self, messages, time_range: TimeRange):
        result = [m for m in messages if time_range.is_in_range(m)]
        time_range.restart()
        return result

    def test_read_all(self, data_path):
        messages = self._generate_mixed_data(data_path)

        reader = MixedLogReader(str(data_path))
        self._check_results(reader, messages)

        # Verify that we successfully generated an index file.
        assert reader.index is not None and len(reader.index) == len(messages)

        # Now rewind and read again. This time, it should read from the index and produce the same results.
        reader.rewind()
        self._check_results(reader, messages)

    def test_read_pose(self, data_path):
        messages = self._generate_mixed_data(data_path)
        expected_messages = [m for m in messages if isinstance(m, PoseMessage)]

        reader = MixedLogReader(str(data_path))
        reader.filter_in_place((PoseMessage,))
        self._check_results(reader, expected_messages)

        # Verify that we successfully generated an index file, _and_ that the index was filtered to just pose messages.
        assert reader.index is not None and len(reader.index) == len(expected_messages)
        assert len(reader._original_index) == len(messages)

        # Now rewind and read again. This time, it should read from the index and produce the same results.
        reader.rewind()
        self._check_results(reader, expected_messages)

        # Last, rewind and read a different message type. This should also read successfully from the index.
        expected_messages = [m for m in messages if isinstance(m, EventNotificationMessage)]
        reader.rewind()
        reader.filter_in_place((EventNotificationMessage,), clear_existing=True)
        self._check_results(reader, expected_messages)

    def test_read_pose_constructor(self, data_path):
        messages = self._generate_mixed_data(data_path)
        expected_messages = [m for m in messages if isinstance(m, PoseMessage)]

        reader = MixedLogReader(str(data_path), message_types=(PoseMessage,))
        self._check_results(reader, expected_messages)

    def test_read_pose_mixed_binary(self, data_path):
        messages = self._generate_mixed_data_with_binary(data_path)
        expected_messages = [m for m in messages if isinstance(m, PoseMessage)]

        reader = MixedLogReader(str(data_path))
        reader.filter_in_place((PoseMessage,))
        self._check_results(reader, expected_messages)

        # Verify that we successfully generated an index file, _and_ that the index was filtered to just pose messages.
        assert reader.index is not None and len(reader.index) == len(expected_messages)
        assert len(reader._original_index) == len(messages)

    def test_return_message_index(self, data_path):
        messages = self._generate_mixed_data(data_path)

        # Read and return message index generated _without_ a file index.
        reader = MixedLogReader(str(data_path), return_message_index=True)
        self._check_results(reader, messages, check_message_index=True)

        # Now rewind and read again. This time, it should read from the index and produce the same results.
        reader.rewind()
        self._check_results(reader, messages, check_message_index=True)

    def test_return_message_index_pose(self, data_path):
        messages = self._generate_mixed_data(data_path)
        expected_messages = [m for m in messages if isinstance(m, PoseMessage)]

        # Read and return message index generated _without_ a file index.
        reader = MixedLogReader(str(data_path), return_message_index=True)
        reader.filter_in_place((PoseMessage,))
        self._check_results(reader, expected_messages, check_message_index=True)

        # Now rewind and read again. This time, it should read from the index and produce the same results.
        reader.rewind()
        self._check_results(reader, expected_messages, check_message_index=True)

    def test_read_events(self, data_path):
        messages = self._generate_mixed_data(data_path)
        expected_messages = [m for m in messages if isinstance(m, EventNotificationMessage)]

        reader = MixedLogReader(str(data_path))
        reader.filter_in_place((EventNotificationMessage,))
        self._check_results(reader, expected_messages)

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

        reader.filter_in_place((PoseMessage,))
        self._check_results(reader, expected_messages)

        # Check that we generated a new index.
        assert os.path.exists(FileIndex.get_path(data_path))
        assert reader.index is not None and len(reader.index) == len(expected_messages)
        assert len(reader._original_index) == len(messages)

    def test_read_ignore_index(self, data_path):
        messages = self._generate_mixed_data(data_path)
        expected_messages = [m for m in messages if isinstance(m, PoseMessage)]

        MixedLogReader.generate_index_file(str(data_path))
        reader = MixedLogReader(str(data_path), ignore_index=True, save_index=False)

        # This time, we are not generating an index so we do _not_ delete the existing file and leave it intact.
        assert os.path.exists(FileIndex.get_path(data_path))

        reader.filter_in_place((PoseMessage,))
        self._check_results(reader, expected_messages)

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
        messages = self._generate_mixed_data(data_path)
        expected_messages = self._filter_by_time(messages, time_range)
        if use_index:
            MixedLogReader.generate_index_file(str(data_path))
        reader = MixedLogReader(str(data_path), time_range=time_range)
        self._check_results(reader, expected_messages)

    def _test_rewind(self, data_path, use_index):
        messages = self._generate_mixed_data_with_binary(data_path)
        expected_messages = [m for m in messages if isinstance(m, PoseMessage)]

        if use_index:
            MixedLogReader.generate_index_file(str(data_path))

        reader = MixedLogReader(str(data_path))
        reader.filter_in_place((PoseMessage,))
        for i in range(3):
            _, message = next(reader)
            self._check_message(message, expected_messages[i])


        assert reader.index is not None

        reader.rewind()
        self._check_results(reader, expected_messages)

        if not use_index:
            assert reader.index is not None and len(reader.index) == len(expected_messages)

    def test_rewind_no_index(self, data_path):
        self._test_rewind(data_path, use_index=False)

    def test_rewind_with_index(self, data_path):
        self._test_rewind(data_path, use_index=True)

    def _test_partial_filter(self, data_path, use_index):
        messages = self._generate_mixed_data_with_binary(data_path)

        if use_index:
            MixedLogReader.generate_index_file(str(data_path))

        # Read the first 3 messages without filtering. This should include 2 pose messages.
        reader = MixedLogReader(str(data_path))
        for i in range(3):
            _, message = next(reader)
            self._check_message(message, messages[i])

        # Next, filter to just pose messages. This should continue where we left off.
        expected_messages = [m for m in messages if isinstance(m, PoseMessage)]
        expected_messages = expected_messages[2:]
        reader.filter_in_place((PoseMessage,))
        self._check_results(reader, expected_messages)

    def test_partial_filter_no_index(self, data_path):
        self._test_partial_filter(data_path, use_index=False)

    def test_partial_filter_with_index(self, data_path):
        self._test_partial_filter(data_path, use_index=True)

    def _test_reset_filter(self, data_path, use_index):
        messages = self._generate_mixed_data_with_binary(data_path)

        if use_index:
            MixedLogReader.generate_index_file(str(data_path))

        # Read the first 2 pose messages.
        reader = MixedLogReader(str(data_path))
        reader.filter_in_place((PoseMessage,))
        expected_messages = [m for m in messages if isinstance(m, PoseMessage)][:2]
        for i in range(2):
            _, message = next(reader)
            self._check_message(message, expected_messages[i])

        # Now, reset the filter to include all message types. This should continue where we left off, starting with the
        # event message at system time 2.0.
        idx = messages.index(expected_messages[-1])
        expected_messages = messages[idx + 1:]
        reader.filter_in_place(None, clear_existing=True)
        self._check_results(reader, expected_messages)

    def test_reset_filter_no_index(self, data_path):
        self._test_reset_filter(data_path, use_index=False)

    def test_reset_filter_with_index(self, data_path):
        self._test_reset_filter(data_path, use_index=True)

    def _test_redo_filter(self, data_path, use_index):
        messages = self._generate_mixed_data_with_binary(data_path)

        if use_index:
            MixedLogReader.generate_index_file(str(data_path))

        # Unlike reset_filter, here we intentionally do _not_ read anything after setting the filter once. The idea is
        # to make sure that if we change the filter but havn't read anything, we still end up reading the first element.
        reader = MixedLogReader(str(data_path))
        reader.filter_in_place((PoseMessage,))

        # Now, change the filter to allow all messages. We expect to read starting at the first entry: we haven't read
        # anything yet, so we shouldn't be picking up where we left off.
        reader.filter_in_place((PoseMessage, EventNotificationMessage), clear_existing=True)
        for i in range(3):
            _, message = next(reader)
            self._check_message(message, messages[i])

    def test_redo_filter_no_index(self, data_path):
        self._test_redo_filter(data_path, use_index=False)

    def test_redo_filter_with_index(self, data_path):
        self._test_redo_filter(data_path, use_index=True)

    def _test_seek_to_eof(self, data_path, use_index):
        messages = self._generate_mixed_data_with_binary(data_path)

        if use_index:
            MixedLogReader.generate_index_file(str(data_path))

        # Read the first 2 pose messages.
        reader = MixedLogReader(str(data_path))
        reader.filter_in_place((PoseMessage,))
        expected_messages = [m for m in messages if isinstance(m, PoseMessage)][:2]
        for i in range(2):
            _, message = next(reader)
            self._check_message(message, expected_messages[i])

        # Now jump to EOF.
        reader.seek_to_eof()

    def test_seek_to_eof_no_index(self, data_path):
        self._test_seek_to_eof(data_path, use_index=False)

    def test_seek_to_eof_with_index(self, data_path):
        self._test_seek_to_eof(data_path, use_index=True)
