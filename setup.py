import sys
from setuptools import setup, find_packages

with open('transitions/version.py') as f:
    exec(f.read())

if len(set(('test', 'easy_install')).intersection(sys.argv)) > 0:
    import setuptools

tests_require = ['dill', 'pygraphviz']

extra_setuptools_args = {}
if 'setuptools' in sys.modules:
    tests_require.append('nose')
    extra_setuptools_args = dict(
        test_suite='nose.collector',
        extras_require=dict(
            test='nose>=0.10.1')
    )

setup(
    name="transitions",
    version=__version__,
    description="A lightweight, object-oriented Python state machine implementation.",
    maintainer='Tal Yarkoni',
    maintainer_email='tyarkoni@gmail.com',
    url='http://github.com/tyarkoni/transitions',
    packages=find_packages(exclude=['tests', 'test_*']),
    package_data={'transitions': ['data/*'],
                  'transitions.tests': ['data/*']
                  },
    install_requires=['six'],
    tests_require=tests_require,
    license='MIT',
    download_url='https://github.com/tyarkoni/transitions/archive/%s.tar.gz' % __version__,
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    **extra_setuptools_args
)
