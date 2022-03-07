from setuptools import setup, find_packages

setup(
    name='fusion-engine-client',
    version='v1.9.0',
    packages=find_packages(where='.'),
    install_requires=[
        'gpstime @ https://github.com/PointOneNav/gpstime/archive/f9e2ab58a8beeeafee992d87a0eafc50887ba849.zip#egg=gpstime',
        'numpy>=1.16.0',
        'construct>=2.10.0',
    ],
    extras_require={
        'analysis': [
            'argparse-formatter>=1.4',
            'plotly>=4.0.0',
            'pymap3d>=2.4.3',
        ],
    },
)
