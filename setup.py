# -*- coding: utf-8 -*-

# HACK for `nose.collector` to work on python 2.7.3 and earlier
import multiprocessing
import os

from setuptools import find_packages, setup

# HACK READTHEDOCS (find a better solution)
if '/home/docs/checkouts/readthedocs' in os.getcwd():
    requires = []
else:
    requires = ['numpy', 'shapely']

setup(name='quantized-mesh-tile',
      version='0.6.1',
      description='Quantized-Mesh format reader and writer',
      author='Loic Gasser',
      author_email='loicgasser4@gmail.com',
      classifiers=[
        "Development Status :: Beta",
        "Environment :: Plugins",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Topic :: Scientific/Engineering :: GIS",
      ],
      license='MIT',
      keywords='gis tile terrain quantized-mesh',
      url='https://github.com/loicgasser/quantized-mesh-tile',
      packages=find_packages(exclude=['tests', 'doc']),
      zip_safe=False,
      test_suite='nose.collector',
      install_requires=requires,
      )
