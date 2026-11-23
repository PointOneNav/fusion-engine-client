import os
import re

from setuptools import setup, find_packages


def find_version(*file_paths):
    with open(os.path.join(*file_paths), 'rt') as f:
        version_file = f.read()
        version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
        if version_match:
            return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


def build_core():
    # A source distribution of the core package records its name in `PKG-INFO`, so a wheel built from it is a core
    # wheel even when the environment variable is not set (e.g., `pip install --no-binary`).
    if os.path.exists('PKG-INFO'):
        with open('PKG-INFO', 'rt') as f:
            if re.search(r"^Name: fusion[-_]engine[-_]client[-_]core$", f.read(), re.M):
                return True
    return os.environ.get('FUSION_ENGINE_CLIENT_CORE', '') not in ('', '0')


version = find_version('fusion_engine_client', '__init__.py')

# By default, build the full `fusion-engine-client` package. If `FUSION_ENGINE_CLIENT_CORE=1` is set, build the
# `fusion-engine-client-core` package instead. It contains the same code, but only requires the packages needed to
# encode and decode messages, and only installs the command-line applications that need nothing more (`p1_capture`,
# `p1_filter`, and `p1_print`). Install one or the other, never both, since they both contain `fusion_engine_client`.
core = build_core()

message_requirements = set([
    'aenum>=3.1.1',
    # Note: Using the Point One fork of gpstime until the patch to download the leap
    # seconds file from alternate servers is merged:
    # https://gitlab.com/jrollins/gpstime/-/merge_requests/2
    'p1-gpstime>=0.6.3.dev1',
    'numpy>=1.16.0',
    'construct>=2.10.0',
    # Note: Messages do not need this, but `utils.argument_parser` does, and applications that only use messages still
    # use that parser. It is small and has no requirements of its own.
    'argparse-formatter>=1.4',
    # Note: Messages do not need this either, but `p1_capture` (and the applications that use it) do. It is small and
    # has no requirements of its own.
    'colorama>=0.4.4',
])

tools_requirements = set([
    'scipy>=1.5.0',
])

display_requirements = set([
    'orjson>=3.9.0',
    'palettable>=3.3.0',
    # Note: Plotly 7 bundles a MapLibre build whose web worker is an ES module, which Chrome refuses
    # to start from a `file://` page. That breaks the generated map, which is normally opened as a
    # local file.
    'plotly>=6.9.0,<7',
    'pymap3d>=2.4.3',
]) | tools_requirements

dev_requirements = set([
    'packaging>=21.0.0',
])

all_requirements = message_requirements | tools_requirements | display_requirements | dev_requirements

# Applications that only need the core requirements. Both packages install these.
core_console_scripts = [
    'p1_capture = fusion_engine_client.applications.p1_capture:main',
    'p1_filter = fusion_engine_client.applications.p1_filter:main',
    'p1_print = fusion_engine_client.applications.p1_print:main',
]

if core:
    name = 'fusion-engine-client-core'
    install_requires = message_requirements
    console_scripts = core_console_scripts
    extras_require = {}
    description_note = """
This package contains only the requirements needed to encode and decode FusionEngine messages, and the `p1_capture`,
`p1_filter`, and `p1_print` applications. To use the analysis and display tools and the other `p1_*` applications,
install `fusion-engine-client` instead. Do not install both packages.
"""
else:
    name = 'fusion-engine-client'
    install_requires = all_requirements
    console_scripts = core_console_scripts + [
        'p1_display = fusion_engine_client.applications.p1_display:main',
        'p1_extract = fusion_engine_client.applications.p1_extract:main',
        'p1_lband_extract = fusion_engine_client.applications.p1_lband_extract:main',
        'p1_proxy = fusion_engine_client.applications.p1_proxy:main',
    ]
    extras_require = {
        # Kept for backwards compatibility.
        'all': [],
        'dev': [],
        'display': [],
        'tools': [],
    }
    description_note = """
If you only need to encode and decode FusionEngine messages, you may build the `fusion-engine-client-core` package from
source instead, which contains the same code without the analysis and display requirements. Do not install both
packages.
"""

setup(
    name=name,
    version=version,
    description='Point One FusionEngine Library',
    long_description=f"""\
Point One FusionEngine protocol support for real-time interaction and control, plus post-processing data analysis tools.
{description_note}
See https://github.com/PointOneNav/fusion-engine-client for full details. See https://pointonenav.com/docs/
for the latest FusionEngine message specification.
""",
    long_description_content_type='text/markdown',
    author='Point One Navigation',
    author_email='support@pointonenav.com',
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    url='https://github.com/PointOneNav/fusion-engine-client',
    download_url=f'https://github.com/PointOneNav/fusion-engine-client/archive/refs/tags/v{version}.tar.gz',
    packages=find_packages(where='.'),
    entry_points={
        'console_scripts': console_scripts,
    },
    python_requires='>=3.6',
    setup_requires=[
        'wheel>=0.36.2',
    ],
    install_requires=sorted(install_requires),
    extras_require=extras_require,
)
