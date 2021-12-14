from setuptools import setup, find_packages

setup(
    name='fusion-engine-client',
    version='v1.9.0',
    packages=find_packages(where='.'),
    install_requires=[
        'numpy>=1.16.0',
        'construct>=2.10.0',
    ],
    extras_require={
        'analysis': ["plotly>=4.0.0", "pymap3d>=2.4.3"],
    },
)
