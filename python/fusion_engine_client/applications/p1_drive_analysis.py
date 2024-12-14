#!/usr/bin/env python3

from dataclasses import dataclass, field
from enum import Enum, auto
import glob
import io
import sys
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import boto3
import numpy as np

if __package__ is None or __package__ == "":
    from import_utils import enable_relative_imports
    __package__ = enable_relative_imports(__name__, __file__)

from ..analysis.pose_compare import main as pose_compare_main
from ..analysis.pose_compare import PoseCompare
from ..messages import SolutionType
from ..utils import trace as logging
from ..utils.argument_parser import ArgumentParser

S3_DEFAULT_INGEST_BUCKET = 'pointone-ingest-landingpad'
S3_DEFAULT_REGION = 'us-west-1'
META_FILE = "drive_test_metadata.json"
LOG_DIR = Path('/logs/drive_analysis')
MANIFEST_FILE = 'maniphest.json'
TEST_LOG_FILE = 'output/diagnostics.p1log'
REFERENCE_LOG_FILE = 'fusion_engine.p1log'


_logger = logging.getLogger('point_one.fusion_engine.applications.drive_analysis')

s3_client = boto3.client('s3', region_name=S3_DEFAULT_REGION)


def download_to_memory(s3_key) -> bytes:
    file_stream = io.BytesIO()
    s3_client.download_fileobj(S3_DEFAULT_INGEST_BUCKET, s3_key, file_stream)
    file_stream.seek(0)
    return file_stream.read()


def find_logs(prefix, log_guids) -> Dict[str, str]:
    PREFIX_DATE_FORMAT = '%Y-%m-%d'
    resp: Dict[str, str] = {}

    prefix_date = datetime.strptime(prefix, PREFIX_DATE_FORMAT)
    day_before = prefix_date - timedelta(days=1)
    day_after = prefix_date + timedelta(days=1)
    prefixes = [prefix, day_before.strftime(PREFIX_DATE_FORMAT), day_after.strftime(PREFIX_DATE_FORMAT)]

    for prefix in prefixes:
        if len(log_guids) == len(resp):
            break
        _logger.debug(f"Searching {S3_DEFAULT_INGEST_BUCKET}/{prefix} for logs.")
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=S3_DEFAULT_INGEST_BUCKET, Prefix=prefix)
        for page in pages:
            for content in page['Contents']:
                for uuid in log_guids:
                    if uuid in content['Key']:
                        offset = content['Key'].index(uuid)
                        resp[uuid] = content['Key'][:offset] + uuid
                        break
    return resp


def get_device_name_from_path(log_path: Path) -> str:
    return '_'.join(log_path.name.split('_')[1:-1])


class StatType(Enum):
    MEAN = auto()
    MAX = auto()


@dataclass(frozen=True)
class Metric:
    type: StatType
    limit: float


@dataclass(frozen=True)
class PassFailSettings:
    error_3d_metrics: Dict[SolutionType, List[Metric]]
    percent_fixed_when_reference_fixed: float
    percent_float_or_better_when_reference_float: float
    skip_gps_times: List[Tuple[float, float]] = field(default_factory=list)


def load_pass_fail_settings(setting_path: Path) -> PassFailSettings:
    json_data = json.load(open(setting_path))
    if 'skip_gps_times' in json_data:
        skip_gps_times = [tuple(t) for t in json_data['skip_gps_times']]
    else:
        skip_gps_times = []
    error_3d_metrics = {}
    for type, metrics in json_data['error_3d_metrics'].items():
        error_3d_metrics[SolutionType[type]] = [
            Metric(type=StatType[v['type']], limit=v['limit']) for v in metrics
        ]

    return PassFailSettings(
        error_3d_metrics,
        percent_fixed_when_reference_fixed=json_data['percent_fixed_when_reference_fixed'],
        percent_float_or_better_when_reference_float=json_data['percent_float_or_better_when_reference_float'],
        skip_gps_times=skip_gps_times
    )


def pass_fail_check(analysis: PoseCompare, settings: PassFailSettings) -> bool:
    def find_fail_times(gps_times):
        MAX_GAP = 5.0
        if len(gps_times) == 0:
            return []

        start = float(gps_times[0])
        stop = float(gps_times[0])

        failures = []
        for gps_time in gps_times[1:]:
            if gps_time - stop < MAX_GAP:
                stop = float(gps_time)
            else:
                failures.append((start, stop))
                start = float(gps_time)
                stop = float(gps_time)

        failures.append((start, stop))
        return failures

    if analysis.missing_test_gps_epochs > 0:
        _logger.warning(f'{analysis.missing_test_gps_epochs} missing epochs in test data.')
        return False

    gps_times = analysis.error_gps_times
    filtered_time_idx = np.full((len(analysis.error_gps_times)), True)
    for start, stop in settings.skip_gps_times:
        filtered_time_idx[(gps_times >= start) & (gps_times <= stop)] = False

    SOLUTION_RATE_MAP = {
        'percent_fixed_when_reference_fixed': 'RTK Fixed',
        'percent_float_or_better_when_reference_float': 'RTK Float'
    }

    for k1, k2 in SOLUTION_RATE_MAP.items():
        if getattr(settings, k1) > analysis.percent_solution_type_reference_or_better[k2]:
            _logger.warning(f'{k1} check failed {getattr(settings, k1)} > {
                            analysis.percent_solution_type_reference_or_better[k2]}')
            return False

    tests_failed = False
    for solution_type, metrics in settings.error_3d_metrics.items():
        valid_idx = np.logical_and(analysis.error_solution_types == solution_type, filtered_time_idx)
        for metric in metrics:
            if metric.type == StatType.MAX:
                fail_max_idx = analysis.error_3d_m[valid_idx] > metric.limit
                failures = find_fail_times((gps_times[valid_idx])[fail_max_idx])
                for failure in failures:
                    _logger.warning(f'failure {failure[0]} - {failure[1]} ({failure[1] -
                                    failure[0]:.1f}s) for {metric} 3D {solution_type.name} error (m).')
                    tests_failed = True
            elif metric.type == StatType.MEAN:
                mean_error = np.mean(analysis.error_3d_m[valid_idx])
                if mean_error > metric.limit:
                    _logger.warning(f'3D {solution_type.name} error(m) failure {metric}. {mean_error} > {metric.limit}')
                    tests_failed = True

    return not tests_failed


def main():
    parser = ArgumentParser(description="""\
Run p1_pose_compare for each device included in a drive test.
This tool downloads the relevant files from S3 and prompts stdin before moving on to the next log.""")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Print verbose/trace debugging messages.")

    parser.add_argument(
        'key_for_log_in_drive',
        help="The full S3 key for one of the logs in the drive.\n"
             "Ex. '2024-04-04/p1-lexus-rack-2/a0a0ff472ea342809d05380d8fe54399'")

    parser.add_argument(
        '--reference', help="Specify reference path.")

    parser.add_argument(
        '--pass-fail-json', type=Path, help="JSON file with pass/fail test metrics.")

    parser.add_argument(
        '--skip-plots', action='store_true', help="Don't generate plots for each device.")

    options = parser.parse_args()

    # Configure logging.
    if options.verbose >= 1:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s:%(lineno)d - %(message)s',
                            stream=sys.stdout)
        _logger.setLevel(logging.DEBUG)
        if options.verbose == 1:
            logging.getLogger('point_one.fusion_engine.analysis.pose_compare').setLevel(logging.DEBUG)
        else:
            logging.getLogger('point_one.fusion_engine.analysis.pose_compare').setLevel(
                logging.getTraceLevel(depth=options.verbose - 1))
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s', stream=sys.stdout)

    pass_fail_settings = None if options.pass_fail_json is None else load_pass_fail_settings(options.pass_fail_json)

    key_split = options.key_for_log_in_drive.split('/')

    if len(key_split) < 3:
        _logger.error(
            f'Key had unexpected prefix. Expecting S3 key like "2024-04-04/p1-lexus-rack-2/a0a0ff472ea342809d05380d8fe54399".')
        exit(1)
    elif len(key_split) > 3:
        options.key_for_log_in_drive = '/'.join(key_split[:3])
        _logger.warning(
            f'Key had unexpected prefix. Expecting S3 key like "2024-04-04/p1-lexus-rack-2/a0a0ff472ea342809d05380d8fe54399". Only using "{options.key_for_log_in_drive}".')

    input_guid = options.key_for_log_in_drive.split('/')[-1]
    prefix = options.key_for_log_in_drive.split('/')[0]

    os.makedirs(LOG_DIR, exist_ok=True)

    try:
        meta_key = options.key_for_log_in_drive + '/' + META_FILE
        drive_meta_data = download_to_memory(meta_key)
    except:
        _logger.error(
            f'Could not find "S3://{S3_DEFAULT_INGEST_BUCKET}/{meta_key}". Make sure this log was taken as part of a drive test collection.')
        exit(1)

    drive_meta = json.loads(drive_meta_data.decode('utf-8'))

    reference_guid = None
    novatel_csv_path = None
    if options.reference is not None:
        _logger.info('Attempting to use external data as reference.')
        reference_path = options.reference
        if not os.path.exists(reference_path):
            _logger.error(f"Could't find reference data: {reference_path}.")
            exit(1)
    else:
        reference_guid = drive_meta.get('drive_reference_log', None)
        has_novatel = drive_meta.get('has_novatel_reference', False)
        if has_novatel:
            _logger.info(f'Using Novatel reference log.')
            novatel_key = options.key_for_log_in_drive + '/data/novatel.csv'
            novatel_csv_path = LOG_DIR / f'{input_guid}_novatel.csv'
            if not novatel_csv_path.exists():
                _logger.info(f'Downloading: {novatel_key}')
                s3_client.download_file(S3_DEFAULT_INGEST_BUCKET, novatel_key, novatel_csv_path)
        elif reference_guid is not None:
            _logger.info(f'Using reference log: {reference_guid}')
        else:
            _logger.error('No reference found in configuration file and no reference path provided.')
            exit(1)

    test_guids = drive_meta['drive_logs']

    logs_to_download = []
    log_paths = {}
    for guid in [reference_guid] + test_guids:
        # If a reference path was provided, do not attempt to use cached reference log.
        if guid is None:
            continue

        matches = glob.glob(str(LOG_DIR / f'*{guid}.p1log'))
        if len(matches) > 0:
            log_paths[guid] = Path(matches[0])
            _logger.info(f'Using cached: {log_paths[guid]}')
        else:
            logs_to_download.append(guid)

    if len(logs_to_download) > 0:
        log_prefixes = find_logs(prefix, logs_to_download)
        for guid in logs_to_download:
            if guid not in log_prefixes:
                if reference_guid == guid:
                    _logger.error(
                        f"Could't find test log: {guid}. Continuing without it.")
                    test_guids.remove(guid)
                else:
                    _logger.error(f"Could't find reference log: {guid}.")
                    exit(1)

        for guid, s3_prefix in log_prefixes.items():
            file_name = s3_prefix.replace('/', '_') + '.p1log'
            log_paths[guid] = LOG_DIR / file_name
            _logger.info(f'Downloading: {log_paths[guid]}')
            if reference_guid == guid:
                reference_p1log_key = s3_prefix + '/' + REFERENCE_LOG_FILE
            else:
                reference_p1log_key = s3_prefix + '/' + TEST_LOG_FILE

            s3_client.download_file(S3_DEFAULT_INGEST_BUCKET, reference_p1log_key, log_paths[guid])

    if options.reference is not None:
        reference = reference_path
        reference_device = os.path.basename(reference_path)
        reference_filter = 'std_dev'
    elif novatel_csv_path is not None:
        reference = novatel_csv_path
        reference_device = 'novatel.csv'
        reference_filter = 'std_dev'
    else:
        reference = log_paths[reference_guid]
        reference_device = get_device_name_from_path(reference)
        reference_filter = 'type'

    for guid in test_guids:
        _logger.info(f'Comparing log: {log_paths[guid]}')
        test_device = get_device_name_from_path(log_paths[guid])
        sys.argv = ['pose_compare_main', str(log_paths[guid]),  str(reference),
                    '--time-axis=rel', f'--test-device-name={test_device}',
                    f'--reference-device-name={reference_device}']
        if options.skip_plots:
            sys.argv.append('--skip-plots')

        try:
            analysis = pose_compare_main()
            if pass_fail_settings is not None:
                if not pass_fail_check(analysis, settings=pass_fail_settings):
                    sys.exit(1)
                else:
                    _logger.info('Tests passed for ' + guid)
        except Exception as e:
            _logger.error(f'Failure: {e}')
            sys.exit(1)
        if not options.skip_plots:
            input("Press Enter To Process Next Log")


if __name__ == '__main__':
    main()
