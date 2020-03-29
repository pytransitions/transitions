import codecs
import sys
from setuptools import setup, find_packages

with open('transitions/version.py') as f:
    exec(f.read())

with codecs.open('README.md', 'r', 'utf-8') as f:
    import re
    # cut the badges from the description and also the TOC which is currently not working on PyPi
    regex = r"([\s\S]*)## Quickstart"
    readme = f.read()

    long_description = re.sub(regex, "## Quickstart", readme, 1)
    assert long_description[:13] == '## Quickstart'  # Description should start with a headline (## Quickstart)

tests_require = ['dill', 'graphviz', 'pygraphviz']
extras_require = {'diagrams': ['pygraphviz']}

extra_setuptools_args = {}
if 'setuptools' in sys.modules:
    extras_require['test'] = ['pytest']
    tests_require.append('pytest')

setup(
    name="transitions",
    version=__version__,
    description="A lightweight, object-oriented Python state machine implementation with many extensions.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Tal Yarkoni',
    author_email='tyarkoni@gmail.com',
    maintainer='Alexander Neumann',
    maintainer_email='aleneum@gmail.com',
    url='http://github.com/pytransitions/transitions',
    packages=find_packages(exclude=['tests', 'test_*']),
    package_data={'transitions': ['data/*'],
                  'transitions.tests': ['data/*']
                  },
    include_package_data=True,
    install_requires=['six'],
    extras_require=extras_require,
    tests_require=tests_require,
    license='MIT',
    download_url='https://github.com/pytransitions/transitions/archive/%s.tar.gz' % __version__,
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    **extra_setuptools_args
)
