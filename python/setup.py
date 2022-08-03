from setuptools import setup, find_packages

setup(
    name='fusion-engine-client',
    version='v1.11.2',
    packages=find_packages(where='.'),
    install_requires=[
        'numpy>=1.16.0',
        'construct>=2.10.0',
    ],
    extras_require={
        'analysis': [
            'argparse-formatter>=1.4',
            'gpstime>=0.6.2',
            'plotly>=4.0.0',
            'pymap3d>=2.4.3',
        ],
    },
)
