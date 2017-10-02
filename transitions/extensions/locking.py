"""
    transitions.extensions.factory
    ------------------------------

    Adds locking to machine methods as well as model functions that trigger events.
    Additionally, the user can inject her/his own context manager into the machine if required.
"""

from collections import defaultdict
from functools import partial
from threading import Lock
import inspect
import warnings
import logging

from transitions.core import Machine, Event, listify

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())

# this is a workaround for dill issues when partials and super is used in conjunction
# without it, Python 3.0 - 3.3 will not support pickling
# https://github.com/pytransitions/transitions/issues/236
_super = super

try:
    from contextlib import nested  # Python 2
    from thread import get_ident
    # with nested statements now raise a DeprecationWarning. Should be replaced with ExitStack-like approaches.
    warnings.simplefilter('ignore', DeprecationWarning)

except ImportError:
    from contextlib import ExitStack, contextmanager
    from threading import get_ident

    @contextmanager
    def nested(*contexts):
        """ Reimplementation of nested in Python 3. """
        with ExitStack() as stack:
            for ctx in contexts:
                stack.enter_context(ctx)
            yield contexts


class PicklableLock(object):
    """ A wrapper for threading.Lock which discards its state during pickling and
        is reinitialized unlocked when unpickled.
    """

    def __init__(self):
        self.lock = Lock()

    def __getstate__(self):
        return ''

    def __setstate__(self, value):
        return self.__init__()

    def __enter__(self):
        self.lock.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.__exit__(exc_type, exc_val, exc_tb)


class LockedEvent(Event):
    """ An event type which uses the parent's machine context map when triggered. """

    def trigger(self, model, *args, **kwargs):
        """ Extends transitions.core.Event.trigger by using locks/machine contexts. """
        # pylint: disable=protected-access
        # noinspection PyProtectedMember
        # LockedMachine._locked should not be called somewhere else. That's why it should not be exposed
        # to Machine users.
        if self.machine._locked != get_ident():
            with nested(*self.machine.model_context_map[model]):
                return _super(LockedEvent, self).trigger(model, *args, **kwargs)
        else:
            return _super(LockedEvent, self).trigger(model, *args, **kwargs)


class LockedMachine(Machine):
    """ Machine class which manages contexts. In it's default version the machine uses a `threading.Lock`
        context to lock access to its methods and event triggers bound to model objects.
    Attributes:
        machine_context (dict): A dict of context managers to be entered whenever a machine method is
            called or an event is triggered. Contexts are managed for each model individually.
    """

    event_cls = LockedEvent

    def __init__(self, *args, **kwargs):
        self._locked = 0

        try:
            self.machine_context = listify(kwargs.pop('machine_context'))
        except KeyError:
            self.machine_context = [PicklableLock()]

        self.machine_context.append(self)
        self.model_context_map = defaultdict(list)

        _super(LockedMachine, self).__init__(*args, **kwargs)

    def add_model(self, model, initial=None, model_context=None):
        """ Extends `transitions.core.Machine.add_model` by `model_context` keyword.
        Args:
            model (list or object): A model (list) to be managed by the machine.
            initial (string or State): The initial state of the passed model[s].
            model_context (list or object): If passed, assign the context (list) to the machines
                model specific context map.
        """
        models = listify(model)
        model_context = listify(model_context) if model_context is not None else []
        output = _super(LockedMachine, self).add_model(models, initial)

        for mod in models:
            mod = self if mod == 'self' else mod
            self.model_context_map[mod].extend(self.machine_context)
            self.model_context_map[mod].extend(model_context)

        return output

    def remove_model(self, model):
        """ Extends `transitions.core.Machine.remove_model` by removing model specific context maps
            from the machine when the model itself is removed. """
        models = listify(model)

        for mod in models:
            del self.model_context_map[mod]

        return _super(LockedMachine, self).remove_model(models)

    def __getattribute__(self, item):
        get_attr = _super(LockedMachine, self).__getattribute__
        tmp = get_attr(item)
        if not item.startswith('_') and inspect.ismethod(tmp):
            return partial(get_attr('_locked_method'), tmp)
        return tmp

    def __getattr__(self, item):
        try:
            return _super(LockedMachine, self).__getattribute__(item)
        except AttributeError:
            return _super(LockedMachine, self).__getattr__(item)

    # Determine if the returned method is a partial and make sure the returned partial has
    # not been created by Machine.__getattr__.
    # https://github.com/tyarkoni/transitions/issues/214
    def _add_model_to_state(self, state, model):
        _super(LockedMachine, self)._add_model_to_state(state, model)  # pylint: disable=protected-access
        for prefix in ['enter', 'exit']:
            callback = "on_{0}_".format(prefix) + state.name
            func = getattr(model, callback, None)
            if isinstance(func, partial) and func.func != state.add_callback:
                state.add_callback(prefix, callback)

    def _locked_method(self, func, *args, **kwargs):
        if self._locked != get_ident():
            with nested(*self.machine_context):
                return func(*args, **kwargs)
        else:
            return func(*args, **kwargs)

    def __enter__(self):
        self._locked = get_ident()

    def __exit__(self, *exc):
        self._locked = 0
