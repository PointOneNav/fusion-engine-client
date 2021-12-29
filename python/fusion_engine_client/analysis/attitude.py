import numpy as np


def get_ned_rotation_matrix(latitude, longitude, deg=False):
    """!
    @brief Get the rotation matrix resolving from ECEF to the local NED frame.

    @param latitude The local latitude (in rad).
    @param longitude The local longitude (in rad).
    @param deg If @c True, interpret @c latitude and @c longitude in degrees instead of radians.

    @return A 3x3 rotation matrix as an @c np.array.
    """
    if deg:
        latitude = np.deg2rad(latitude)
        longitude = np.deg2rad(longitude)

    cos_lat = np.cos(latitude)
    sin_lat = np.sin(latitude)
    cos_lon = np.cos(longitude)
    sin_lon = np.sin(longitude)

    result = np.zeros([3, 3])
    result[0, 0] = -sin_lat * cos_lon
    result[0, 1] = -sin_lat * sin_lon
    result[0, 2] = cos_lat

    result[1, 0] = -sin_lon
    result[1, 1] = cos_lon

    result[2, 0] = -cos_lat * cos_lon
    result[2, 1] = -cos_lat * sin_lon
    result[2, 2] = -sin_lat

    return result


def get_enu_rotation_matrix(latitude, longitude, deg=False):
    """!
    @brief Get the rotation matrix resolving from ECEF to the local ENU frame.

    @param latitude The local latitude (in rad).
    @param longitude The local longitude (in rad).
    @param deg If @c True, interpret @c latitude and @c longitude in degrees instead of radians.

    @return A 3x3 rotation matrix as an @c np.array.
    """
    C_ned_e = get_ned_rotation_matrix(latitude=latitude, longitude=longitude, deg=deg)
    C_enu_e = C_ned_e[(1, 0, 2), :]
    C_enu_e[2, :] = -C_enu_e[2, :]
    return C_enu_e
