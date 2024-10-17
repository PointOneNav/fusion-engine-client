#!/usr/bin/env python3

import glob
import io
import sys
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

import boto3

if __package__ is None or __package__ == "":
    from import_utils import enable_relative_imports
    __package__ = enable_relative_imports(__name__, __file__)

from ..analysis.pose_compare import main as pose_compare_main
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
    resp = {}

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

    key_split = options.key_for_log_in_drive.split('/')

    if len(key_split) < 3:
        _logger.error(
            f'Key had unexpected prefix. Expecting S3 key like "2024-04-04/p1-lexus-rack-2/a0a0ff472ea342809d05380d8fe54399".')
        exit(1)
    elif len(key_split) > 3:
        options.key_for_log_in_drive = '/'.join(key_split[:3])
        _logger.warning(
            f'Key had unexpected prefix. Expecting S3 key like "2024-04-04/p1-lexus-rack-2/a0a0ff472ea342809d05380d8fe54399". Only using "{options.key_for_log_in_drive}".')

    prefix = options.key_for_log_in_drive.split('/')[0]

    os.makedirs(LOG_DIR, exist_ok=True)

    try:
        meta_key = options.key_for_log_in_drive + '/' + META_FILE
        drive_meta_data = download_to_memory(options.key_for_log_in_drive + '/' + META_FILE)
    except:
        _logger.error(
            f'Could not find "S3://{S3_DEFAULT_INGEST_BUCKET}/{meta_key}". Make sure this log was taken as part of a drive test collection.')
        exit(1)

    drive_meta = json.loads(drive_meta_data.decode('utf-8'))

    logs_to_download = []
    if options.reference is None:
        reference_guid = drive_meta['drive_reference_log']
        _logger.info(f'Using reference log: {reference_guid}')
        logs_to_download = [reference_guid]
    else:
        reference_guid = None
        reference_path = options.reference
        _logger.info('Attempting to use external data as reference.')
        if not os.path.exists(reference_path):
            _logger.error(f"Could't find reference data: {reference_path}.")
            exit(1)

    test_guids = drive_meta['drive_logs']

    log_paths = {}
    for guid in test_guids:
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

    if options.reference is None:
        reference = log_paths[reference_guid]
        reference_device = get_device_name_from_path(reference)
    else:
        reference = reference_path
        reference_device = os.path.basename(reference_path)

    for guid in test_guids:
        _logger.info(f'Comparing log: {log_paths[guid]}')
        test_device = get_device_name_from_path(log_paths[guid])
        sys.argv = ['pose_compare_main', str(log_paths[guid]),  str(
            reference), '--time-axis=rel', f'--test-device-name={test_device}', f'--reference-device-name={reference_device}']
        try:
            pose_compare_main()
        except Exception as e:
            _logger.error(f'Failure: {e}')
        input("Press Enter To Process Next Log")


if __name__ == '__main__':
    main()
