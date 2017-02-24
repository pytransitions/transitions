from transitions.core import Machine, Transition, Event, listify

from collections import defaultdict
from threading import RLock
import inspect

try:
    from contextlib import nested  # Python 2
    # with nested statements now raise a DeprecationWarning. Should be replaced with ExitStack-like approaches.
    import warnings
    warnings.simplefilter('ignore', DeprecationWarning)

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


class PickleableLock(object):

    def __init__(self):
        self.lock = RLock()

    def __getstate__(self):
        return ''

    def __setstate__(self, value):
        return self.__init__()

    def __getattr__(self, item):
        return self.lock.__getattr__(item)

    def __enter__(self):
        self.lock.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.__exit__(exc_type, exc_val, exc_tb)


class LockedMethod:

    def __init__(self, context, func):
        self.context = context
        self.func = func

    def __call__(self, *args, **kwargs):
        with nested(*self.context):
            return self.func(*args, **kwargs)


class LockedEvent(Event):

    def trigger(self, model, *args, **kwargs):
        with nested(*self.machine.model_context_map[model]):
            return super(LockedEvent, self).trigger(model, *args, **kwargs)


class LockedMachine(Machine):

    def __init__(self, *args, **kwargs):
        try:
            self.machine_context = listify(kwargs.pop('machine_context'))
        except KeyError:
            self.machine_context = [PickleableLock()]

        self.model_context_map = defaultdict(list)

        super(LockedMachine, self).__init__(*args, **kwargs)

        if self.machine_context:
            for model in self.models:
                self.model_context_map[model].extend(self.machine_context)

    def add_model(self, model, *args, **kwargs):
        models = listify(model)

        try:
            model_context = listify(kwargs.pop('model_context'))
        except KeyError:
            model_context = []

        output = super(LockedMachine, self).add_model(models, *args, **kwargs)

        for model in models:
            self.model_context_map[model].extend(self.machine_context)
            self.model_context_map[model].extend(model_context)

        return output

    def remove_model(self, model, *args, **kwargs):
        models = listify(model)

        for model in models:
            del self.model_context_map[model]

        return super(LockedMachine, self).remove_model(models, *args, **kwargs)

    def __getattribute__(self, item):
        f = super(LockedMachine, self).__getattribute__
        tmp = f(item)
        if inspect.ismethod(tmp) and item not in "__getattribute__":
            return LockedMethod(f('machine_context'), tmp)
        return tmp

    def __getattr__(self, item):
        try:
            return super(LockedMachine, self).__getattribute__(item)
        except AttributeError:
            return super(LockedMachine, self).__getattr__(item)

    @staticmethod
    def _create_event(*args, **kwargs):
        return LockedEvent(*args, **kwargs)
