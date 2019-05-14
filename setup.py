# -*- coding: utf-8 -*-

# HACK for `nose.collector` to work on python 2.7.3 and earlier
import multiprocessing
import os

from setuptools import find_packages, setup

# HACK READTHEDOCS (find a better solution)
if '/home/docs/checkouts/readthedocs' in os.getcwd():
    requires = []
else:
    requires = ['future', 'numpy', 'shapely']

setup(name='quantized-mesh-tile',
      version='0.6',
      description='Quantized-Mesh format reader and writer',
      author=u'Loic Gasser',
      author_email='loicgasser4@gmail.com',
      license='MIT',
      url='https://github.com/loicgasser/quantized-mesh-tile',
      packages=find_packages(exclude=['tests', 'doc']),
      zip_safe=False,
      test_suite='nose.collector',
      install_requires=requires,
      )
