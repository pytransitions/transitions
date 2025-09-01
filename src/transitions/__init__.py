"""
transitions
-----------

A lightweight, object-oriented state machine implementation in Python. Compatible with Python 2.7+ and 3.0+.
"""

from __future__ import absolute_import
from .core import (State, Transition, Event, EventData, Machine, MachineError)

def _get_version():
    if not hasattr(_get_version, 'cached'):
        try:
            from importlib.metadata import version
            _get_version.cached = version(__name__)
        except ImportError:
            import pkg_resources
            _get_version.cached = pkg_resources.get_distribution(__name__).version
        except Exception:
            _get_version.cached = "unknown"
    return _get_version.cached

def __getattr__(name):
    if name == "__version__":
        return _get_version()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__copyright__ = "Copyright (c) 2024 Tal Yarkoni, Alexander Neumann"
__license__ = "MIT"
__summary__ = "A lightweight, object-oriented finite state machine implementation in Python with many extensions"
__uri__ = "https://github.com/pytransitions/transitions"
