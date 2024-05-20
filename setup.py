from setuptools import setup, find_packages

setup(
    name='helmet_utils',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        # List the common dependencies here, e.g.,
        'numpy',
        'pandas',
        'geopandas',
        'shapely'
    ],
    extras_require={
        'landuse': [
            # List the landuse-specific dependencies here, e.g.,
            'rasterstats'
        ]
    }
)