import os
import sys
from setuptools import setup
from transitions.version import __version__

if len(set(('test', 'easy_install')).intersection(sys.argv)) > 0:
    import setuptools

extra_setuptools_args = {}
if 'setuptools' in sys.modules:
    extra_setuptools_args = dict(
        tests_require=['nose'],
        test_suite='nose.collector',
        extras_require=dict(
            test='nose>=0.10.1')
    )

setup(
    name="transitions",
    version=__version__,
    description="A lightweight, object-oriented Python state machine implementation.",
    author='Tal Yarkoni',
    author_email='tyarkoni@gmail.com',
    url='http://github.com/tyarkoni/transitions',
    packages=["transitions"],
    package_data={'transitions': ['data/*'],
                'transitions.tests': ['data/*']
                },
    download_url='https://github.com/tyarkoni/transitions/archive/%s.tar.gz' % __version__,
    **extra_setuptools_args
    )
