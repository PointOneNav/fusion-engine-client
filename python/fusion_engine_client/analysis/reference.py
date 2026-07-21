from typing import Optional, Union

import re

import numpy as np
from pymap3d import geodetic2ecef

from .data_loader import DataLoader, TimeAlignmentMode
from ..messages import PoseMessage, PoseAuxMessage, SolutionType
from ..utils import trace as logging
from ..utils.log import locate_log, DEFAULT_LOG_BASE_DIR

_logger = logging.getLogger('point_one.fusion_engine.analysis.reference')

_OWN_LOG_STATISTICS = ('first', 'first_fixed', 'median', 'median_fixed')


def _interp_columns(x: np.ndarray, y: Optional[np.ndarray], x_new: np.ndarray) -> Optional[np.ndarray]:
    """!
    @brief Linearly interpolate each row of `y` (sampled at `x`) onto `x_new`, returning NaN for any query point
           outside the range of `x` or where too few valid (non-NaN) samples exist to interpolate.
    """
    if y is None:
        return None

    out = np.full((y.shape[0], len(x_new)), np.nan)
    in_range = np.logical_and(x_new >= x[0], x_new <= x[-1])
    if not np.any(in_range):
        return out

    for row in range(y.shape[0]):
        valid = ~np.isnan(y[row, :])
        if np.count_nonzero(valid) < 2:
            continue
        out[row, in_range] = np.interp(x_new[in_range], x[valid], y[row, valid])

    return out


class ReferenceData:
    """!
    @brief Moving or stationary reference pose data.
    """

    def __init__(self, description: str, is_truth: bool,
                 position_ecef_m: np.ndarray,
                 gps_time_sec: Optional[np.ndarray] = None,
                 solution_type: Optional[np.ndarray] = None,
                 velocity_enu_mps: Optional[np.ndarray] = None,
                 ypr_deg: Optional[np.ndarray] = None):
        """!
        @brief Construct a reference data instance.

        @param description A human-readable description of where this data came from, suitable for display in plot
               titles (e.g., "Stationary Reference (37.123, -122.456, 12.3)", "Median Position",
               "Reference Log 'abc123'").
        @param is_truth If `True`, this data comes from an independent truth source (a stationary location, or a
               separate reference log). If `False`, this data is derived from the primary log's own data (e.g., its
               median or first position).
        @param position_ecef_m A 3-element (stationary) or 3xN (time-varying) ECEF position array, in meters.
        @param gps_time_sec GPS time of week/epoch (sec) for each time-varying sample, sorted in ascending order.
               `None` for a stationary reference.
        @param solution_type Solution type for each time-varying sample. `None` for a stationary reference.
        @param velocity_enu_mps Optional ENU velocity (3-element or 3xN), in m/s.
        @param ypr_deg Optional yaw/pitch/roll orientation (3-element or 3xN), in degrees.
        """
        self.description = description
        self.is_truth = is_truth
        self.position_ecef_m = np.asarray(position_ecef_m, dtype=float)
        self.gps_time_sec = None if gps_time_sec is None else np.asarray(gps_time_sec, dtype=float)
        self.solution_type = solution_type
        self.velocity_enu_mps = velocity_enu_mps
        self.ypr_deg = ypr_deg

        # Cache of the most recent interpolate_*() result for each field, keyed by the query time vector's start
        # time, end time, and sample count (not the full time vector) to avoid recomputing for repeated queries.
        self._interp_cache = {}

    @property
    def is_stationary(self) -> bool:
        return self.gps_time_sec is None

    @property
    def has_velocity(self) -> bool:
        return self.velocity_enu_mps is not None

    @property
    def has_orientation(self) -> bool:
        return self.ypr_deg is not None

    @property
    def displacement_label(self) -> str:
        """!
        @brief 'Error' if this is an independent truth source, or 'Displacement' if derived from the log's own data.
        """
        return 'Error' if self.is_truth else 'Displacement'

    def __repr__(self):
        extent = 'stationary' if self.is_stationary else f'{len(self.gps_time_sec)} samples'
        return f'ReferenceData({self.description!r}, is_truth={self.is_truth}, {extent})'

    def get_coverage_mask(self, gps_time_sec: np.ndarray, warn: bool = True) -> np.ndarray:
        """!
        @brief Determine which of the specified GPS timestamps fall within the time range covered by this reference.

        @param gps_time_sec The GPS timestamps (sec) to be checked.
        @param warn If `True` and this is a time-varying reference that does not fully cover `gps_time_sec`, log a
               warning indicating the percentage of the requested range that is covered.

        @return A boolean mask, the same length as `gps_time_sec`, `True` for entries within range.
        """
        if self.is_stationary:
            return np.full(len(gps_time_sec), True)

        in_range = np.logical_and(gps_time_sec >= self.gps_time_sec[0], gps_time_sec <= self.gps_time_sec[-1])
        if warn and not np.all(in_range):
            coverage_percent = 100.0 * np.count_nonzero(in_range) / len(in_range)
            _logger.warning(
                "Reference data '%s' only covers %.1f%% of the log's time range. Data outside the reference time "
                "range will be omitted." % (self.description, coverage_percent))
        return in_range

    def _interpolate_cached(self, key: str, y: np.ndarray, gps_time_sec: np.ndarray) -> np.ndarray:
        """!
        @brief Interpolate `y` onto `gps_time_sec`, caching the result to avoid recomputing for repeated queries.

        The cache is keyed on the query time vector's start time, end time, and sample count (not the full time
        vector), so a repeated call with an equivalent query (e.g., the same reference reused across multiple
        plots) is served from cache instead of re-interpolated.

        @param key A name identifying which field is being interpolated (e.g., 'position').
        @param y The data to be interpolated, sampled at `self.gps_time_sec`.
        @param gps_time_sec The GPS timestamps (sec) to interpolate onto.

        @return The interpolated data.
        """
        if len(gps_time_sec) > 0:
            signature = (gps_time_sec[0], gps_time_sec[-1], len(gps_time_sec))
            cached_signature, cached_result = self._interp_cache.get(key, (None, None))
            if signature == cached_signature:
                return cached_result
        else:
            signature = None

        result = _interp_columns(self.gps_time_sec, y, gps_time_sec)
        if signature is not None:
            self._interp_cache[key] = (signature, result)
        return result

    def interpolate_position_ecef_m(self, gps_time_sec: np.ndarray) -> np.ndarray:
        """!
        @brief Interpolate this reference's ECEF position (m) onto the specified GPS timestamps (sec).

        Entries outside the time range covered by this reference are set to NaN.
        """
        if self.is_stationary:
            return np.tile(self.position_ecef_m.reshape(3, 1), (1, len(gps_time_sec)))
        else:
            return self._interpolate_cached('position', self.position_ecef_m, gps_time_sec)

    def interpolate_velocity_enu_mps(self, gps_time_sec: np.ndarray) -> Optional[np.ndarray]:
        """!
        @brief Interpolate this reference's ENU velocity (m/s) onto the specified GPS timestamps (sec).

        Returns `None` if velocity is not available. Entries outside the covered time range are set to NaN.
        """
        if self.velocity_enu_mps is None:
            return None
        elif self.is_stationary:
            return np.tile(self.velocity_enu_mps.reshape(3, 1), (1, len(gps_time_sec)))
        else:
            return self._interpolate_cached('velocity', self.velocity_enu_mps, gps_time_sec)

    def interpolate_ypr_deg(self, gps_time_sec: np.ndarray) -> Optional[np.ndarray]:
        """!
        @brief Interpolate this reference's YPR orientation (deg) onto the specified GPS timestamps (sec).

        Returns `None` if orientation is not available. Entries outside the covered time range are set to NaN.
        """
        if self.ypr_deg is None:
            return None
        elif self.is_stationary:
            return np.tile(self.ypr_deg.reshape(3, 1), (1, len(gps_time_sec)))
        else:
            return self._interpolate_cached('ypr', self.ypr_deg, gps_time_sec)

    # -------------------------------------------------------------------------------------------------------------
    # Constructors
    # -------------------------------------------------------------------------------------------------------------

    @classmethod
    def from_stationary_lla(cls, lla_deg: np.ndarray) -> 'ReferenceData':
        """!
        @brief Create a stationary truth reference from an LLA position (deg, deg, m).
        """
        lla_deg = np.asarray(lla_deg, dtype=float)
        position_ecef_m = np.array(geodetic2ecef(*lla_deg, deg=True))
        description = 'Stationary Reference (%.8f, %.8f, %.2f)' % tuple(lla_deg)
        return cls(description=description, is_truth=True, position_ecef_m=position_ecef_m)

    @classmethod
    def from_stationary_ecef(cls, position_ecef_m: np.ndarray) -> 'ReferenceData':
        """!
        @brief Create a stationary truth reference from an ECEF position (m).
        """
        position_ecef_m = np.asarray(position_ecef_m, dtype=float)
        description = 'Stationary Reference (ECEF %.2f, %.2f, %.2f)' % tuple(position_ecef_m)
        return cls(description=description, is_truth=True, position_ecef_m=position_ecef_m)

    @classmethod
    def from_own_log(cls, loader: DataLoader, statistic: str, source_id: Optional[int] = None,
                     params: Optional[dict] = None) -> Optional['ReferenceData']:
        """!
        @brief Create a reference derived from the primary log's own pose data.

        This is *not* an independent truth source -- it is simply a statistic computed from the same data being
        analyzed, so comparisons against it should be labeled as "displacement", not "error".

        @param loader The @ref DataLoader for the log being analyzed.
        @param statistic One of 'first', 'first_fixed', 'median', or 'median_fixed'.
        @param source_id If specified, only consider data from this source ID.
        @param params Additional keyword arguments to forward to `loader.read()` (e.g., `time_range`).

        @return A @ref ReferenceData instance, or `None` if no suitable data was found.
        """
        if statistic not in _OWN_LOG_STATISTICS:
            raise ValueError(f"Unrecognized own-log reference statistic '{statistic}'.")

        params = dict(params or {})
        params.setdefault('return_numpy', True)
        params.setdefault('show_progress', True)
        source_ids = None if source_id is None else [source_id]
        result = loader.read(message_types=[PoseMessage, PoseAuxMessage], source_ids=source_ids,
                             time_align=TimeAlignmentMode.INSERT, **params)
        pose_data = result[PoseMessage.MESSAGE_TYPE]
        aux_data = result[PoseAuxMessage.MESSAGE_TYPE]

        valid_idx = np.logical_and(~np.isnan(pose_data.p1_time), pose_data.solution_type != SolutionType.Invalid)
        if not np.any(valid_idx):
            _logger.warning('No valid position solutions available in log. Cannot generate own-log reference.')
            return None

        if statistic == 'first':
            selected_idx = np.array([np.flatnonzero(valid_idx)[0]])
            description = 'First Position'
        elif statistic == 'first_fixed':
            fixed_idx = np.logical_and(valid_idx, pose_data.solution_type == SolutionType.RTKFixed)
            if np.any(fixed_idx):
                selected_idx = np.array([np.flatnonzero(fixed_idx)[0]])
                description = 'First Fixed Position'
            else:
                _logger.warning('No fixed positions available. Using first instead.')
                selected_idx = np.array([np.flatnonzero(valid_idx)[0]])
                description = 'First Position'
        elif statistic == 'median_fixed':
            fixed_idx = np.logical_and(valid_idx, pose_data.solution_type == SolutionType.RTKFixed)
            if np.any(fixed_idx):
                selected_idx = np.flatnonzero(fixed_idx)
                description = 'Median Fixed Position'
            else:
                _logger.warning('No fixed positions available. Using median of all valid positions instead.')
                selected_idx = np.flatnonzero(valid_idx)
                description = 'Median Position'
        elif statistic == 'median':
            selected_idx = np.flatnonzero(valid_idx)
            description = 'Median Position'
        else:
            raise ValueError(f"Unrecognized statistic type '{statistic}'.")

        lla_deg = pose_data.lla_deg[:, selected_idx]
        position_ecef_m = np.array(geodetic2ecef(lat=lla_deg[0, :], lon=lla_deg[1, :], alt=lla_deg[2, :], deg=True))
        velocity_enu_mps = aux_data.velocity_enu_mps[:, selected_idx]
        ypr_deg = pose_data.ypr_deg[:, selected_idx]

        if statistic in ('first', 'first_fixed'):
            position_ecef_m = position_ecef_m[:, 0]
            velocity_enu_mps = None if np.any(np.isnan(velocity_enu_mps[:, 0])) else velocity_enu_mps[:, 0]
            ypr_deg = None if np.any(np.isnan(ypr_deg[:, 0])) else ypr_deg[:, 0]
        else:
            position_ecef_m = np.median(position_ecef_m, axis=1)
            with np.errstate(invalid='ignore'):
                velocity_enu_mps = (None if np.all(np.isnan(velocity_enu_mps))
                                    else np.nanmedian(velocity_enu_mps, axis=1))
                ypr_deg = None if np.all(np.isnan(ypr_deg)) else np.nanmedian(ypr_deg, axis=1)

        return cls(description=description, is_truth=False, position_ecef_m=position_ecef_m,
                   velocity_enu_mps=velocity_enu_mps, ypr_deg=ypr_deg)

    @classmethod
    def from_reference_log(cls, path_or_loader: Union[str, DataLoader], log_base_dir: str = None,
                           log_type: str = 'auto', source_id: Optional[int] = None,
                           params: Optional[dict] = None) -> Optional['ReferenceData']:
        """!
        @brief Load time-varying truth reference data (position, velocity, orientation) from a separate log.

        @param path_or_loader A @ref DataLoader instance, or a path/log pattern/hash identifying the reference log.
        @param log_base_dir The base directory to search when resolving a log hash/pattern. Defaults to
               @ref DEFAULT_LOG_BASE_DIR.
        @param log_type The type of log data to load (see the `--log-type` help text).
        @param source_id If specified, only consider data from this source ID within the reference log.
        @param params Additional keyword arguments to forward to `loader.read()` (e.g., `time_range`).

        @return A @ref ReferenceData instance, or `None` if the log could not be loaded, or contained no valid pose
                data.
        """
        if isinstance(path_or_loader, DataLoader):
            loader = path_or_loader
            description = "Reference Log '%s'" % loader.get_input_path()
        else:
            if log_base_dir is None:
                log_base_dir = DEFAULT_LOG_BASE_DIR

            input_path, log_id = locate_log(input_path=path_or_loader, log_base_dir=log_base_dir,
                                            return_output_dir=False, return_log_id=True, log_type=log_type)
            if input_path is None:
                # locate_log() will log an error.
                return None

            loader = DataLoader(input_path)
            description = "Reference Log %s" % (log_id if log_id is not None else input_path)

        params = dict(params or {})
        params.setdefault('return_numpy', True)
        params.setdefault('show_progress', True)
        source_ids = None if source_id is None else [source_id]
        result = loader.read(message_types=[PoseMessage, PoseAuxMessage], source_ids=source_ids,
                             time_align=TimeAlignmentMode.INSERT, **params)
        pose_data = result[PoseMessage.MESSAGE_TYPE]
        aux_data = result[PoseAuxMessage.MESSAGE_TYPE]

        valid_idx = np.logical_and(~np.isnan(pose_data.p1_time), pose_data.solution_type != SolutionType.Invalid)
        if not np.any(valid_idx):
            _logger.warning("No valid position solutions available in reference log '%s'." % description)
            return None

        # Sort by GPS time since it is the only time base comparable across two independently recorded logs (P1 time
        # is monotonic but device- and boot-specific, and is not meaningful when comparing two different logs).
        gps_time_sec = pose_data.gps_time[valid_idx]
        order = np.argsort(gps_time_sec)

        gps_time_sec = gps_time_sec[order]
        solution_type = pose_data.solution_type[valid_idx][order]
        lla_deg = pose_data.lla_deg[:, valid_idx][:, order]
        position_ecef_m = np.array(geodetic2ecef(lat=lla_deg[0, :], lon=lla_deg[1, :], alt=lla_deg[2, :], deg=True))
        velocity_enu_mps = aux_data.velocity_enu_mps[:, valid_idx][:, order]
        ypr_deg = pose_data.ypr_deg[:, valid_idx][:, order]

        return cls(description=description, is_truth=True, position_ecef_m=position_ecef_m,
                   gps_time_sec=gps_time_sec, solution_type=solution_type, velocity_enu_mps=velocity_enu_mps,
                   ypr_deg=ypr_deg)

    # -------------------------------------------------------------------------------------------------------------
    # CLI argument parsing
    # -------------------------------------------------------------------------------------------------------------

    # An optional "lla:"/"ecef:" prefix followed by 3 comma-separated values (decimal point optional on each value,
    # e.g., "37, -122, 10", "lla: 37.1234, -122.5, 10.2", or "ecef: -2707071.0, -4321671.7, 3817403.2"). If the
    # prefix is omitted, the coordinate type is inferred from the magnitude of the values (see
    # `_ECEF_MAGNITUDE_THRESHOLD_M`).
    _COORD_REGEX = re.compile(
        r'^(?:(lla|ecef)\s*:\s*)?(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)$', re.IGNORECASE)

    # ECEF coordinates are always within a few hundred km of Earth's radius (~6.37e6 m) in magnitude, regardless of
    # location, while LLA values (even treated naively as a raw 3-vector of degrees/degrees/meters) never approach
    # that magnitude. This threshold sits comfortably between the two.
    _ECEF_MAGNITUDE_THRESHOLD_M = 1.0e5

    @classmethod
    def _is_ecef_magnitude(cls, values: np.ndarray) -> bool:
        return np.linalg.norm(values) > cls._ECEF_MAGNITUDE_THRESHOLD_M

    @classmethod
    def resolve_cli_argument(cls, reference: Optional[str],
                             loader: Optional[DataLoader] = None,
                             log_base_dir: str = None, log_type: str = 'auto',
                             source_id: Optional[int] = None) -> Optional['ReferenceData']:
        """!
        @brief Parse and resolve the `--reference` command-line argument into a @ref ReferenceData instance.

        Supported formats:
        - The path to a separate log file, or a log hash/pattern to be located under `log_base_dir`, whose pose data
          will be used as a time-varying truth reference
        - A stationary position, as 3 comma-separated values. LLA (degrees, degrees, meters) vs. ECEF (meters) is
          inferred automatically from the magnitude of the values, or may be specified explicitly with an `lla:` or
          `ecef:` prefix:
          - LLA: `37.1234, -122.526335, 102.34`
          - LLA: `lla: 37.1234, -122.526335, 102.34`
          - ECEF: `-2707071.0, -4321671.7, 3817403.2`
          - ECEF: `ecef: -2707071.0, -4321671.7, 3817403.2`
        - A statistic computed from the log's own data:
          - `first` - Use the first-available pose solution
          - `first_fixed` - Use the first RTK-fixed pose solution
          - `median` - Use the median pose solution across the entire log
          - `median_fixed` - Use the median pose solution only when RTK-fixed

        @param reference The `--reference` argument string, or `None`.
        @param loader The @ref DataLoader for the primary log being analyzed. Used to resolve the `first`, `median`,
               etc. statistics.
        @param log_base_dir The base directory to search if `reference` specifies a log hash/pattern.
        @param log_type The type of log data to load if `reference` specifies a separate log file.
        @param source_id If specified, restrict reference data to this source ID.

        @return A @ref ReferenceData instance, or `None` if `reference` is `None`, or could not be resolved.
        """
        if reference is None:
            return None

        m = cls._COORD_REGEX.match(reference)
        if m:
            prefix = m.group(1)
            values = np.array([float(m.group(i)) for i in (2, 3, 4)])
            is_ecef = cls._is_ecef_magnitude(values) if prefix is None else prefix.lower() == 'ecef'
            return cls.from_stationary_ecef(values) if is_ecef else cls.from_stationary_lla(values)

        reference_stat = reference.lower().replace('-', '_')
        if reference_stat in _OWN_LOG_STATISTICS:
            if loader is None:
                raise ValueError(f'Data log not available. Cannot compute {reference_stat} statistic.')
            return cls.from_own_log(loader, statistic=reference_stat, source_id=source_id)

        return cls.from_reference_log(reference, log_base_dir=log_base_dir, log_type=log_type, source_id=source_id)
