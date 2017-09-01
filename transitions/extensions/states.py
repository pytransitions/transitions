from threading import Timer
from ..core import MachineError, listify
import logging
import itertools
import inspect

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class Tags(object):

    def __init__(self, *args, **kwargs):
        self.tags = kwargs.pop('tags', [])
        super(Tags, self).__init__(*args, **kwargs)

    def __getattr__(self, item):
        if item.startswith('is_'):
            return item[3:] in self.tags
        else:
            return super(Tags, self).__getattribute__(item)


class Error(Tags):

    def __init__(self, *args, **kwargs):
        tags = kwargs.get('tags', [])
        accepted = kwargs.pop('accepted', False)
        if accepted:
            tags.append('accepted')
            kwargs['tags'] = tags
        super(Error, self).__init__(*args, **kwargs)

    def enter(self, event_data):
        if len(event_data.machine.get_triggers(self.name)) == 0 and not self.is_accepted:
            raise MachineError("Error state '{0}' reached!".format(self.name))


class Timeout(object):

    dynamic_methods = ['on_timeout']

    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.pop('timeout', 0)
        self._on_timeout = None
        if self.timeout > 0:
            try:
                self.on_timeout = kwargs.pop('on_timeout')
            except KeyError:
                raise AttributeError("Timeout state requires 'on_timeout' when timeout is set.")
        self.runner = {}
        super(Timeout, self).__init__(*args, **kwargs)

    def enter(self, event_data):
        if self.timeout > 0:
            t = Timer(self.timeout, self._process_timeout, args=(event_data,))
            t.start()
            self.runner[id(event_data.model)] = t
        super(Timeout, self).enter(event_data)

    def exit(self, event_data):
        t = self.runner.get(id(event_data.model), None)
        if t is not None and t.is_alive:
            t.cancel()
        super(Timeout, self).exit(event_data)

    def _process_timeout(self, event_data):
        logger.debug("%sTimeout state %s. Processing callbacks...", event_data.machine.name, self.name)
        for oe in self.on_timeout:
            event_data.machine._callback(oe, event_data)
        logger.info("%sTimeout state %s processed.", event_data.machine.name, self.name)

    @property
    def on_timeout(self):
        return self._on_timeout

    @on_timeout.setter
    def on_timeout(self, value):
        self._on_timeout = listify(value)


class Volatile(object):

    def __init__(self, *args, **kwargs):
        self.volatile_cls = kwargs.pop('volatile', VolatileObject)
        self.volatile_hook = kwargs.pop('hook', 'scope')
        super(Volatile, self).__init__(*args, **kwargs)
        self.initialized = True

    def enter(self, event_data):
        setattr(event_data.model, self.volatile_hook, self.volatile_cls())
        super(Volatile, self).enter(event_data)

    def exit(self, event_data):
        super(Volatile, self).exit(event_data)
        try:
            delattr(event_data.model, self.volatile_hook)
        except AttributeError:
            pass


def add_state_features(*args):
    def class_decorator(cls):
        class CustomState(type('CustomState', args, {}), cls.state_cls):
            pass

        method_list = sum([c.dynamic_methods for c in inspect.getmro(CustomState) if hasattr(c, 'dynamic_methods')], [])
        CustomState.dynamic_methods = set(method_list)
        cls.state_cls = CustomState
        return cls
    return class_decorator


class VolatileObject(object):
    pass
