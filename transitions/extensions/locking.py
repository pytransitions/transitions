from ..core import Machine, Transition, Event, listify

from threading import RLock
import inspect

try:
    from contextlib import nested  # Python 2
except ImportError:
    from contextlib import ExitStack, contextmanager

    @contextmanager
    def nested(*contexts):
        """
        Reimplementation of nested in python 3.
        """
        with ExitStack() as stack:
            for ctx in contexts:
                stack.enter_context(ctx)
            yield contexts


class LockedMethod:

    def __init__(self, context, func):
        self.context = context
        self.func = func

    def __call__(self, *args, **kwargs):
        with nested(*self.context):
            return self.func(*args, **kwargs)


class LockedEvent(Event):

    def trigger(self, model, *args, **kwargs):
        with nested(*self.machine.context):
            return super(LockedEvent, self).trigger(model, *args, **kwargs)


class LockedMachine(Machine):

    def __init__(self, *args, **kwargs):
        try:
            self.context = listify(kwargs.pop('context'))
        except KeyError:
            self.context = [RLock()]

        super(LockedMachine, self).__init__(*args, **kwargs)

    def __getattribute__(self, item):
        f = super(LockedMachine, self).__getattribute__
        tmp = f(item)
        if inspect.ismethod(tmp) and item not in "__getattribute__":
            return LockedMethod(f('context'), tmp)
        return tmp

    def __getattr__(self, item):
        try:
            return super(LockedMachine, self).__getattribute__(item)
        except AttributeError:
            return super(LockedMachine, self).__getattr__(item)

    @staticmethod
    def _create_event(*args, **kwargs):
        return LockedEvent(*args, **kwargs)
