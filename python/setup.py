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


version = find_version('fusion_engine_client', '__init__.py')

message_requirements = set([
    'aenum>=3.1.1',
    # Note: Using the Point One fork of gpstime until the patch to download the leap
    # seconds file from alternate servers is merged:
    # https://gitlab.com/jrollins/gpstime/-/merge_requests/2
    'p1-gpstime>=0.6.3.dev1',
    'numpy>=1.16.0',
    'construct>=2.10.0',
])

tools_requirements = set([
    'argparse-formatter>=1.4',
    'scipy>=1.5.0',
])

display_requirements = set([
    'colorama>=0.4.4',
    'palettable>=3.3.0',
    'plotly>=4.0.0',
    'pymap3d>=2.4.3',
]) | tools_requirements

dev_requirements = set([
    'packaging>=21.0.0',
])

all_requirements = message_requirements | tools_requirements | display_requirements | dev_requirements

setup(
    name='fusion-engine-client',
    version=version,
    description='Point One FusionEngine Library',
    long_description="""\
Point One FusionEngine protocol support for real-time interaction and control, plus post-processing data analysis tools.

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
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    url='https://github.com/PointOneNav/fusion-engine-client',
    packages=find_packages(where='.'),
    entry_points={
        'console_scripts': [
            'p1_display = fusion_engine_client.applications.p1_display:main',
            'p1_extract = fusion_engine_client.applications.p1_extract:main',
            'p1_lband_extract = fusion_engine_client.applications.p1_lband_extract:main',
            'p1_print = fusion_engine_client.applications.p1_print:main',
        ]
    },
    python_requires='>=3.6',
    setup_requires=[
        'wheel>=0.36.2',
    ],
    install_requires=list(all_requirements),
    extras_require={
        # Kept for backwards compatibility.
        'all': [],
        'dev': [],
        'display': [],
        'tools': [],
    },
)
