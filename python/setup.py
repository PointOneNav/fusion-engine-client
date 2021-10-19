from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

setup(
    name='fusion-engine-client',
    version='v1.8.0',
    packages=find_packages(where='.'),
    install_requires=[
        'wheel>=0.36.2',
        'aenum @ git+https://github.com/PointOneNav/aenum.git@extend-enum#egg=aenum',
        'numpy>=1.16.0',
        'construct>=2.10.0',
    ],
    extras_require={
        'analysis': ["plotly>=4.0.0","pymap3d>=2.4.3"],
    },
)
