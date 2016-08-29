from ..core import Machine, Transition, Event

from threading import RLock
import inspect


class LockedMethod:

    def __init__(self, lock, func):
        self.lock = lock
        self.func = func

    def __call__(self, *args, **kwargs):
        with self.lock:
            return self.func(*args, **kwargs)


class LockedEvent(Event):

    def trigger(self, model, *args, **kwargs):
        with self.machine.rlock:
            return super(LockedEvent, self).trigger(model, *args, **kwargs)


class LockedMachine(Machine):

    def __init__(self, *args, **kwargs):
        self.rlock = RLock()
        super(LockedMachine, self).__init__(*args, **kwargs)

    def __getattribute__(self, item):
        f = super(LockedMachine, self).__getattribute__
        tmp = f(item)
        if inspect.ismethod(tmp) and item not in "__getattribute__":
            return LockedMethod(f('rlock'), tmp)
        return tmp

    def __getattr__(self, item):
        try:
            return super(LockedMachine, self).__getattribute__(item)
        except AttributeError:
            return super(LockedMachine, self).__getattr__(item)

    @staticmethod
    def _create_event(*args, **kwargs):
        return LockedEvent(*args, **kwargs)
