import numpy as np

def find_first(arr: np.ndarray):
    """!
    @brief Get the first index of input array which is `True`.

    @param arr A boolean array.

    @return First index of input array which is `True`. If all elements are `False`, returns -1.
    """
    if arr.dtype != bool:
        raise ValueError('Input array is not a boolean array.')

    idx = np.argmax(arr)
    if idx == 0 and arr[0] is not True:
        return -1
    else:
        return idx
