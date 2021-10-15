from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

setup(
    name='fusion-engine-client',
    version='v1.8.0',
    package_dir={'': 'fusion_engine_client'},
    packages=find_packages(where='fusion_engine_client'),
    install_requires=['numpy>=1.16.0'],
    extras_require={
        'analysis': ["plotly>=4.0.0","pymap3d>=2.4.3"],
    },
)
