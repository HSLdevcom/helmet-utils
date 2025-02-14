from setuptools import setup, find_packages

setup(
    name='helmet_utils',
    version='0.3',
    description='Utilities for the processing and adjusting of data used by Helmet',
    author='Santeri Hiitola | HSL',
    license='EUPL',
    packages=find_packages(),
    package_data={
        'helmet_utils': ['data/elevation_fixes.csv'],
    },
    install_requires=[
        'geopandas',
        'tabulate',
        'httpx',
        'rasterio'
    ],
    extras_require={
        'landuse': [
            'rasterstats'
        ]
    }
)