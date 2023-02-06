from setuptools import setup, find_packages

setup(
    name='fusion-engine-client',
    version='v1.15.0',
    packages=find_packages(where='.'),
    install_requires=[
        'wheel>=0.36.2',
        'aenum @ git+https://github.com/PointOneNav/aenum.git@extend-enum#egg=aenum',
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
