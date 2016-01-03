# Changelog

## 0.3.1 (January 3, 2016)
Mostly a bug fix release. Changes include:
- Fixes graphing bug introduced in 0.3.0 (thanks to @wtgee)
- Fixes bug in dynamic addition of before/after callbacks (though this is a currently undocumented feature)
- Adds coveralls support and badge
- Adds a few tests to achieve near-100% coverage

## 0.3.0 (January 2, 2016)
Release 0.3 includes a number of new features (nesting, multithreading, and graphing) as well as bug fixes and minor improvements:
- Support for nested states (thanks to @aleneum)
- Basic multithreading support for function access (thanks to @aleneum)
- Basic graphing support via graphviz (thanks to @svdgraaf)
- Stylistic edits, minor fixes, and improvements to README
- Expanded and refactored tests
- Minor bug fixes

## 0.2.9 (November 10, 2015)
- Enabled pickling in Python 3.4 (and in < 3.4 with the dill module)
- Added reference to generating Transition in EventData objects
- Fixed minor bugs

## 0.2.8 (August, 6, 2015)
- README improvements, added TOC, and typo fixes
- Condition checks now receive optional data
- Removed invasive basicConfig() call introduced with logging in 0.2.6

## 0.2.7 (July 27, 2015)
- Fixed import bug that prevented dependency installation at setup

## 0.2.6 (July 26, 2015)
- Added rudimentary logging for key transition and state change events
- Added generic before/after callbacks that apply to all state changes
- Ensured string type compatibility across Python 2 and 3

## 0.2.5 (May 4, 2015)
- Added ability to suppress invalid trigger calls
- Shorthand definition of transitions via lists

## 0.2.4 (March 11, 2015)
- Automatic detection of predefined state callbacks
- Fixed bug in automatic transition creation
- Added Changelog

## 0.2.3 (January 14, 2015)
- Added travis-ci support
- Cleaned up and PEP8fied code
- Added 'unless' argument to transitions that mirrors 'conditions'

## 0.2.2 (December 28, 2014)
- Python 2/3 compatibility
- Added automatic to_{state}() methods
- Added ability to easily add ordered transitions
