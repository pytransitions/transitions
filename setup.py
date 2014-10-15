import os
import sys
from distutils.core import setup

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

# fetch version from within module
with open(os.path.join('transitions', 'version.py')) as f:
    exec(f.read())

setup(name="transitions",
      version=__version__,
      description="A lightweight, object-oriented Python state machine implementation.",
      maintainer='Tal Yarkoni',
      maintainer_email='tyarkoni@gmail.com',
      url='http://github.com/tyarkoni/transitions',
      packages=["transitions"],
      package_data={'transitions': ['data/*'],
                    'transitions.tests': ['data/*']
                    },
      **extra_setuptools_args
      )
