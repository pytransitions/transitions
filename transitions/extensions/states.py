"""
    transitions.extensions.states
    -----------------------------

    This module contains mix ins which can be used to extend state functionality.
"""

from collections import Counter
from threading import Timer
import logging
import inspect

from ..core import MachineError, listify, State

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())


class Tags(State):
    """ Allows states to be tagged.
        Attributes:
            tags (list): A list of tag strings. `State.is_<tag>` may be used
                to check if <tag> is in the list.
    """
    def __init__(self, *args, **kwargs):
        """
        Args:
            **kwargs: If kwargs contains `tags`, assign them to the attribute.
        """
        self.tags = kwargs.pop('tags', [])
        super(Tags, self).__init__(*args, **kwargs)

    def __getattr__(self, item):
        if item.startswith('is_'):
            return item[3:] in self.tags
        return super(Tags, self).__getattribute__(item)


class Error(Tags):
    """ This mix in builds upon tag and should be used INSTEAD of Tags if final states that have
        not been tagged with 'accepted' should throw an `MachineError`.
    """

    def __init__(self, *args, **kwargs):
        """
        Args:
            **kwargs: If kwargs contains the keyword `accepted` add the 'accepted' tag to a tag list
                which will be forwarded to the Tags constructor.
        """
        tags = kwargs.get('tags', [])
        accepted = kwargs.pop('accepted', False)
        if accepted:
            tags.append('accepted')
            kwargs['tags'] = tags
        super(Error, self).__init__(*args, **kwargs)

    def enter(self, event_data):
        """ Extends transitions.core.State.enter. Throws a `MachineError` if there is
            no leaving transition from this state and 'accepted' is not in self.tags.
        """
        if not event_data.machine.get_triggers(self.name) and not self.is_accepted:
            raise MachineError("Error state '{0}' reached!".format(self.name))
        super(Error, self).enter(event_data)


class Timeout(State):
    """ Adds timeout functionality to a state. Timeouts are handled model-specific.
    Attributes:
        timeout (float): Seconds after which a timeout function should be called.
        on_timeout (list): Functions to call when a timeout is triggered.
    """

    dynamic_methods = ['on_timeout']

    def __init__(self, *args, **kwargs):
        """
        Args:
            **kwargs: If kwargs contain 'timeout', assign the float value to self.timeout. If timeout
                is set, 'on_timeout' needs to be passed with kwargs as well or an AttributeError will
                be thrown. If timeout is not passed or equal 0.
        """
        self.timeout = kwargs.pop('timeout', 0)
        self._on_timeout = None
        if self.timeout > 0:
            try:
                self.on_timeout = kwargs.pop('on_timeout')
            except KeyError:
                raise AttributeError("Timeout state requires 'on_timeout' when timeout is set.")  # from KeyError
        else:
            self._on_timeout = kwargs.pop('on_timeout', [])
        self.runner = {}
        super(Timeout, self).__init__(*args, **kwargs)

    def enter(self, event_data):
        """ Extends `transitions.core.State.enter` by starting a timeout timer for the current model
            when the state is entered and self.timeout is larger than 0.
        """
        if self.timeout > 0:
            timer = Timer(self.timeout, self._process_timeout, args=(event_data,))
            timer.daemon = True
            timer.start()
            self.runner[id(event_data.model)] = timer
        return super(Timeout, self).enter(event_data)

    def exit(self, event_data):
        """ Extends `transitions.core.State.exit` by canceling a timer for the current model. """
        timer = self.runner.get(id(event_data.model), None)
        if timer is not None and timer.is_alive():
            timer.cancel()
        return super(Timeout, self).exit(event_data)

    def _process_timeout(self, event_data):
        _LOGGER.debug("%sTimeout state %s. Processing callbacks...", event_data.machine.name, self.name)
        for callback in self.on_timeout:
            event_data.machine.callback(callback, event_data)
        _LOGGER.info("%sTimeout state %s processed.", event_data.machine.name, self.name)

    @property
    def on_timeout(self):
        """ List of strings and callables to be called when the state timeouts. """
        return self._on_timeout

    @on_timeout.setter
    def on_timeout(self, value):
        """ Listifies passed values and assigns them to on_timeout."""
        self._on_timeout = listify(value)


class Volatile(State):
    """ Adds scopes/temporal variables to the otherwise persistent state objects.
    Attributes:
        volatile_cls (cls): Class of the temporal object to be initiated.
        volatile_hook (str): Model attribute name which will contain the volatile instance.
    """

    def __init__(self, *args, **kwargs):
        """
        Args:
            **kwargs: If kwargs contains `volatile`, always create an instance of the passed class
                whenever the state is entered. The instance is assigned to a model attribute which
                can be passed with the kwargs keyword `hook`. If hook is not passed, the instance will
                be assigned to the 'attribute' scope. If `volatile` is not passed, an empty object will
                be assigned to the model's hook.
        """
        self.volatile_cls = kwargs.pop('volatile', VolatileObject)
        self.volatile_hook = kwargs.pop('hook', 'scope')
        super(Volatile, self).__init__(*args, **kwargs)
        self.initialized = True

    def enter(self, event_data):
        """ Extends `transitions.core.State.enter` by creating a volatile object and assign it to
            the current model's hook. """
        setattr(event_data.model, self.volatile_hook, self.volatile_cls())
        super(Volatile, self).enter(event_data)

    def exit(self, event_data):
        """ Extends `transitions.core.State.exit` by deleting the temporal object from the model. """
        super(Volatile, self).exit(event_data)
        try:
            delattr(event_data.model, self.volatile_hook)
        except AttributeError:
            pass


class Retry(State):
    """ The Retry mix-in sets a limit on the number of times a state may be
        re-entered from itself.

        The first time a state is entered it does not count as a retry. Thus with
        `retries=3` the state can be entered four times before it fails.

        When the retry limit is exceeded, the state is not entered and instead the
        `on_failure` callback is invoked on the model. For example,

            Retry(retries=3, on_failure='to_failed')

        transitions the model directly to the 'failed' state, if the machine has
        automatic transitions enabled (the default).

        Attributes:
            retries (int): Number of retries to allow before failing.
            on_failure (str): Function to invoke on the model when the retry limit
                is exceeded.
    """
    def __init__(self, *args, **kwargs):
        """
        Args:
            **kwargs: If kwargs contains `retries`, then limit the number of times
                the state may be re-entered from itself. The argument `on_failure`,
                which is the function to invoke on the model when the retry limit
                is exceeded, must also be provided.
        """
        self.retries = kwargs.pop('retries', 0)
        self.on_failure = kwargs.pop('on_failure', None)
        self.retry_counts = Counter()
        if self.retries > 0 and self.on_failure is None:
            raise AttributeError("Retry state requires 'on_failure' when "
                                 "'retries' is set.")
        super(Retry, self).__init__(*args, **kwargs)

    def enter(self, event_data):
        k = id(event_data.model)

        # If we are entering from a different state, then this is our first try;
        # reset the retry counter.
        if event_data.transition.source != self.name:
            _LOGGER.debug('%sRetry limit for state %s reset (came from %s)',
                          event_data.machine.name, self.name,
                          event_data.transition.source)
            self.retry_counts[k] = 0

        # If we have tried too many times, invoke our failure callback instead
        if self.retry_counts[k] > self.retries > 0:
            _LOGGER.info('%sRetry count for state %s exceeded limit (%i)',
                         event_data.machine.name, self.name, self.retries)
            event_data.machine.callback(self.on_failure, event_data)
            return

        # Otherwise, increment the retry count and continue per normal
        _LOGGER.debug('%sRetry count for state %s is now %i',
                      event_data.machine.name, self.name, self.retry_counts[k])
        self.retry_counts.update((k,))
        super(Retry, self).enter(event_data)


def add_state_features(*args):
    """ State feature decorator. Should be used in conjunction with a custom Machine class. """
    def _class_decorator(cls):

        class CustomState(type('CustomState', args, {}), cls.state_cls):
            """ The decorated State. It is based on the State class used by the decorated Machine. """

        method_list = sum([c.dynamic_methods for c in inspect.getmro(CustomState) if hasattr(c, 'dynamic_methods')], [])
        CustomState.dynamic_methods = list(set(method_list))
        cls.state_cls = CustomState
        return cls
    return _class_decorator


class VolatileObject(object):
    """ Empty Python object which can be used to assign attributes to."""
