import os


def find_log(input_path, return_output_dir=False, return_log_id=False):
    """!
    @brief Locate a FusionEngine `*.p1bin` file.

    If `input_path` is a file, the returned output directory will be the parent directory of that file. If it is an
    Atlas log, the returned output directory will be the log directory.

    @param input_path The path to a `.p1bin` file, or to an Atlas log directory containing FusionEngine output.
    @param return_output_dir If `True`, return the output directory associated with the located input file.
    @param return_log_id If `True`, return the ID of the log if the requested path is an Atlas log.

    @return - The path to the located file.
            - The path to the located output directory. Only provided if `return_output_dir` is `True`.
            - The log ID string, or `None` if the requested file is not part of an Atlas log.
    """
    # Check if the input path is a file. If so, return it and set the output directory to its parent directory.
    if os.path.isfile(input_path):
        output_dir = os.path.dirname(input_path)
        log_id = None
    # If the input path is a directory, see if it's an Atlas log. If so, set the output directory to the log directory
    # (not the subdirectory containing the p1bin file).
    elif os.path.isdir(input_path):
        # A valid Atlas logs will contain a manifest file (note: the filename spelling below is intentional).
        log_dir = input_path
        if not os.path.exists(os.path.join(log_dir, 'maniphest.json')):
            raise FileNotFoundError('Specified directory is not a valid Atlas log.')
        else:
            log_id = os.path.basename(log_dir)

            # Check for a FusionEngine output file.
            fe_service_dir = os.path.join(log_dir, 'filter', 'output', 'fe_service')
            input_path = os.path.join(fe_service_dir, 'output.p1bin')

            if os.path.exists(input_path):
                output_dir = log_dir
            else:
                raise FileNotFoundError("No .p1bin file found for log '%s' (%s)." % (log_id, log_dir))
    else:
        raise FileNotFoundError("File '%s' not found." % input_path)

    result = [input_path]
    if return_output_dir:
        result.append(output_dir)
    if return_log_id:
        result.append(log_id)

    return result
