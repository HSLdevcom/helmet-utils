from setuptools import setup, find_packages

setup(
    name='helmet_utils',
    version='0.2',
    description='Utilities for the processing and adjusting of data used by Helmet',
    author='Santeri Hiitola | HSL',
    license='EUPL',
    packages=find_packages(),
    install_requires=[
        'numpy',
        'pandas',
        'geopandas',
        'shapely',
        'tabulate'
    ],
    extras_require={
        'landuse': [
            'rasterstats'
        ]
    }
)