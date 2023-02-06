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

setup(
    name='fusion-engine-client',
    version=version,
    packages=find_packages(where='.'),
    install_requires=[
        'numpy>=1.16.0',
        'construct>=2.10.0',
    ],
    extras_require={
        'analysis': [
            'argparse-formatter>=1.4',
            'colorama>=0.4.4',
            'gpstime>=0.6.2',
            'palettable>=3.3.0',
            'plotly>=4.0.0',
            'pymap3d>=2.4.3',
        ],
    },
)
