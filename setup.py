# -*- coding: utf-8 -*-

# HACK for `nose.collector` to work on python 2.7.3 and earlier
import multiprocessing
from setuptools import setup, find_packages

setup(name='quantized-mesh-tile',
      version='0.0.1',
      description='Quantized-Mesh format reader and writer',
      author='Loic√c Gaer',
      author_email='loicgasser4@gmail.com',
      license='MIT',
      url='https://github.com/loicgasser/quantized-mesh-tile',
      packages=find_packages(exclude=['tests']),
      zip_safe=False,
      test_suite='nose.collector',
      install_requires=['shapely', 'numpy'],
      )
