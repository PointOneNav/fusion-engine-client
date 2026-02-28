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


def axis_rotation_dcm(angle, axis, deg=False):
    """!
    @brief Create a direction cosine matrix rotating a coordinate frame around the specified axis.

    The resulting DCM represents a passive transformation of a vector expressed in the original coordinate frame (@f$
    \alpha @f$) to one expressed in the rotated coordinate frame (@f$ \beta @f$).

    @param angle The desired rotation angle.
    @param axis The axis to be rotated around (@c 'x', @c 'y', or @c 'z').
    @param deg If @c True, interpret the input angles as degrees. Otherwise, interpret as radians.

    @return The 3x3 rotation matrix @f$ C_\alpha^\beta @f$.
    """
    if deg:
        angle = np.deg2rad(angle)

    cos = np.cos(angle)
    sin = np.sin(angle)

    if axis == 'x':
        return np.array(((1,    0,   0),
                         (0,  cos, sin),
                         (0, -sin, cos)))
    elif axis == 'y':
        return np.array(((cos,  0, -sin),
                         (  0,  1,    0),
                         (sin,  0,  cos)))
    elif axis == 'z':
        return np.array((( cos,  sin, 0),
                         (-sin,  cos, 0),
                         (   0,    0, 1)))
    else:
        raise RuntimeError('Invalid axis specification.')


def euler_angles_to_dcm(x, y=None, z=None, order='321', deg=False):
    """!
    @brief Convert an Euler (Tait-Bryan) angle attitude (in radians) into a direction cosine matrix.

    The input angles represent the rotation from coordinate frame @f$ \alpha @f$ to coordinate frame @f$ \beta @f$ (@f$
    C_\alpha^\beta @f$. This is frequently the rotation from the navigation frame (local level frame) to the body frame,
    @f$ C_n^b @f$.

    @note
    This DCM represents a passive transformation of a vector from one coordinate frame to another, as opposed to an
    active rotation of a vector within a single coordinate frame.

    This function supports any intrinsic rotation order through the @c order argument. The most common convention is a
    three-two-one rotation (@c '321'), in which the coordinate frame is first rotated around the Z-axis (i.e., the third
    axis) by the angle @c z, then the second axis in the resulting intermediate coordinate frame (the Y'-axis), and
    finally the third axis in the last intermediate coordinate frame (the X''-axis). 3-2-1 rotation angles are commonly
    referred to as yaw, pitch, and roll for the Z, Y, and X rotations respectively.

    You may specify all three angles separately using the @c x, @c y, and @c z parameters, or provide a Numpy array
    containing all three angles.

    @param x The angle to rotate around the X-axis (i.e., axis 1). May be a Numpy array containing the rotation angles
           for all three axes in the order X, Y, Z.
    @param y The angle to rotate around the Y-axis (i.e., axis 2).
    @param z The angle to rotate around the Z-axis (i.e., axis 3).
    @param order A string specifying the rotation order to be applied.
    @param deg If @c True, interpret the input angles as degrees. Otherwise, interpret as radians.

    @return The 3x3 rotation matrix rotating from the @f$ \alpha @f$ frame to the @f$ \beta @f$ frame (@f$
            C_\alpha^\beta @f$).
    """
    if isinstance(x, np.ndarray):
        if y is not None or z is not None:
            raise RuntimeError('Cannot specify Y/Z angles when using a Numpy array.')
        else:
            angles = x
    else:
        if y is None or z is None:
            raise RuntimeError('You must specify Y and Z angles.')
        else:
            angles = np.array((x, y, z))

    if deg:
        angles = np.deg2rad(angles)

    # 3-2-1 order written explicitly for efficiency since it's the most common order. Taken from Groves section 2.2.2.
    if order == '321':
        sin_phi, sin_theta, sin_psi = np.sin(angles)
        cos_phi, cos_theta, cos_psi = np.cos(angles)

        return np.array((
            (cos_theta * cos_psi, cos_theta * sin_psi, -sin_theta),
            (-cos_phi * sin_psi + sin_phi * sin_theta * cos_psi,
             cos_phi * cos_psi + sin_phi * sin_theta * sin_psi,
             sin_phi * cos_theta),
            (sin_phi * sin_psi + cos_phi * sin_theta * cos_psi,
             -sin_phi * cos_psi + cos_phi * sin_theta * sin_psi,
             cos_phi * cos_theta)
        ))
    else:
        dcm = {}
        dcm['1'] = axis_rotation_dcm(angles[0], axis='x')
        dcm['2'] = axis_rotation_dcm(angles[1], axis='y')
        dcm['3'] = axis_rotation_dcm(angles[2], axis='z')

        return dcm[order[2]].dot(dcm[order[1]]).dot(dcm[order[0]])


def dcm_to_euler_angles(dcm, order='321', deg=False):
    """!
    @brief Convert a direction cosine matrix into an Euler (Tait-Bryan) angle attitude representation.

    Convert a DCM representing the rotation from coordinate frame @f$ \alpha @f$ to coordinate frame @f$ \beta @f$ into
    corresponding Euler angles with the specified rotation order.

    @param dcm The 3x3 rotation matrix.
    @param order The desired Euler angle order.
    @param deg If @c True, return angles in degrees. Otherwise, return radians.

    @return A Numpy array containing the X, Y, and Z rotation angles.
    """
    if order == '321':
        x = np.arctan2(dcm[1, 2], dcm[2, 2])
        y = -np.arcsin(dcm[0, 2])
        z = np.arctan2(dcm[0, 1], dcm[0, 0])
    else:
        raise RuntimeError('Unsupported rotation order.')

    result = np.array((x, y, z))
    if deg:
        result = np.rad2deg(result)

    return result
