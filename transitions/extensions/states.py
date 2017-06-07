from threading import Timer
from six import string_types
from ..core import MachineError


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
        print(event_data.machine.get_triggers(self.name))
        if len(event_data.machine.get_triggers(self.name)) == 0 and not self.is_accepted:
            raise MachineError("Error state '{0}' reached!".format(self.name))


class Timeout(object):

    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.pop('timeout', 0)
        if self.timeout > 0:
            self.on_timeout = kwargs.pop('on_timeout', None)
            if self.on_timeout is None:
                raise AttributeError("Timeout state requires 'on_timeout' when timeout is set.")
        self.runner = {}
        super(Timeout, self).__init__(*args, **kwargs)

    def enter(self, event_data):
        if self.timeout > 0:
            func = getattr(event_data.model, self.on_timeout) if isinstance(self.on_timeout, string_types)\
                else self.on_timeout
            t = Timer(self.timeout, func)
            t.start()
            self.runner[id(event_data.model)] = t
        super(Timeout, self).enter(event_data)

    def exit(self, event_data):
        t = self.runner.get(id(event_data.model), None)
        if t is not None and t.is_alive:
            t.cancel()
        super(Timeout, self).exit(event_data)


class Volatile(object):

    def __init__(self, *args, **kwargs):
        self.volatile_cls = kwargs.pop('volatile', VolatileObject)
        self.volatile = self.volatile_cls()
        super(Volatile, self).__init__(*args, **kwargs)
        self.initialized = True

    def enter(self, event_data):
        self.volatile = self.volatile_cls()
        super(Volatile, self).enter(event_data)

    # def exit(self, event_data):
    #     super(Timeout, self).exit(event_data)
    #     del self.volatile

    def __getattr__(self, item):
        try:
            return super(Volatile, self).__getattribute__(item)
        except AttributeError:
            return super(Volatile, self).__getattribute__('volatile').__getattribute__(item)

    def __setattr__(self, key, value):
        if hasattr(self, 'initialized'):
            try:
                super(Volatile, self).__getattribute__(key)
                super(Volatile, self).__setattr__(key, value)
            except AttributeError:
                setattr(super(Volatile, self).__getattribute__('volatile'), key, value)
        else:
            super(Volatile, self).__setattr__(key, value)


def add_state_features(*args):
    def class_decorator(cls):
        class CustomState(type('CustomMixins', args, {}), cls.state_cls):
            pass

        cls.state_cls = CustomState
        return cls
    return class_decorator


class VolatileObject(object):
    pass
