from __future__ import absolute_import
from .version import __version__, __updated__

from .core import (State, Transition, Event, EventData, Machine, MachineError,
                   logger)
__copyright__ = "Copyright (c) 2014 Tal Yarkoni"
__license__ = "MIT"
__summary__ = "A lightweight, object-oriented finite state machine in Python"
__uri__ = "https://github.com/tyarkoni/transitions"
