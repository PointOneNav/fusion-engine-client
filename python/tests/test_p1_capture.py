import argparse
import os

import pytest

from fusion_engine_client.messages import (
    EventNotificationMessage,
    GNSSInfoMessage,
    InputDataType,
    InputDataWrapperMessage,
    MessageType,
    PoseMessage,
    Timestamp,
)
from fusion_engine_client.parsers import FusionEngineEncoder, MixedLogReader
from fusion_engine_client.applications.p1_capture import Application


def make_options(**overrides):
    defaults = dict(
        input=None,
        output=None,
        output_format=None,
        display='none',
        summary=False,
        verbose=0,
        message_type=None,
        invert=False,
        unwrap=False,
        wrapped_data_format='parent',
        wrapped_data_type=None,
        source_identifier=None,
        time=None,
        max=None,
        skip=0,
        progress=False,
        log_base_dir=None,
        log_type=None,
        ignore_index=False,
        log_timestamp_source=None,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class TestApplication:
    @pytest.fixture
    def tmp(self, tmp_path):
        return tmp_path

    # -------------------------------------------------------------------------
    # Helpers

    def _write_fe_messages(self, path, specs):
        """Write FusionEngine messages to *path*.

        Each entry in *specs* is one of:
          - bytes: written verbatim (raw binary, no FE framing)
          - (MessageClass, p1_time_sec): message with the given P1 time,
            source_identifier=0
          - (MessageClass, p1_time_sec, source_identifier): explicit source
        """
        encoder = FusionEngineEncoder()
        with open(str(path), 'wb') as f:
            for item in specs:
                if isinstance(item, bytes):
                    f.write(item)
                    continue
                msg_cls = item[0]
                p1_time = item[1]
                src_id = item[2] if len(item) > 2 else 0
                msg = msg_cls()
                if p1_time is not None and hasattr(msg, 'p1_time'):
                    msg.p1_time = Timestamp(float(p1_time))
                f.write(encoder.encode_message(msg, source_identifier=src_id))

    def _write_wrapper_messages(self, path, specs):
        """Write InputDataWrapperMessage records to *path*.

        Each entry: (InputDataType, payload_bytes, system_time_ns)
        """
        encoder = FusionEngineEncoder()
        with open(str(path), 'wb') as f:
            for dtype, payload, ts_ns in specs:
                msg = InputDataWrapperMessage()
                msg.system_time_ns = ts_ns
                msg.data_type = dtype
                msg.data = payload
                f.write(encoder.encode_message(msg))

    def _read_output(self, path):
        """Return list of (MessageType, source_identifier) from a .p1log file."""
        reader = MixedLogReader(str(path))
        return [(h.message_type, h.source_identifier) for h, _ in reader]

    def _run(self, input_path, **kwargs):
        opts = make_options(input=str(input_path), **kwargs)
        app = Application(options=opts)
        app.process_input()
        return app

    # -------------------------------------------------------------------------
    # File reading

    def test_read_pure_fe_file(self, tmp):
        path = tmp / 'input.p1log'
        self._write_fe_messages(path, [
            (PoseMessage, 0.0),
            (PoseMessage, 1.0),
            (GNSSInfoMessage, 1.0),
        ])
        app = self._run(path)
        assert app.messages_sent == 3

    def test_read_mixed_binary_file(self, tmp):
        """Non-FE binary interspersed with FE messages must not count as messages."""
        path = tmp / 'input.p1log'
        self._write_fe_messages(path, [
            b'\xde\xad\xbe\xef',
            (PoseMessage, 0.0),
            b'\xca\xfe\xba\xbe',
            (GNSSInfoMessage, 1.0),
            b'\x00\x01\x02\x03',
        ])
        app = self._run(path)
        assert app.messages_sent == 2

    def test_read_empty_file(self, tmp):
        path = tmp / 'empty.p1log'
        path.write_bytes(b'')
        app = self._run(path)
        assert app.messages_sent == 0

    # -------------------------------------------------------------------------
    # Message type filtering

    def test_message_type_no_filter_passes_all(self, tmp):
        path = tmp / 'input.p1log'
        self._write_fe_messages(path, [
            (PoseMessage, 0.0),
            (PoseMessage, 1.0),
            (GNSSInfoMessage, 1.0),
        ])
        app = self._run(path)
        assert app.messages_sent == 3

    def test_message_type_single_type(self, tmp):
        path = tmp / 'input.p1log'
        out = tmp / 'out.p1log'
        self._write_fe_messages(path, [
            (PoseMessage, 0.0),
            (PoseMessage, 1.0),
            (GNSSInfoMessage, 1.0),
        ])
        app = self._run(path, output=str(out), output_format='p1log',
                        message_type=['Pose'])
        assert app.messages_sent == 2
        assert all(t == MessageType.POSE for t, _ in self._read_output(out))

    def test_message_type_comma_list(self, tmp):
        path = tmp / 'input.p1log'
        out = tmp / 'out.p1log'
        self._write_fe_messages(path, [
            (PoseMessage, 0.0),
            (GNSSInfoMessage, 1.0),
            (EventNotificationMessage, None),
        ])
        app = self._run(path, output=str(out), output_format='p1log',
                        message_type=['Pose,GNSSInfo'])
        assert app.messages_sent == 2
        types = {t for t, _ in self._read_output(out)}
        assert types == {MessageType.POSE, MessageType.GNSS_INFO}

    def test_message_type_repeated_flag(self, tmp):
        path = tmp / 'input.p1log'
        out = tmp / 'out.p1log'
        self._write_fe_messages(path, [
            (PoseMessage, 0.0),
            (GNSSInfoMessage, 1.0),
            (EventNotificationMessage, None),
        ])
        app = self._run(path, output=str(out), output_format='p1log',
                        message_type=['Pose', 'GNSSInfo'])
        assert app.messages_sent == 2
        types = {t for t, _ in self._read_output(out)}
        assert types == {MessageType.POSE, MessageType.GNSS_INFO}

    def test_message_type_wildcard(self, tmp):
        path = tmp / 'input.p1log'
        out = tmp / 'out.p1log'
        self._write_fe_messages(path, [
            (PoseMessage, 0.0),
            (GNSSInfoMessage, 1.0),
        ])
        # GNSS* should match GNSSInfo but not Pose
        app = self._run(path, output=str(out), output_format='p1log',
                        message_type=['GNSS*'])
        assert app.messages_sent >= 1
        types = {t for t, _ in self._read_output(out)}
        assert MessageType.POSE not in types
        assert MessageType.GNSS_INFO in types

    def test_message_type_unknown_name_exits(self, tmp):
        path = tmp / 'input.p1log'
        path.write_bytes(b'')
        with pytest.raises(SystemExit) as exc:
            Application(options=make_options(input=str(path),
                                             message_type=['NoSuchType_XYZ']))
        assert exc.value.code == 1

    # -------------------------------------------------------------------------
    # Source ID filtering

    def test_source_id_no_filter_passes_all(self, tmp):
        path = tmp / 'input.p1log'
        # 3 messages per source
        self._write_fe_messages(path, [
            (PoseMessage, float(i), src)
            for src in range(3)
            for i in range(3)
        ])
        app = self._run(path)
        assert app.messages_sent == 9

    def test_source_id_single(self, tmp):
        path = tmp / 'input.p1log'
        self._write_fe_messages(path, [
            (PoseMessage, float(i), src)
            for src in range(3)
            for i in range(3)
        ])
        app = self._run(path, source_identifier=['1'])
        assert app.messages_sent == 3

    def test_source_id_multiple(self, tmp):
        path = tmp / 'input.p1log'
        self._write_fe_messages(path, [
            (PoseMessage, float(i), src)
            for src in range(3)
            for i in range(3)
        ])
        app = self._run(path, source_identifier=['0', '2'])
        assert app.messages_sent == 6

    def test_source_id_non_integer_exits(self, tmp):
        path = tmp / 'input.p1log'
        path.write_bytes(b'')
        with pytest.raises(SystemExit) as exc:
            Application(options=make_options(input=str(path),
                                             source_identifier=['abc']))
        assert exc.value.code == 1

    def test_source_id_combined_with_message_type(self, tmp):
        """Only messages matching both the type filter and source ID are forwarded."""
        path = tmp / 'input.p1log'
        out = tmp / 'out.p1log'
        self._write_fe_messages(path, [
            (PoseMessage, 0.0, 0),
            (PoseMessage, 1.0, 1),
            (GNSSInfoMessage, 1.0, 1),
        ])
        app = self._run(path, output=str(out), output_format='p1log',
                        message_type=['Pose'], source_identifier=['1'])
        assert app.messages_sent == 1
        results = self._read_output(out)
        assert all(t == MessageType.POSE for t, _ in results)
        assert all(s == 1 for _, s in results)

    # -------------------------------------------------------------------------
    # Time range filtering
    #
    # Relative time ranges with a defined start are unreliable when reading
    # from a file: the Application passes the same TimeRange object to both
    # MixedLogReader (for index-level pre-filtering) and _apply_filters (for
    # per-message filtering), so the stateful TimeRange is consumed twice.
    # Absolute time ranges and open-start relative ranges are unaffected and
    # are tested here.

    def test_time_range_absolute(self, tmp):
        path = tmp / 'input.p1log'
        self._write_fe_messages(path, [(PoseMessage, float(i)) for i in range(6)])
        app = self._run(path, time='1:3:abs')
        assert app.messages_sent == 2  # t=1, t=2

    def test_time_range_absolute_open_start(self, tmp):
        path = tmp / 'input.p1log'
        self._write_fe_messages(path, [(PoseMessage, float(i)) for i in range(6)])
        app = self._run(path, time=':3:abs')
        assert app.messages_sent == 3  # t=0, t=1, t=2

    def test_time_range_absolute_open_end(self, tmp):
        path = tmp / 'input.p1log'
        self._write_fe_messages(path, [(PoseMessage, float(i)) for i in range(6)])
        app = self._run(path, time='3::abs')
        assert app.messages_sent == 3  # t=3, t=4, t=5

    def test_time_range_relative_open_start(self, tmp):
        """Open-start relative range works correctly with file input."""
        path = tmp / 'input.p1log'
        self._write_fe_messages(path, [(PoseMessage, float(i)) for i in range(6)])
        app = self._run(path, time=':2')
        assert app.messages_sent == 2  # t=0, t=1

    def test_time_range_no_matches(self, tmp):
        path = tmp / 'input.p1log'
        self._write_fe_messages(path, [(PoseMessage, float(i)) for i in range(6)])
        app = self._run(path, time='100:200:abs')
        assert app.messages_sent == 0

    def test_time_range_combined_with_message_type(self, tmp):
        path = tmp / 'input.p1log'
        out = tmp / 'out.p1log'
        self._write_fe_messages(path, [
            (PoseMessage, 0.0),
            (GNSSInfoMessage, 0.0),
            (PoseMessage, 1.0),
            (GNSSInfoMessage, 1.0),
            (PoseMessage, 5.0),
        ])
        app = self._run(path, output=str(out), output_format='p1log',
                        message_type=['Pose'], time=':2:abs')
        assert app.messages_sent == 2  # Pose at t=0 and t=1
        types = {t for t, _ in self._read_output(out)}
        assert types == {MessageType.POSE}

    # -------------------------------------------------------------------------
    # InputDataWrapper filtering

    def test_input_data_wrapper_no_filter(self, tmp):
        path = tmp / 'input.p1log'
        self._write_wrapper_messages(path, [
            (InputDataType.M_TYPE_RTCM3_UNKNOWN, b'rtcm', 0),
            (InputDataType.M_TYPE_RTCM3_UNKNOWN, b'rtcm', 1_000_000_000),
            (InputDataType.M_TYPE_EXTERNAL_UNFRAMED_GNSS, b'gnss', 2_000_000_000),
        ])
        app = self._run(path)
        assert app.messages_sent == 3

    def test_input_data_wrapper_filter_by_data_type(self, tmp):
        path = tmp / 'input.p1log'
        self._write_wrapper_messages(path, [
            (InputDataType.M_TYPE_RTCM3_UNKNOWN, b'rtcm_0', 0),
            (InputDataType.M_TYPE_RTCM3_UNKNOWN, b'rtcm_1', 1_000_000_000),
            (InputDataType.M_TYPE_EXTERNAL_UNFRAMED_GNSS, b'gnss', 2_000_000_000),
        ])
        app = self._run(path, wrapped_data_type=['RTCM3_UNKNOWN'])
        assert app.messages_sent == 2

    def test_input_data_wrapper_invert_data_type(self, tmp):
        path = tmp / 'input.p1log'
        self._write_wrapper_messages(path, [
            (InputDataType.M_TYPE_RTCM3_UNKNOWN, b'rtcm_0', 0),
            (InputDataType.M_TYPE_RTCM3_UNKNOWN, b'rtcm_1', 1_000_000_000),
            (InputDataType.M_TYPE_EXTERNAL_UNFRAMED_GNSS, b'gnss', 2_000_000_000),
        ])
        app = self._run(path, wrapped_data_type=['RTCM3_UNKNOWN'], invert=True)
        assert app.messages_sent == 1

    def test_unwrap_requires_output_exits(self, tmp):
        path = tmp / 'input.p1log'
        path.write_bytes(b'')
        with pytest.raises(SystemExit) as exc:
            Application(options=make_options(input=str(path), unwrap=True,
                                             output=None))
        assert exc.value.code == 1

    def test_unwrap_rejects_message_type_exits(self, tmp):
        path = tmp / 'input.p1log'
        path.write_bytes(b'')
        with pytest.raises(SystemExit) as exc:
            Application(options=make_options(input=str(path), unwrap=True,
                                             message_type=['Pose'],
                                             output=str(tmp / 'out.bin')))
        assert exc.value.code == 1

    def test_unwrap_rejects_multiple_data_types_exits(self, tmp):
        path = tmp / 'input.p1log'
        path.write_bytes(b'')
        with pytest.raises(SystemExit) as exc:
            Application(options=make_options(
                input=str(path), unwrap=True,
                wrapped_data_type=['RTCM3_UNKNOWN', 'EXTERNAL_UNFRAMED_GNSS'],
                output=str(tmp / 'out.bin')))
        assert exc.value.code == 1

    # -------------------------------------------------------------------------
    # Output formats

    def test_output_p1log_contains_only_fe_messages(self, tmp):
        """p1log output strips non-FE binary and contains exactly the FE messages."""
        path = tmp / 'input.p1log'
        out = tmp / 'out.p1log'
        self._write_fe_messages(path, [
            b'\xde\xad\xbe\xef',
            (PoseMessage, 0.0),
            b'\xca\xfe',
            (GNSSInfoMessage, 1.0),
        ])
        app = self._run(path, output=str(out), output_format='p1log')
        assert app.messages_sent == 2
        types = [t for t, _ in self._read_output(out)]
        assert types == [MessageType.POSE, MessageType.GNSS_INFO]

    def test_output_p1log_message_type_filter(self, tmp):
        """p1log output with a type filter contains only the requested type."""
        path = tmp / 'input.p1log'
        out = tmp / 'out.p1log'
        self._write_fe_messages(path, [
            (PoseMessage, 0.0),
            (GNSSInfoMessage, 0.0),
            (PoseMessage, 1.0),
        ])
        self._run(path, output=str(out), output_format='p1log',
                  message_type=['Pose'])
        types = [t for t, _ in self._read_output(out)]
        assert types == [MessageType.POSE, MessageType.POSE]

    def test_output_raw_matches_input_for_pure_fe_file(self, tmp):
        """Raw output of a pure FE file is byte-identical to the input."""
        path = tmp / 'input.p1log'
        out = tmp / 'out.bin'
        encoder = FusionEngineEncoder()
        raw_content = b''.join(
            encoder.encode_message(PoseMessage()) for _ in range(3)
        )
        path.write_bytes(raw_content)

        self._run(path, output=str(out), output_format='raw')
        assert out.read_bytes() == raw_content

    def test_output_csv_header_and_rows(self, tmp):
        """CSV output starts with the expected header and has one row per message."""
        path = tmp / 'input.p1log'
        out = tmp / 'out.csv'
        self._write_fe_messages(path, [
            (PoseMessage, 0.0),
            (PoseMessage, 1.0),
            (PoseMessage, 2.0),
        ])
        self._run(path, output=str(out), output_format='csv')
        lines = out.read_text().splitlines()
        assert lines[0] == 'host_time,type,p1_time,sys_time'
        assert len(lines) == 4  # header + 3 data rows
        for line in lines[1:]:
            fields = line.split(',')
            assert fields[1] == 'POSE'

    def test_output_raw_with_type_filter_produces_p1log(self, tmp):
        """--output-format=raw plus --message-type is silently demoted to p1log."""
        path = tmp / 'input.p1log'
        out = tmp / 'out.bin'
        self._write_fe_messages(path, [
            (PoseMessage, 0.0),
            (GNSSInfoMessage, 0.0),
        ])
        app = self._run(path, output=str(out), output_format='raw',
                        message_type=['Pose'])
        assert app.messages_sent == 1
        # Output is a valid p1log containing only Pose
        types = [t for t, _ in self._read_output(out)]
        assert types == [MessageType.POSE]

    # -------------------------------------------------------------------------
    # --max and --skip

    def test_max_stops_after_n_messages(self, tmp):
        path = tmp / 'input.p1log'
        self._write_fe_messages(path, [(PoseMessage, float(i)) for i in range(10)])
        app = self._run(path, max=3)
        assert app.messages_sent == 3

    def test_skip_omits_first_n_messages(self, tmp):
        path = tmp / 'input.p1log'
        self._write_fe_messages(path, [(PoseMessage, float(i)) for i in range(10)])
        app = self._run(path, skip=4)
        assert app.messages_sent == 6

    def test_skip_counts_only_filtered_messages(self, tmp):
        """--skip counts only messages that pass the type filter."""
        path = tmp / 'input.p1log'
        specs = []
        for i in range(5):
            specs.append((PoseMessage, float(i)))
            specs.append((GNSSInfoMessage, float(i)))
        self._write_fe_messages(path, specs)
        # 5 Pose messages total; skipping 4 filtered (Pose) ones leaves 1
        app = self._run(path, message_type=['Pose'], skip=4)
        assert app.messages_sent == 1

    def test_max_and_skip_combined(self, tmp):
        path = tmp / 'input.p1log'
        self._write_fe_messages(path, [(PoseMessage, float(i)) for i in range(10)])
        app = self._run(path, skip=2, max=3)
        assert app.messages_sent == 3

    def test_max_and_skip_with_type_filter(self, tmp):
        """--skip and --max both count only messages that pass the type filter."""
        path = tmp / 'input.p1log'
        specs = []
        for i in range(10):
            specs.append((PoseMessage, float(i)))
            specs.append((GNSSInfoMessage, float(i)))
        self._write_fe_messages(path, specs)
        # 10 Pose messages; skip 3 filtered, then take max 4 → 4 sent
        app = self._run(path, message_type=['Pose'], skip=3, max=4)
        assert app.messages_sent == 4

    def test_max_counts_only_matching_type(self, tmp):
        """--max counts only messages that pass the type filter."""
        path = tmp / 'input.p1log'
        # Interleave Pose and GNSSInfo
        specs = []
        for i in range(5):
            specs.append((PoseMessage, float(i)))
            specs.append((GNSSInfoMessage, float(i)))
        self._write_fe_messages(path, specs)
        app = self._run(path, message_type=['Pose'], max=2)
        assert app.messages_sent == 2
