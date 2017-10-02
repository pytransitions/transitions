"""
transitions
-----------

A lightweight, object-oriented state machine implementation in Python. Compatible with Python 2.7+ and 3.0+.
"""

from __future__ import absolute_import
from .version import __version__
from .core import (State, Transition, Event, EventData, Machine, MachineError)

__copyright__ = "Copyright (c) 2017 Tal Yarkoni"
__license__ = "MIT"
__summary__ = "A lightweight, object-oriented finite state machine in Python"
__uri__ = "https://github.com/tyarkoni/transitions"
