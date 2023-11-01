import os
import sys


def enable_relative_imports(name, file, package=None):
    """!
    @brief Enable relative imports for a Python script run as `python script.py`.

    When running an application directly as a script (e.g., python p1_*.py), rather than as an application installed by
    pip (e.g., p1_*), Python will not set the application's `__package__` setting, and will not include the module
    root directory (fusion-engine-client/python/) in the import search path. That means that by default, scripts cannot
    perform relative imports to other files in the same module. This function sets both of those things so that an
    application may perform either relative or absolute imports as needed.

    @note
    Note that Python will include the parent directory of the script itself in the search path, so we do not
    need to do that in order to do the _absolute_ import `from import_utils ...` below. However, if the file is being
    imported within another file and not executed directly (for example, called as `p1_*` from an entry point script
    installed by `pip`), its parent directory is _not_ guaranteed to be present on the search path so the absolute
    import will fail. It is highly recommended that you check the value of `__package__` before importing this function.

    For example, imagine an application `fusion_engine_client/applications/p1_my_app.py` and run as
    `python p1_my_app.py`:
    ```py
    if __package__ is None or __package__ == "":
        from import_utils import enable_relative_imports
        __package__ = enable_relative_imports(__name__, __file__, __package__)

    # Can now do a relative import (recommended):
    from ..messages import PoseMessage
    # or an absolute import:
    from fusion_engine_client.messages import PoseMessage
    ```
    """
    if name == "__main__":
        # Note that the root directory is fixed relative to the path to _this_ file, not the caller's file.
        root_dir = os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(__file__)), '../..'))
        sys.path.insert(0, root_dir)

        if package is None or package == "":
            package = os.path.dirname(os.path.relpath(file, root_dir)).replace('/', '.')
    return package
