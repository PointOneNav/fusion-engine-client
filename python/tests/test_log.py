import json
import os

import pytest

from fusion_engine_client.utils.log import get_candidate_file_list, locate_log

LOG_HASH = '95cf9ba38f0b40f7af13b072401a82d7'


def _write_stub(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(b'\x00')


def make_log_dir(base_dir, log_id, files):
    """Create <base_dir>/<log_id>/ with 1-byte stub files. Return log dir path."""
    log_dir = os.path.join(str(base_dir), log_id)
    os.makedirs(log_dir, exist_ok=True)
    for f in files:
        _write_stub(os.path.join(log_dir, f))
    return log_dir


def make_manifest(log_dir, data_filename, guid=None):
    """Write manifest.json with {"channels": [data_filename]} in log_dir."""
    with open(os.path.join(str(log_dir), 'manifest.json'), 'w') as f:
        manifest = {'channels': [data_filename]}
        if guid is not None:
            manifest['guid'] = guid
        json.dump(manifest, f)


def make_log_base_dir(tmpdir, log_id, files):
    """
    Create realistic nested log structure:
      tmpdir/log_base/2024-01-15/device_name/<log_id>/[files]

    Returns (log_base_path, log_dir_path).
    """
    log_base = str(tmpdir.mkdir('log_base'))
    nested = os.path.join(log_base, '2024-01-15', 'device_name')
    log_dir = make_log_dir(nested, log_id, files)
    return log_base, log_dir


class TestGetCandidateFileList:
    def test_auto(self):
        files = get_candidate_file_list('auto')
        assert 'output/fusion_engine.p1log' in files
        assert 'output/diagnostics.p1log' in files
        # User output before diagnostic.
        assert files.index('output/fusion_engine.p1log') < files.index('output/diagnostics.p1log')

    def test_diagnostic(self):
        files = get_candidate_file_list('diagnostic')
        assert 'output/diagnostics.p1log' in files
        assert 'output/fusion_engine.p1log' not in files

    def test_diag_alias(self):
        assert get_candidate_file_list('diag') == get_candidate_file_list('diagnostic')

    def test_user(self):
        files = get_candidate_file_list('user')
        assert 'output/fusion_engine.p1log' in files
        assert 'output/diagnostics.p1log' not in files

    def test_invalid(self):
        with pytest.raises(ValueError):
            get_candidate_file_list('bogus')


class TestLocateLogDirectFile:
    """User specifies an exact file path."""

    def test_file_user_p1log(self, tmpdir):
        path = os.path.join(str(tmpdir), 'fusion_engine.p1log')
        _write_stub(path)
        assert locate_log(path, log_base_dir=str(tmpdir)) == path

    def test_file_diag_p1log(self, tmpdir):
        path = os.path.join(str(tmpdir), 'output', 'diagnostics.p1log')
        _write_stub(path)
        assert locate_log(path, log_base_dir=str(tmpdir)) == path

    def test_file_input_p1log(self, tmpdir):
        path = os.path.join(str(tmpdir), 'input.p1log')
        _write_stub(path)
        assert locate_log(path, log_base_dir=str(tmpdir)) == path

    def test_file_not_found(self, tmpdir):
        path = os.path.join(str(tmpdir), 'nonexistent.p1log')
        assert locate_log(path, log_base_dir=str(tmpdir)) is None

    def test_file_empty_direct(self, tmpdir):
        # When a file is specified directly, the empty-file skip does not apply.
        path = os.path.join(str(tmpdir), 'fusion_engine.p1log')
        open(path, 'wb').close()
        assert locate_log(path, log_base_dir=str(tmpdir)) == path


class TestLocateLogDirectory:
    """User passes path to a log directory."""

    def test_dir_user_output(self, tmpdir):
        log_dir = make_log_dir(tmpdir, LOG_HASH, ['output/fusion_engine.p1log'])
        assert locate_log(log_dir, log_base_dir=str(tmpdir)) == \
            os.path.join(log_dir, 'output', 'fusion_engine.p1log')

    def test_dir_diag(self, tmpdir):
        log_dir = make_log_dir(tmpdir, LOG_HASH, ['output/diagnostics.p1log'])
        assert locate_log(log_dir, log_base_dir=str(tmpdir)) == \
            os.path.join(log_dir, 'output', 'diagnostics.p1log')

    def test_dir_input_p1log(self, tmpdir):
        log_dir = make_log_dir(tmpdir, LOG_HASH, ['input.p1log'])
        assert locate_log(log_dir, log_base_dir=str(tmpdir)) == \
            os.path.join(log_dir, 'input.p1log')

    def test_dir_manifest_data(self, tmpdir):
        log_dir = make_log_dir(tmpdir, LOG_HASH, ['test_file.bin'])
        make_manifest(log_dir, 'test_file.bin')
        assert locate_log(log_dir, log_base_dir=str(tmpdir)) == \
            os.path.join(log_dir, 'test_file.bin')

    def test_dir_priority_user_over_diag(self, tmpdir):
        log_dir = make_log_dir(tmpdir, LOG_HASH,
                               ['output/fusion_engine.p1log', 'output/diagnostics.p1log'])
        assert locate_log(log_dir, log_base_dir=str(tmpdir)) == \
            os.path.join(log_dir, 'output', 'fusion_engine.p1log')

    def test_dir_empty_first_candidate_skipped(self, tmpdir):
        log_dir = make_log_dir(tmpdir, LOG_HASH, ['output/diagnostics.p1log'])
        open(os.path.join(log_dir, 'output', 'fusion_engine.p1log'), 'wb').close()
        assert locate_log(log_dir, log_base_dir=str(tmpdir), log_type='auto') == \
            os.path.join(log_dir, 'output', 'diagnostics.p1log')

    def test_dir_no_candidates(self, tmpdir):
        log_dir = make_log_dir(tmpdir, LOG_HASH, ['irrelevant.txt'])
        assert locate_log(log_dir, log_base_dir=str(tmpdir)) is None

    def test_logtype_diag_skips_user(self, tmpdir):
        log_dir = make_log_dir(tmpdir, LOG_HASH,
                               ['output/fusion_engine.p1log', 'output/diagnostics.p1log'])
        assert locate_log(log_dir, log_base_dir=str(tmpdir), log_type='diagnostic') == \
            os.path.join(log_dir, 'output', 'diagnostics.p1log')

    def test_logtype_user_skips_diag(self, tmpdir):
        log_dir = make_log_dir(tmpdir, LOG_HASH,
                               ['output/fusion_engine.p1log', 'output/diagnostics.p1log'])
        assert locate_log(log_dir, log_base_dir=str(tmpdir), log_type='user') == \
            os.path.join(log_dir, 'output', 'fusion_engine.p1log')

    def test_logtype_user_no_match(self, tmpdir):
        log_dir = make_log_dir(tmpdir, LOG_HASH, ['output/diagnostics.p1log'])
        assert locate_log(log_dir, log_base_dir=str(tmpdir), log_type='user') is None

    def test_logtype_diag_no_match(self, tmpdir):
        log_dir = make_log_dir(tmpdir, LOG_HASH, ['output/fusion_engine.p1log'])
        assert locate_log(log_dir, log_base_dir=str(tmpdir), log_type='diagnostic') is None


class TestLocateLogPatternMatch:
    """User passes partial/full log hash; locate_log searches under log_base_dir."""

    def test_partial_hash(self, tmpdir):
        log_base, log_dir = make_log_base_dir(tmpdir, LOG_HASH, ['output/diagnostics.p1log'])
        assert locate_log(LOG_HASH[:8], log_base_dir=log_base) == \
            os.path.join(log_dir, 'output', 'diagnostics.p1log')

    def test_full_hash(self, tmpdir):
        log_base, log_dir = make_log_base_dir(tmpdir, LOG_HASH, ['output/diagnostics.p1log'])
        assert locate_log(LOG_HASH, log_base_dir=log_base) == \
            os.path.join(log_dir, 'output', 'diagnostics.p1log')

    def test_no_match(self, tmpdir):
        log_base, _ = make_log_base_dir(tmpdir, LOG_HASH, ['output/diagnostics.p1log'])
        assert locate_log('zzz000', log_base_dir=log_base) is None

    def test_ambiguous_prefix(self, tmpdir):
        log_base = str(tmpdir.mkdir('log_base'))
        nested = os.path.join(log_base, '2024-01-15', 'device_name')
        make_log_dir(nested, LOG_HASH, ['output/diagnostics.p1log'])
        make_log_dir(nested, '95cf9000000000000000000000000000', ['output/diagnostics.p1log'])
        assert locate_log('95cf9', log_base_dir=log_base) is None

    def test_full_hash_resolves_ambiguity(self, tmpdir):
        log_base = str(tmpdir.mkdir('log_base'))
        nested = os.path.join(log_base, '2024-01-15', 'device_name')
        log_dir = make_log_dir(nested, LOG_HASH, ['output/diagnostics.p1log'])
        make_log_dir(nested, '95cf9000000000000000000000000000', ['output/diagnostics.p1log'])
        assert locate_log(LOG_HASH, log_base_dir=log_base) == \
            os.path.join(log_dir, 'output', 'diagnostics.p1log')

    def test_pattern_diag_type(self, tmpdir):
        log_base, log_dir = make_log_base_dir(tmpdir, LOG_HASH, ['output/diagnostics.p1log'])
        assert locate_log(LOG_HASH[:8], log_base_dir=log_base, log_type='diagnostic') == \
            os.path.join(log_dir, 'output', 'diagnostics.p1log')

    def test_pattern_diag_type_no_match(self, tmpdir):
        log_base, _ = make_log_base_dir(tmpdir, LOG_HASH, ['output/fusion_engine.p1log'])
        assert locate_log(LOG_HASH[:8], log_base_dir=log_base, log_type='diagnostic') is None

    def test_pattern_manifest_only(self, tmpdir):
        log_base, log_dir = make_log_base_dir(tmpdir, LOG_HASH, ['test_file.bin'])
        make_manifest(log_dir, 'test_file.bin')
        assert locate_log(LOG_HASH[:8], log_base_dir=log_base) == \
            os.path.join(log_dir, 'test_file.bin')

    def test_pattern_manifest_missing_data_file(self, tmpdir):
        log_base, log_dir = make_log_base_dir(tmpdir, LOG_HASH, [])
        make_manifest(log_dir, 'missing.bin')
        assert locate_log(LOG_HASH[:8], log_base_dir=log_base) is None


class TestLocateLogReturnModes:
    def _make_log(self, tmpdir):
        return make_log_base_dir(tmpdir, LOG_HASH, ['output/diagnostics.p1log'])

    def test_file_only(self, tmpdir):
        log_base, log_dir = self._make_log(tmpdir)
        result = locate_log(LOG_HASH[:8], log_base_dir=log_base)
        assert isinstance(result, str)
        assert result == os.path.join(log_dir, 'output', 'diagnostics.p1log')

    def test_return_output_dir(self, tmpdir):
        log_base, log_dir = self._make_log(tmpdir)
        path, out_dir = locate_log(LOG_HASH[:8], log_base_dir=log_base, return_output_dir=True)
        assert path == os.path.join(log_dir, 'output', 'diagnostics.p1log')
        assert out_dir == log_dir

    def test_return_log_id(self, tmpdir):
        log_base, log_dir = self._make_log(tmpdir)
        path, log_id = locate_log(LOG_HASH[:8], log_base_dir=log_base, return_log_id=True)
        assert path == os.path.join(log_dir, 'output', 'diagnostics.p1log')
        assert log_id == LOG_HASH

    def test_return_both(self, tmpdir):
        log_base, log_dir = self._make_log(tmpdir)
        path, out_dir, log_id = locate_log(LOG_HASH[:8], log_base_dir=log_base,
                                           return_output_dir=True, return_log_id=True)
        assert path == os.path.join(log_dir, 'output', 'diagnostics.p1log')
        assert out_dir == log_dir
        assert log_id == LOG_HASH

    def test_error_file_only(self, tmpdir):
        assert locate_log('zzz000', log_base_dir=str(tmpdir)) is None

    def test_error_with_both(self, tmpdir):
        result = locate_log('zzz000', log_base_dir=str(tmpdir),
                            return_output_dir=True, return_log_id=True)
        assert result == (None, None, None)

    def test_return_log_id_from_directory(self, tmpdir):
        # log_id should be the log hash, not a subdirectory name like "output".
        log_dir = make_log_dir(tmpdir, LOG_HASH, ['output/diagnostics.p1log'])
        make_manifest(log_dir, 'output/diagnostics.p1log')
        _, log_id = locate_log(log_dir, log_base_dir=str(tmpdir), return_log_id=True)
        assert log_id == LOG_HASH

    def test_return_alt_log_id_from_directory(self, tmpdir):
        # log_id should be the log hash, not a subdirectory name like "output".
        log_dir = make_log_dir(tmpdir, LOG_HASH, ['output/diagnostics.p1log'])
        make_manifest(log_dir, 'output/diagnostics.p1log', guid='abcdef0123456789')
        _, log_id = locate_log(log_dir, log_base_dir=str(tmpdir), return_log_id=True)
        assert log_id == 'abcdef0123456789'

    def test_return_log_id_no_manifest(self, tmpdir):
        # If there is no manifest file, the fallback behavior is to return the parent directory name (even if that dir
        # happens to have its own parent dir whose name could be a valid log hash.
        log_dir = make_log_dir(tmpdir, LOG_HASH, ['output/diagnostics.p1log'])
        _, log_id = locate_log(log_dir, log_base_dir=str(tmpdir), return_log_id=True)
        assert log_id == 'output'
