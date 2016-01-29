from ..core import Machine, Transition, Event

from threading import RLock
import inspect
import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

class LockedMethod:

    def __init__(self, lock, func):
        self.lock = lock
        self.func = func

    def __call__(self, *args, **kwargs):
        with self.lock:
            return self.func(*args, **kwargs)


class LockedEvent(Event):

    def trigger(self, *args, **kwargs):
        with self.machine.lock:
            super(LockedEvent, self).trigger(*args, **kwargs)


class LockedMachine(Machine):

    def __init__(self, *args, **kwargs):
        self.lock = RLock()
        super(LockedMachine, self).__init__(*args, **kwargs)

    def __getattribute__(self, item):
        f = super(LockedMachine, self).__getattribute__
        tmp = f(item)
        if inspect.ismethod(tmp) and item not in "__getattribute__":
            return LockedMethod(f('lock'), tmp)
        return tmp

    def __getattr__(self, item):
        try:
            return super(LockedMachine, self).__getattribute__(item)
        except AttributeError:
            return super(LockedMachine, self).__getattr__(item)

    def add_transition(self, trigger, source, dest, **kwargs):
        if trigger not in self.events:
             self.events[trigger] = LockedEvent(trigger, self)
             setattr(self.model, trigger, self.events[trigger].trigger)
        super(LockedMachine, self).add_transition(trigger, source, dest, **kwargs)