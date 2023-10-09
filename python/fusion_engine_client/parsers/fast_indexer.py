import os
import math
from multiprocessing import Pool, cpu_count
from typing import List, Tuple
import struct

import numpy as np

from ..messages import MessageHeader, Timestamp, message_type_to_class
from ..utils import trace as logging
from .file_index import FileIndex

# NOTE: This needs to be larger then the biggest possible FE message. The
# smaller it is, the faster the indexer can run, but if it's not large enough,
# messages may be missed.
_MAX_FE_MSG_SIZE_BYTES = 1024 * 12

# This has been tuned on my laptop to where increasing the read size was giving
# diminishing returns on speed.
_READ_SIZE_BYTES = 80 * 1024

_PREAMBLE = struct.unpack('<H', MessageHeader.SYNC)

_logger = logging.getLogger('point_one.fusion_engine.parsers.fast_indexer')


def _search_blocks_for_fe(input_path: str, block_starts: List[int]):
    """!
    @brief Search the specified portions of the file for the start offsets of valid FE messages.

    @param input_path The path to the file to be read.
    @param block_starts The blocks of data to search for FE messages in.

    @return The raw index data corresponding to this thread's data blocks.
    """
    header = MessageHeader()
    message_end = 0
    num_syncs = 0
    # Data corresponding to raw values in FileIndex._RAW_DTYPE.
    raw_list: List[Tuple[int, int, int]] = []
    with open(input_path, 'rb') as fd:
        for i in range(len(block_starts)):
            block_offset = block_starts[i]
            fd.seek(block_offset)
            # The `_READ_SIZE_BYTES` will be the data searched for the start of
            # messages. The additional data is read to give room to complete the
            # last message.
            data = fd.read(_READ_SIZE_BYTES + _MAX_FE_MSG_SIZE_BYTES)
            if len(data) == _READ_SIZE_BYTES + _MAX_FE_MSG_SIZE_BYTES:
                word_count = int(_READ_SIZE_BYTES / 2)
            # The last read on the last thread will run out of data, so read
            # whatever is left.
            else:
                word_count = int(len(data) / 2) - 1

            # This is a fairly optimized search for preamble matches.
            # Allocate space for all the message offsets to check.
            np_data = np.empty(word_count * 2, dtype=np.uint16)
            # Load the potential sync words for the even offsets.
            np_data[0::2] = np.frombuffer(data, dtype=np.uint16, count=word_count)
            # Load the potential sync words for the odd offsets ([AA 31 2E AA] shifted over one byte).
            np_data[1::2] = np.frombuffer(data[1:], dtype=np.uint16, count=word_count)
            # This is lot faster then doing this check in raw Python due to numpy optimizations.
            sync_matches = np.where(np_data == _PREAMBLE)[0]

            num_syncs += len(sync_matches)

            # To do the CRC check and find a p1_time the full message needs to be parsed. This
            # section is not particularly optimized. The chance of the preamble appearing in data
            # is relatively low, so this code is in a much less hot path then the preamble sync above.
            for i in sync_matches:
                absolute_offset = i + block_offset
                # Don't check preambles found inside other valid messages. Generally, this didn't
                # provide much speed up, but could prevent wasting cycles if the message size is large.
                if absolute_offset < message_end:
                    continue

                try:
                    # Check if the message has a valid length and CRC. This could probably be optimized.
                    header.unpack(buffer=data, offset=i, validate_crc=True, warn_on_unrecognized=False)
                    # Populate the p1_time from the payload if it exists.
                    p1_time = Timestamp()
                    # About half the indexing time is spent doing this p1_time check. This would
                    # probably take some doing to optimize. One approach to speed up the validation
                    # and p1 time checks is to read the message as a uint32_t and having a map to
                    # the p1_time (if present) for each class.
                    cls = message_type_to_class.get(header.message_type, None)
                    if cls is not None:
                        try:
                            payload = cls()
                            if hasattr(payload, 'p1_time') or hasattr(payload, 'details'):
                                payload.unpack(buffer=data, offset=i +
                                               MessageHeader.calcsize(), message_version=header.message_version)
                                p1_time = payload.get_p1_time()
                        except BaseException:
                            pass
                    # Convert the Timestamp to an integer.
                    p1_time_raw = Timestamp._INVALID if math.isnan(p1_time.seconds) else int(p1_time.seconds)
                    message_end = absolute_offset + header.get_message_size()
                    raw_list.append((p1_time_raw, int(header.message_type), absolute_offset))
                except BaseException:
                    pass
    _logger.trace(f'{num_syncs} sync with {len(raw_list)} valid FE.')
    # Return the index data for this section of the file.
    return np.array(raw_list, dtype=FileIndex._RAW_DTYPE)


def fast_generate_index(
        input_path: str,
        force_reindex=False,
        save_index=True,
        max_bytes=None,
        num_threads=cpu_count()) -> FileIndex:
    """!
    @brief Quickly build a FileIndex.

    This basic logic would be relatively easy to extend to do general parallel processing on messages.

    @param input_path The path to the file to be read.
    @param force_reindex If `True` regenerate the index even if there's an existing file.
    @param save_index If `True` save the index to disk after generation.
    @param max_bytes If specified, read up to the maximum number of bytes.
    @param num_threads The number of parallel processes to spawn for searching the file.

    @return The loaded or generated @ref FileIndex.
    """
    file_size = os.stat(input_path).st_size
    _logger.debug(f'File size: {int(file_size/1024/1024)}MB')

    if max_bytes and max_bytes < file_size:
        _logger.debug(f'Only indexing: {max_bytes/1024/1024}MB')
        file_size = max_bytes
        if save_index:
            save_index = False
            _logger.info('Max bytes specified. Disabling saving index.')

    index_path = FileIndex.get_path(input_path)
    # Check if index file can be loaded.
    if not force_reindex and os.path.exists(index_path):
        try:
            index = FileIndex(index_path, input_path)
            _logger.info(f'Loading existing cache: "{index_path}".')
            return index
        except ValueError as e:
            _logger.warning(f'Couldn\'t load cache "{index_path}": {str(e)}.')

    _logger.info(f'Indexing file "{input_path}". This may take a few seconds.')
    _logger.debug(f'Using Threads: {num_threads}')

    # These are the args passed to the _search_blocks_for_fe instances.
    args: list[Tuple[str, List[int]]] = []
    # Allocate which blocks of bytes will be processed by each thread.
    num_blocks = math.ceil(file_size / _READ_SIZE_BYTES)
    # Each thread will process at least blocks_per_thread blocks. If the number
    # doesn't divide evenly, distribute the remainder.
    blocks_per_thread, blocks_remainder = divmod(num_blocks, num_threads)
    byte_offset = 0
    for i in range(num_threads):
        blocks = blocks_per_thread
        if i < blocks_remainder:
            blocks += 1
        args.append((input_path, list(range(byte_offset, byte_offset + blocks * _READ_SIZE_BYTES, _READ_SIZE_BYTES))))
        byte_offset += blocks * _READ_SIZE_BYTES

    _logger.debug(f'Reads/thread: {blocks_per_thread}')

    # Create a threadpool.
    with Pool(num_threads) as p:
        # Kick off the threads to process with their args. Then concatenate their returned data.
        index_raw = np.concatenate([o for o in p.starmap(_search_blocks_for_fe, args)])

    total_entries = len(index_raw)

    _logger.debug(f'FE messages found: {total_entries}')

    # This does an unnecessary conversion back and forth from the _RAW_DTYPE to
    # the _DTYPE and back again when saving. This is to avoid needing to deal
    # with the EOF entry directly. This adds less than a second, and could be
    # avoided by reproducing the FileIndex EOF entry logic.
    index = FileIndex(data=FileIndex._from_raw(index_raw))
    if save_index:
        _logger.info(f'Saving index to "{index_path}".')
        index.save(index_path, input_path)
    return index
