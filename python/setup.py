from setuptools import setup, find_packages

setup(
    name='fusion-engine-client',
    version='v1.9.0',
    packages=find_packages(where='.'),
    install_requires=[
        'gpstime @ https://github.com/PointOneNav/gpstime/archive/416601324bc46ec496c393bb3e8ab7edd47fb937.zip#egg=gpstime',
        'numpy>=1.16.0',
        'construct>=2.10.0',
    ],
    extras_require={
        'analysis': ["plotly>=4.0.0", "pymap3d>=2.4.3"],
    },
)
