#
# setup.py
#

import setuptools

setuptools.setup(
    name="dgcatalog",
    version="0.0.1",
    author="DigitalGlobe",
    description="DigitalGlobe STAC catalog client",
    url="https://github.com/DigitalGlobe/goose-python-client",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        'requests'
    ]
)
