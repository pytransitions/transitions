"""
    transitions.core
    ----------------

    This module contains the central parts of transitions which are the state machine logic, state
    and transition concepts.
"""


try:
    from builtins import object
except ImportError:
    # python2
    pass

try:
    # Enums are supported for Python 3.4+ and Python 2.7 with enum34 package installed
    from enum import Enum, EnumMeta
except ImportError:
    # If enum is not available, create dummy classes for type checks
    class Enum:
        pass

    class EnumMeta:
        pass

import inspect
import itertools
import logging

from collections import OrderedDict, defaultdict, deque
from functools import partial
from six import string_types
import warnings

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())

warnings.filterwarnings(action='default', message=r".*transitions version.*", category=DeprecationWarning)


def listify(obj):
    """Wraps a passed object into a list in case it has not been a list, tuple before.
    Returns an empty list in case ``obj`` is None.
    Args:
        obj: instance to be converted into a list.
    Returns:
        list: May also return a tuple in case ``obj`` has been a tuple before.
    """
    if obj is None:
        return []

    return obj if isinstance(obj, (list, tuple, EnumMeta)) else [obj]


def _prep_ordered_arg(desired_length, arguments=None):
    """Ensure list of arguments passed to add_ordered_transitions has the proper length.
    Expands the given arguments and apply same condition, callback
    to all transitions if only one has been given.

    Args:
        desired_length (int): The size of the resulting list
        arguments (optional[str, reference or list]): Parameters to be expanded.
    Returns:
        list: Parameter sets with the desired length.
    """
    arguments = listify(arguments) if arguments is not None else [None]
    if len(arguments) != desired_length and len(arguments) != 1:
        raise ValueError("Argument length must be either 1 or the same length as "
                         "the number of transitions.")
    if len(arguments) == 1:
        return arguments * desired_length
    return arguments


class State(object):
    """A persistent representation of a state managed by a ``Machine``.

    Attributes:
        name (str): State name which is also assigned to the model(s).
        on_enter (list): Callbacks executed when a state is entered.
        on_exit (list): Callbacks executed when a state is exited.
        ignore_invalid_triggers (bool): Indicates if unhandled/invalid triggers should raise an exception.
    """

    # A list of dynamic methods which can be resolved by a ``Machine`` instance for convenience functions.
    # Dynamic methods for states must always start with `on_`!
    dynamic_methods = ['on_enter', 'on_exit']

    def __init__(self, name, on_enter=None, on_exit=None,
                 ignore_invalid_triggers=None):
        """
        Args:
            name (str or Enum): The name of the state
            on_enter (str or list): Optional callable(s) to trigger when a
                state is entered. Can be either a string providing the name of
                a callable, or a list of strings.
            on_exit (str or list): Optional callable(s) to trigger when a
                state is exited. Can be either a string providing the name of a
                callable, or a list of strings.
            ignore_invalid_triggers (Boolean): Optional flag to indicate if
                unhandled/invalid triggers should raise an exception

        """
        self._name = name
        self.ignore_invalid_triggers = ignore_invalid_triggers
        self.on_enter = listify(on_enter) if on_enter else []
        self.on_exit = listify(on_exit) if on_exit else []

    @property
    def name(self):
        if isinstance(self._name, Enum):
            return self._name.name
        else:
            return self._name

    @property
    def value(self):
        return self._name

    def enter(self, event_data):
        """ Triggered when a state is entered. """
        _LOGGER.debug("%sEntering state %s. Processing callbacks...", event_data.machine.name, self.name)
        event_data.machine.callbacks(self.on_enter, event_data)
        _LOGGER.info("%sFinished processing state %s enter callbacks.", event_data.machine.name, self.name)

    def exit(self, event_data):
        """ Triggered when a state is exited. """
        _LOGGER.debug("%sExiting state %s. Processing callbacks...", event_data.machine.name, self.name)
        event_data.machine.callbacks(self.on_exit, event_data)
        _LOGGER.info("%sFinished processing state %s exit callbacks.", event_data.machine.name, self.name)

    def add_callback(self, trigger, func):
        """ Add a new enter or exit callback.
        Args:
            trigger (str): The type of triggering event. Must be one of
                'enter' or 'exit'.
            func (str): The name of the callback function.
        """
        callback_list = getattr(self, 'on_' + trigger)
        callback_list.append(func)

    def __repr__(self):
        return "<%s('%s')@%s>" % (type(self).__name__, self.name, id(self))


class Condition(object):
    """ A helper class to call condition checks in the intended way.

    Attributes:
        func (callable): The function to call for the condition check
        target (bool): Indicates the target state--i.e., when True,
                the condition-checking callback should return True to pass,
                and when False, the callback should return False to pass.
    """

    def __init__(self, func, target=True):
        """
        Args:
            func (str): Name of the condition-checking callable
            target (bool): Indicates the target state--i.e., when True,
                the condition-checking callback should return True to pass,
                and when False, the callback should return False to pass.
        Notes:
            This class should not be initialized or called from outside a
            Transition instance, and exists at module level (rather than
            nesting under the transition class) only because of a bug in
            dill that prevents serialization under Python 2.7.
        """
        self.func = func
        self.target = target

    def check(self, event_data):
        """ Check whether the condition passes.
        Args:
            event_data (EventData): An EventData instance to pass to the
                condition (if event sending is enabled) or to extract arguments
                from (if event sending is disabled). Also contains the data
                model attached to the current machine which is used to invoke
                the condition.
        """
        predicate = event_data.machine.resolve_callable(self.func, event_data)
        if event_data.machine.send_event:
            return predicate(event_data) == self.target
        return predicate(*event_data.args, **event_data.kwargs) == self.target

    def __repr__(self):
        return "<%s(%s)@%s>" % (type(self).__name__, self.func, id(self))


class Transition(object):
    """ Representation of a transition managed by a ``Machine`` instance.

    Attributes:
        source (str): Source state of the transition.
        dest (str): Destination state of the transition.
        prepare (list): Callbacks executed before conditions checks.
        conditions (list): Callbacks evaluated to determine if
            the transition should be executed.
        before (list): Callbacks executed before the transition is executed
            but only if condition checks have been successful.
        after (list): Callbacks executed after the transition is executed
            but only if condition checks have been successful.
    """

    dynamic_methods = ['before', 'after', 'prepare']
    """ A list of dynamic methods which can be resolved by a ``Machine`` instance for convenience functions. """
    condition_cls = Condition
    """ The class used to wrap condition checks. Can be replaced to alter condition resolution behaviour
        (e.g. OR instead of AND for 'conditions' or AND instead of OR for 'unless') """

    def __init__(self, source, dest, conditions=None, unless=None, before=None,
                 after=None, prepare=None):
        """
        Args:
            source (str): The name of the source State.
            dest (str): The name of the destination State.
            conditions (optional[str, callable or list]): Condition(s) that must pass in order for
                the transition to take place. Either a string providing the
                name of a callable, or a list of callables. For the transition
                to occur, ALL callables must return True.
            unless (optional[str, callable or list]): Condition(s) that must return False in order
                for the transition to occur. Behaves just like conditions arg
                otherwise.
            before (optional[str, callable or list]): callbacks to trigger before the
                transition.
            after (optional[str, callable or list]): callbacks to trigger after the transition.
            prepare (optional[str, callable or list]): callbacks to trigger before conditions are checked
        """
        self.source = source
        self.dest = dest
        self.prepare = [] if prepare is None else listify(prepare)
        self.before = [] if before is None else listify(before)
        self.after = [] if after is None else listify(after)

        self.conditions = []
        if conditions is not None:
            for cond in listify(conditions):
                self.conditions.append(self.condition_cls(cond))
        if unless is not None:
            for cond in listify(unless):
                self.conditions.append(self.condition_cls(cond, target=False))

    def _eval_conditions(self, event_data):
        for cond in self.conditions:
            if not cond.check(event_data):
                _LOGGER.debug("%sTransition condition failed: %s() does not return %s. Transition halted.",
                              event_data.machine.name, cond.func, cond.target)
                return False
        return True

    def execute(self, event_data):
        """ Execute the transition.
        Args:
            event_data: An instance of class EventData.
        Returns: boolean indicating whether or not the transition was
            successfully executed (True if successful, False if not).
        """
        _LOGGER.debug("%sInitiating transition from state %s to state %s...",
                      event_data.machine.name, self.source, self.dest)

        event_data.machine.callbacks(self.prepare, event_data)
        _LOGGER.debug("%sExecuted callbacks before conditions.", event_data.machine.name)

        if not self._eval_conditions(event_data):
            return False

        event_data.machine.callbacks(itertools.chain(event_data.machine.before_state_change, self.before), event_data)
        _LOGGER.debug("%sExecuted callback before transition.", event_data.machine.name)

        if self.dest:  # if self.dest is None this is an internal transition with no actual state change
            self._change_state(event_data)

        event_data.machine.callbacks(itertools.chain(self.after, event_data.machine.after_state_change), event_data)
        _LOGGER.debug("%sExecuted callback after transition.", event_data.machine.name)
        return True

    def _change_state(self, event_data):
        event_data.machine.get_state(self.source).exit(event_data)
        event_data.machine.set_state(self.dest, event_data.model)
        event_data.update(getattr(event_data.model, event_data.machine.model_attribute))
        event_data.machine.get_state(self.dest).enter(event_data)

    def add_callback(self, trigger, func):
        """ Add a new before, after, or prepare callback.
        Args:
            trigger (str): The type of triggering event. Must be one of
                'before', 'after' or 'prepare'.
            func (str): The name of the callback function.
        """
        callback_list = getattr(self, trigger)
        callback_list.append(func)

    def __repr__(self):
        return "<%s('%s', '%s')@%s>" % (type(self).__name__,
                                        self.source, self.dest, id(self))


class EventData(object):
    """ Collection of relevant data related to the ongoing transition attempt.

    Attributes:
        state (State): The State from which the Event was triggered.
        event (Event): The triggering Event.
        machine (Machine): The current Machine instance.
        model (object): The model/object the machine is bound to.
        args (list): Optional positional arguments from trigger method
            to store internally for possible later use.
        kwargs (dict): Optional keyword arguments from trigger method
            to store internally for possible later use.
        transition (Transition): Currently active transition. Will be assigned during triggering.
        error (Error): In case a triggered event causes an Error, it is assigned here and passed on.
        result (bool): True in case a transition has been successful, False otherwise.
    """

    def __init__(self, state, event, machine, model, args, kwargs):
        """
        Args:
            state (State): The State from which the Event was triggered.
            event (Event): The triggering Event.
            machine (Machine): The current Machine instance.
            model (object): The model/object the machine is bound to.
            args (tuple): Optional positional arguments from trigger method
                to store internally for possible later use.
            kwargs (dict): Optional keyword arguments from trigger method
                to store internally for possible later use.
        """
        self.state = state
        self.event = event
        self.machine = machine
        self.model = model
        self.args = args
        self.kwargs = kwargs
        self.transition = None
        self.error = None
        self.result = False

    def update(self, state):
        """ Updates the EventData object with the passed state.

        Attributes:
            state (State, str or Enum): The state object, enum member or string to assign to EventData.
        """

        if not isinstance(state, State):
            self.state = self.machine.get_state(state)

    def __repr__(self):
        return "<%s('%s', %s)@%s>" % (type(self).__name__, self.state,
                                      getattr(self, 'transition'), id(self))


class Event(object):
    """ A collection of transitions assigned to the same trigger

    """

    def __init__(self, name, machine):
        """
        Args:
            name (str): The name of the event, which is also the name of the
                triggering callable (e.g., 'advance' implies an advance()
                method).
            machine (Machine): The current Machine instance.
        """
        self.name = name
        self.machine = machine
        self.transitions = defaultdict(list)

    def add_transition(self, transition):
        """ Add a transition to the list of potential transitions.
        Args:
            transition (Transition): The Transition instance to add to the
                list.
        """
        self.transitions[transition.source].append(transition)

    def trigger(self, model, *args, **kwargs):
        """ Serially execute all transitions that match the current state,
        halting as soon as one successfully completes.
        Args:
            args and kwargs: Optional positional or named arguments that will
                be passed onto the EventData object, enabling arbitrary state
                information to be passed on to downstream triggered functions.
        Returns: boolean indicating whether or not a transition was
            successfully executed (True if successful, False if not).
        """
        func = partial(self._trigger, model, *args, **kwargs)
        # pylint: disable=protected-access
        # noinspection PyProtectedMember
        # Machine._process should not be called somewhere else. That's why it should not be exposed
        # to Machine users.
        return self.machine._process(func)

    def _trigger(self, model, *args, **kwargs):
        """ Internal trigger function called by the ``Machine`` instance. This should not
        be called directly but via the public method ``Machine.trigger``.
        """
        state = self.machine.get_model_state(model)
        if state.name not in self.transitions:
            msg = "%sCan't trigger event %s from state %s!" % (self.machine.name, self.name,
                                                               state.name)
            ignore = state.ignore_invalid_triggers if state.ignore_invalid_triggers is not None \
                else self.machine.ignore_invalid_triggers
            if ignore:
                _LOGGER.warning(msg)
                return False
            else:
                raise MachineError(msg)
        event_data = EventData(state, self, self.machine, model, args=args, kwargs=kwargs)
        return self._process(event_data)

    def _process(self, event_data):
        self.machine.callbacks(self.machine.prepare_event, event_data)
        _LOGGER.debug("%sExecuted machine preparation callbacks before conditions.", self.machine.name)

        try:
            for trans in self.transitions[event_data.state.name]:
                event_data.transition = trans
                if trans.execute(event_data):
                    event_data.result = True
                    break
        except Exception as err:
            event_data.error = err
            if self.machine.on_exception:
                self.machine.callbacks(self.machine.on_exception, event_data)
            else:
                raise
        finally:
            try:
                self.machine.callbacks(self.machine.finalize_event, event_data)
                _LOGGER.debug("%sExecuted machine finalize callbacks", self.machine.name)
            except Exception as err:
                _LOGGER.error("%sWhile executing finalize callbacks a %s occurred: %s.",
                              self.machine.name,
                              type(err).__name__,
                              str(err))

        return event_data.result

    def __repr__(self):
        return "<%s('%s')@%s>" % (type(self).__name__, self.name, id(self))

    def add_callback(self, trigger, func):
        """ Add a new before or after callback to all available transitions.
        Args:
            trigger (str): The type of triggering event. Must be one of
                'before', 'after' or 'prepare'.
            func (str): The name of the callback function.
        """
        for trans in itertools.chain(*self.transitions.values()):
            trans.add_callback(trigger, func)


class Machine(object):
    """ Machine manages states, transitions and models. In case it is initialized without a specific model
    (or specifically no model), it will also act as a model itself. Machine takes also care of decorating
    models with conveniences functions related to added transitions and states during runtime.

    Attributes:
        states (OrderedDict): Collection of all registered states.
        events (dict): Collection of transitions ordered by trigger/event.
        models (list): List of models attached to the machine.
        initial (str): Name of the initial state for new models.
        prepare_event (list): Callbacks executed when an event is triggered.
        before_state_change (list): Callbacks executed after condition checks but before transition is conducted.
            Callbacks will be executed BEFORE the custom callbacks assigned to the transition.
        after_state_change (list): Callbacks executed after the transition has been conducted.
            Callbacks will be executed AFTER the custom callbacks assigned to the transition.
        finalize_event (list): Callbacks will be executed after all transitions callbacks have been executed.
            Callbacks mentioned here will also be called if a transition or condition check raised an error.
        queued (bool): Whether transitions in callbacks should be executed immediately (False) or sequentially.
        send_event (bool): When True, any arguments passed to trigger methods will be wrapped in an EventData
            object, allowing indirect and encapsulated access to data. When False, all positional and keyword
            arguments will be passed directly to all callback methods.
        auto_transitions (bool):  When True (default), every state will automatically have an associated
            to_{state}() convenience trigger in the base model.
        ignore_invalid_triggers (bool): When True, any calls to trigger methods that are not valid for the
            present state (e.g., calling an a_to_b() trigger when the current state is c) will be silently
            ignored rather than raising an invalid transition exception.
        name (str): Name of the ``Machine`` instance mainly used for easier log message distinction.
    """

    separator = '_'  # separates callback type from state/transition name
    wildcard_all = '*'  # will be expanded to ALL states
    wildcard_same = '='  # will be expanded to source state
    state_cls = State
    transition_cls = Transition
    event_cls = Event

    def __init__(self, model='self', states=None, initial='initial', transitions=None,
                 send_event=False, auto_transitions=True,
                 ordered_transitions=False, ignore_invalid_triggers=None,
                 before_state_change=None, after_state_change=None, name=None,
                 queued=False, prepare_event=None, finalize_event=None, model_attribute='state', on_exception=None,
                 **kwargs):
        """
        Args:
            model (object or list): The object(s) whose states we want to manage. If 'self',
                the current Machine instance will be used the model (i.e., all
                triggering events will be attached to the Machine itself). Note that an empty list
                is treated like no model.
            states (list or Enum): A list or enumeration of valid states. Each list element can be either a
                string, an enum member or a State instance. If string or enum member, a new generic State
                instance will be created that is named according to the string or enum member's name.
            initial (str, Enum or State): The initial state of the passed model[s].
            transitions (list): An optional list of transitions. Each element
                is a dictionary of named arguments to be passed onto the
                Transition initializer.
            send_event (boolean): When True, any arguments passed to trigger
                methods will be wrapped in an EventData object, allowing
                indirect and encapsulated access to data. When False, all
                positional and keyword arguments will be passed directly to all
                callback methods.
            auto_transitions (boolean): When True (default), every state will
                automatically have an associated to_{state}() convenience
                trigger in the base model.
            ordered_transitions (boolean): Convenience argument that calls
                add_ordered_transitions() at the end of initialization if set
                to True.
            ignore_invalid_triggers: when True, any calls to trigger methods
                that are not valid for the present state (e.g., calling an
                a_to_b() trigger when the current state is c) will be silently
                ignored rather than raising an invalid transition exception.
            before_state_change: A callable called on every change state before
                the transition happened. It receives the very same args as normal
                callbacks.
            after_state_change: A callable called on every change state after
                the transition happened. It receives the very same args as normal
                callbacks.
            name: If a name is set, it will be used as a prefix for logger output
            queued (boolean): When True, processes transitions sequentially. A trigger
                executed in a state callback function will be queued and executed later.
                Due to the nature of the queued processing, all transitions will
                _always_ return True since conditional checks cannot be conducted at queueing time.
            prepare_event: A callable called on for before possible transitions will be processed.
                It receives the very same args as normal callbacks.
            finalize_event: A callable called on for each triggered event after transitions have been processed.
                This is also called when a transition raises an exception.
            on_exception: A callable called when an event raises an exception. If not set,
                the exception will be raised instead.

            **kwargs additional arguments passed to next class in MRO. This can be ignored in most cases.
        """

        # calling super in case `Machine` is used as a mix in
        # all keyword arguments should be consumed by now if this is not the case
        try:
            super(Machine, self).__init__(**kwargs)
        except TypeError as err:
            raise ValueError('Passing arguments {0} caused an inheritance error: {1}'.format(kwargs.keys(), err))

        # initialize protected attributes first
        self._queued = queued
        self._transition_queue = deque()
        self._before_state_change = []
        self._after_state_change = []
        self._prepare_event = []
        self._finalize_event = []
        self._on_exception = []
        self._initial = None

        self.states = OrderedDict()
        self.events = {}
        self.send_event = send_event
        self.auto_transitions = auto_transitions
        self.ignore_invalid_triggers = ignore_invalid_triggers
        self.prepare_event = prepare_event
        self.before_state_change = before_state_change
        self.after_state_change = after_state_change
        self.finalize_event = finalize_event
        self.on_exception = on_exception
        self.name = name + ": " if name is not None else ""
        self.model_attribute = model_attribute

        self.models = []

        if states is not None:
            self.add_states(states)

        if initial is not None:
            self.initial = initial

        if transitions is not None:
            self.add_transitions(transitions)

        if ordered_transitions:
            self.add_ordered_transitions()

        if model:
            self.add_model(model)

    def add_model(self, model, initial=None):
        """ Register a model with the state machine, initializing triggers and callbacks. """
        models = listify(model)

        if initial is None:
            if self.initial is None:
                raise ValueError("No initial state configured for machine, must specify when adding model.")
            else:
                initial = self.initial

        for mod in models:
            mod = self if mod == 'self' else mod
            if mod not in self.models:
                self._checked_assignment(mod, 'trigger', partial(self._get_trigger, mod))

                for trigger in self.events:
                    self._add_trigger_to_model(trigger, mod)

                for state in self.states.values():
                    self._add_model_to_state(state, mod)

                self.set_state(initial, model=mod)
                self.models.append(mod)

    def remove_model(self, model):
        """ Remove a model from the state machine. The model will still contain all previously added triggers
        and callbacks, but will not receive updates when states or transitions are added to the Machine.
        If an event queue is used, all queued events of that model will be removed."""
        models = listify(model)

        for mod in models:
            self.models.remove(mod)
        if len(self._transition_queue) > 0:
            # the first element of the list is currently executed. Keeping it for further Machine._process(ing)
            self._transition_queue = deque(
                [self._transition_queue[0]] + [e for e in self._transition_queue if e.args[0] not in models])

    @classmethod
    def _create_transition(cls, *args, **kwargs):
        return cls.transition_cls(*args, **kwargs)

    @classmethod
    def _create_event(cls, *args, **kwargs):
        return cls.event_cls(*args, **kwargs)

    @classmethod
    def _create_state(cls, *args, **kwargs):
        return cls.state_cls(*args, **kwargs)

    @property
    def initial(self):
        """ Return the initial state. """
        return self._initial

    @initial.setter
    def initial(self, value):
        if isinstance(value, State):
            if value.name not in self.states:
                self.add_state(value)
            else:
                _ = self._has_state(value, raise_error=True)
            self._initial = value.name
        else:
            state_name = value.name if isinstance(value, Enum) else value
            if state_name not in self.states:
                self.add_state(state_name)
            self._initial = state_name

    @property
    def has_queue(self):
        """ Return boolean indicating if machine has queue or not """
        return self._queued

    @property
    def model(self):
        """ List of models attached to the machine. For backwards compatibility, the property will
        return the model instance itself instead of the underlying list  if there is only one attached
        to the machine.
        """
        if len(self.models) == 1:
            return self.models[0]
        return self.models

    @property
    def before_state_change(self):
        """Callbacks executed after condition checks but before transition is conducted.
        Callbacks will be executed BEFORE the custom callbacks assigned to the transition."""
        return self._before_state_change

    # this should make sure that _before_state_change is always a list
    @before_state_change.setter
    def before_state_change(self, value):
        self._before_state_change = listify(value)

    @property
    def after_state_change(self):
        """Callbacks executed after the transition has been conducted.
        Callbacks will be executed AFTER the custom callbacks assigned to the transition."""
        return self._after_state_change

    # this should make sure that _after_state_change is always a list
    @after_state_change.setter
    def after_state_change(self, value):
        self._after_state_change = listify(value)

    @property
    def prepare_event(self):
        """Callbacks executed when an event is triggered."""
        return self._prepare_event

    # this should make sure that prepare_event is always a list
    @prepare_event.setter
    def prepare_event(self, value):
        self._prepare_event = listify(value)

    @property
    def finalize_event(self):
        """Callbacks will be executed after all transitions callbacks have been executed.
        Callbacks mentioned here will also be called if a transition or condition check raised an error."""
        return self._finalize_event

    # this should make sure that finalize_event is always a list
    @finalize_event.setter
    def finalize_event(self, value):
        self._finalize_event = listify(value)

    @property
    def on_exception(self):
        """Callbacks will be executed when an Event raises an Exception."""
        return self._on_exception

    # this should make sure that finalize_event is always a list
    @on_exception.setter
    def on_exception(self, value):
        self._on_exception = listify(value)

    def get_state(self, state):
        """ Return the State instance with the passed name. """
        if isinstance(state, Enum):
            state = state.name
        if state not in self.states:
            raise ValueError("State '%s' is not a registered state." % state)
        return self.states[state]

    # In theory this function could be static. This however causes some issues related to inheritance and
    # pickling down the chain.
    def is_state(self, state, model):
        """ Check whether the current state matches the named state. This function is not called directly
            but assigned as partials to model instances (e.g. is_A -> partial(_is_state, 'A', model)).
        Args:
            state (str): name of the checked state
            model: model to be checked
        Returns:
            bool: Whether the model's current state is state.
        """
        return getattr(model, self.model_attribute) == state

    def get_model_state(self, model):
        return self.get_state(getattr(model, self.model_attribute))

    def set_state(self, state, model=None):
        """
            Set the current state.
        Args:
            state (str or Enum or State): value of state to be set
            model (optional[object]): targeted model; if not set, all models will be set to 'state'
        """
        if not isinstance(state, State):
            state = self.get_state(state)
        models = self.models if model is None else listify(model)

        for mod in models:
            setattr(mod, self.model_attribute, state.value)

    def add_state(self, *args, **kwargs):
        """ Alias for add_states. """
        self.add_states(*args, **kwargs)

    def add_states(self, states, on_enter=None, on_exit=None,
                   ignore_invalid_triggers=None, **kwargs):
        """ Add new state(s).
        Args:
            states (list, str, dict, Enum or State): a list, a State instance, the
                name of a new state, an enumeration (member) or a dict with keywords to pass on to the
                State initializer. If a list, each element can be a string, State or enumeration member.
            on_enter (str or list): callbacks to trigger when the state is
                entered. Only valid if first argument is string.
            on_exit (str or list): callbacks to trigger when the state is
                exited. Only valid if first argument is string.
            ignore_invalid_triggers: when True, any calls to trigger methods
                that are not valid for the present state (e.g., calling an
                a_to_b() trigger when the current state is c) will be silently
                ignored rather than raising an invalid transition exception.
                Note that this argument takes precedence over the same
                argument defined at the Machine level, and is in turn
                overridden by any ignore_invalid_triggers explicitly
                passed in an individual state's initialization arguments.

            **kwargs additional keyword arguments used by state mixins.
        """

        ignore = ignore_invalid_triggers
        if ignore is None:
            ignore = self.ignore_invalid_triggers

        states = listify(states)

        for state in states:
            if isinstance(state, (string_types, Enum)):
                state = self._create_state(
                    state, on_enter=on_enter, on_exit=on_exit,
                    ignore_invalid_triggers=ignore, **kwargs)
            elif isinstance(state, dict):
                if 'ignore_invalid_triggers' not in state:
                    state['ignore_invalid_triggers'] = ignore
                state = self._create_state(**state)
            self.states[state.name] = state
            for model in self.models:
                self._add_model_to_state(state, model)
            if self.auto_transitions:
                for a_state in self.states.keys():
                    # add all states as sources to auto transitions 'to_<state>' with dest <state>
                    if a_state == state.name:
                        if self.model_attribute == 'state':
                            method_name = 'to_%s' % a_state
                        else:
                            method_name = 'to_%s_%s' % (self.model_attribute, a_state)
                            self.add_transition('to_%s' % a_state, self.wildcard_all, a_state,
                                                prepare=partial(_warning_wrapper_to, 'to_%s' % a_state))
                        self.add_transition(method_name, self.wildcard_all, a_state)

                    # add auto transition with source <state> to <a_state>
                    else:
                        if self.model_attribute == 'state':
                            method_name = 'to_%s' % a_state
                        else:
                            method_name = 'to_%s_%s' % (self.model_attribute, a_state)
                            self.add_transition('to_%s' % a_state, state.name, a_state,
                                                prepare=partial(_warning_wrapper_to, 'to_%s' % a_state))
                        self.add_transition(method_name, state.name, a_state)

    def _add_model_to_state(self, state, model):
        # Add convenience function 'is_<state_name>' (e.g. 'is_A') to the model.
        # When model_attribute has been customized, add 'is_<model_attribute>_<state_name>' instead
        # to potentially support multiple states on one model (e.g. 'is_custom_state_A' and 'is_my_state_B').

        func = partial(self.is_state, state.value, model)
        if self.model_attribute == 'state':
            method_name = 'is_%s' % state.name
        else:
            method_name = 'is_%s_%s' % (self.model_attribute, state.name)
            self._checked_assignment(model, 'is_%s' % state.name, partial(_warning_wrapper_is, method_name, func))
        self._checked_assignment(model, method_name, func)

        # Add dynamic method callbacks (enter/exit) if there are existing bound methods in the model
        # except if they are already mentioned in 'on_enter/exit' of the defined state
        for callback in self.state_cls.dynamic_methods:
            method = "{0}_{1}".format(callback, state.name)
            if hasattr(model, method) and inspect.ismethod(getattr(model, method)) and \
                    method not in getattr(state, callback):
                state.add_callback(callback[3:], method)

    def _checked_assignment(self, model, name, func):
        if hasattr(model, name):
            _LOGGER.warning("%sModel already contains an attribute '%s'. Skip binding.", self.name, name)
        else:
            setattr(model, name, func)

    def _add_trigger_to_model(self, trigger, model):
        self._checked_assignment(model, trigger, partial(self.events[trigger].trigger, model))

    def _get_trigger(self, model, trigger_name, *args, **kwargs):
        """Convenience function added to the model to trigger events by name.
        Args:
            model (object): Model with assigned event trigger.
            trigger_name (str): Name of the trigger to be called.
            *args: Variable length argument list which is passed to the triggered event.
            **kwargs: Arbitrary keyword arguments which is passed to the triggered event.
        Returns:
            bool: True if a transitions has been conducted or the trigger event has been queued.
        """
        try:
            event = self.events[trigger_name]
        except KeyError:
            state = self.get_model_state(model)
            ignore = state.ignore_invalid_triggers if state.ignore_invalid_triggers is not None \
                else self.ignore_invalid_triggers
            if not ignore:
                raise AttributeError("Do not know event named '%s'." % trigger_name)
            return False
        return event.trigger(model, *args, **kwargs)

    def get_triggers(self, *args):
        """ Collects all triggers FROM certain states.
        Args:
            *args: Tuple of source states.

        Returns:
            list of transition/trigger names.
        """
        names = set([state.name if hasattr(state, 'name') else state for state in args])
        return [t for (t, ev) in self.events.items() if any(name in ev.transitions for name in names)]

    def add_transition(self, trigger, source, dest, conditions=None,
                       unless=None, before=None, after=None, prepare=None, **kwargs):
        """ Create a new Transition instance and add it to the internal list.
        Args:
            trigger (str): The name of the method that will trigger the
                transition. This will be attached to the currently specified
                model (e.g., passing trigger='advance' will create a new
                advance() method in the model that triggers the transition.)
            source(str or list): The name of the source state--i.e., the state we
                are transitioning away from. This can be a single state, a
                list of states or an asterisk for all states.
            dest (str): The name of the destination State--i.e., the state
                we are transitioning into. This can be a single state or an
                equal sign to specify that the transition should be reflexive
                so that the destination will be the same as the source for
                every given source. If dest is None, this transition will be
                an internal transition (exit/enter callbacks won't be processed).
            conditions (str or list): Condition(s) that must pass in order
                for the transition to take place. Either a list providing the
                name of a callable, or a list of callables. For the transition
                to occur, ALL callables must return True.
            unless (str or list): Condition(s) that must return False in order
                for the transition to occur. Behaves just like conditions arg
                otherwise.
            before (str or list): Callables to call before the transition.
            after (str or list): Callables to call after the transition.
            prepare (str or list): Callables to call when the trigger is activated
            **kwargs: Additional arguments which can be passed to the created transition.
                This is useful if you plan to extend Machine.Transition and require more parameters.
        """
        if trigger == self.model_attribute:
            raise ValueError("Trigger name cannot be same as model attribute name.")
        if trigger not in self.events:
            self.events[trigger] = self._create_event(trigger, self)
            for model in self.models:
                self._add_trigger_to_model(trigger, model)

        if source == self.wildcard_all:
            source = list(self.states.keys())
        else:
            # states are checked lazily which means we will only raise exceptions when the passed state
            # is a State object because of potential confusion (see issue #155 for more details)
            source = [s.name if isinstance(s, State) and self._has_state(s, raise_error=True) or hasattr(s, 'name') else
                      s for s in listify(source)]

        for state in source:
            if dest == self.wildcard_same:
                _dest = state
            elif dest is not None:
                if isinstance(dest, State):
                    _ = self._has_state(dest, raise_error=True)
                _dest = dest.name if hasattr(dest, 'name') else dest
            else:
                _dest = None
            _trans = self._create_transition(state, _dest, conditions, unless, before,
                                             after, prepare, **kwargs)
            self.events[trigger].add_transition(_trans)

    def add_transitions(self, transitions):
        """ Add several transitions.

        Args:
            transitions (list): A list of transitions.

        """
        for trans in listify(transitions):
            if isinstance(trans, list):
                self.add_transition(*trans)
            else:
                self.add_transition(**trans)

    def add_ordered_transitions(self, states=None, trigger='next_state',
                                loop=True, loop_includes_initial=True,
                                conditions=None, unless=None, before=None,
                                after=None, prepare=None, **kwargs):
        """ Add a set of transitions that move linearly from state to state.
        Args:
            states (list): A list of state names defining the order of the
                transitions. E.g., ['A', 'B', 'C'] will generate transitions
                for A --> B, B --> C, and C --> A (if loop is True). If states
                is None, all states in the current instance will be used.
            trigger (str): The name of the trigger method that advances to
                the next state in the sequence.
            loop (boolean): Whether or not to add a transition from the last
                state to the first state.
            loop_includes_initial (boolean): If no initial state was defined in
                the machine, setting this to True will cause the _initial state
                placeholder to be included in the added transitions. This argument
                has no effect if the states argument is passed without the
                initial state included.
            conditions (str or list): Condition(s) that must pass in order
                for the transition to take place. Either a list providing the
                name of a callable, or a list of callables. For the transition
                to occur, ALL callables must return True.
            unless (str or list): Condition(s) that must return False in order
                for the transition to occur. Behaves just like conditions arg
                otherwise.
            before (str or list): Callables to call before the transition.
            after (str or list): Callables to call after the transition.
            prepare (str or list): Callables to call when the trigger is activated
            **kwargs: Additional arguments which can be passed to the created transition.
                This is useful if you plan to extend Machine.Transition and require more parameters.
        """
        if states is None:
            states = list(self.states.keys())  # need to listify for Python3
        len_transitions = len(states)
        if len_transitions < 2:
            raise ValueError("Can't create ordered transitions on a Machine "
                             "with fewer than 2 states.")
        if not loop:
            len_transitions -= 1
        # ensure all args are the proper length
        conditions = _prep_ordered_arg(len_transitions, conditions)
        unless = _prep_ordered_arg(len_transitions, unless)
        before = _prep_ordered_arg(len_transitions, before)
        after = _prep_ordered_arg(len_transitions, after)
        prepare = _prep_ordered_arg(len_transitions, prepare)
        # reorder list so that the initial state is actually the first one
        try:
            idx = states.index(self._initial)
            states = states[idx:] + states[:idx]
            first_in_loop = states[0 if loop_includes_initial else 1]
        except ValueError:
            # since initial is not part of states it shouldn't be part of the loop either
            first_in_loop = states[0]

        for i in range(0, len(states) - 1):
            self.add_transition(trigger, states[i], states[i + 1],
                                conditions=conditions[i],
                                unless=unless[i],
                                before=before[i],
                                after=after[i],
                                prepare=prepare[i],
                                **kwargs)
        if loop:
            self.add_transition(trigger, states[-1],
                                # omit initial if not loop_includes_initial
                                first_in_loop,
                                conditions=conditions[-1],
                                unless=unless[-1],
                                before=before[-1],
                                after=after[-1],
                                prepare=prepare[-1],
                                **kwargs)

    def get_transitions(self, trigger="", source="*", dest="*"):
        """ Return the transitions from the Machine.
        Args:
            trigger (str): Trigger name of the transition.
            source (str, Enum or State): Limits list to transitions from a certain state.
            dest (str, Enum or State): Limits list to transitions to a certain state.
        """
        if trigger:
            try:
                events = (self.events[trigger], )
            except KeyError:
                return []
        else:
            events = self.events.values()
        transitions = []
        for event in events:
            transitions.extend(
                itertools.chain.from_iterable(event.transitions.values()))
        target_source = source.name if hasattr(source, 'name') else source if source != "*" else ""
        target_dest = dest.name if hasattr(dest, 'name') else dest if dest != "*" else ""
        return [transition
                for transition in transitions
                if (transition.source, transition.dest) == (target_source or transition.source,
                                                            target_dest or transition.dest)]

    def remove_transition(self, trigger, source="*", dest="*"):
        """ Removes a transition from the Machine and all models.
        Args:
            trigger (str): Trigger name of the transition.
            source (str): Limits removal to transitions from a certain state.
            dest (str): Limits removal to transitions to a certain state.
        """
        source = listify(source) if source != "*" else source
        dest = listify(dest) if dest != "*" else dest
        # outer comprehension, keeps events if inner comprehension returns lists with length > 0
        tmp = {key: value for key, value in
               {k: [t for t in v
                    # keep entries if source should not be filtered; same for dest.
                    if (source != "*" and t.source not in source) or (dest != "*" and t.dest not in dest)]
                   # }.items() takes the result of the inner comprehension and uses it
                   # for the outer comprehension (see first line of comment)
                for k, v in self.events[trigger].transitions.items()}.items()
               if len(value) > 0}
        # convert dict back to defaultdict in case tmp is not empty
        if tmp:
            self.events[trigger].transitions = defaultdict(list, **tmp)
        # if no transition is left remove the trigger from the machine and all models
        else:
            for model in self.models:
                delattr(model, trigger)
            del self.events[trigger]

    def dispatch(self, trigger, *args, **kwargs):
        """ Trigger an event on all models assigned to the machine.
        Args:
            trigger (str): Event name
            *args (list): List of arguments passed to the event trigger
            **kwargs (dict): Dictionary of keyword arguments passed to the event trigger
        Returns:
            bool The truth value of all triggers combined with AND
        """
        return all([getattr(model, trigger)(*args, **kwargs) for model in self.models])

    def callbacks(self, funcs, event_data):
        """ Triggers a list of callbacks """
        for func in funcs:
            self.callback(func, event_data)
            _LOGGER.info("%sExecuted callback '%s'", self.name, func)

    def callback(self, func, event_data):
        """ Trigger a callback function with passed event_data parameters. In case func is a string,
            the callable will be resolved from the passed model in event_data. This function is not intended to
            be called directly but through state and transition callback definitions.
        Args:
            func (str or callable): The callback function.
                1. First, if the func is callable, just call it
                2. Second, we try to import string assuming it is a path to a func
                3. Fallback to a model attribute
            event_data (EventData): An EventData instance to pass to the
                callback (if event sending is enabled) or to extract arguments
                from (if event sending is disabled).
        """

        func = self.resolve_callable(func, event_data)
        if self.send_event:
            func(event_data)
        else:
            func(*event_data.args, **event_data.kwargs)

    @staticmethod
    def resolve_callable(func, event_data):
        """ Converts a model's property name, method name or a path to a callable into a callable.
            If func is not a string it will be returned unaltered.
        Args:
            func (str or callable): Property name, method name or a path to a callable
            event_data (EventData): Currently processed event
        Returns:
            callable function resolved from string or func
        """
        if isinstance(func, string_types):
            try:
                func = getattr(event_data.model, func)
                if not callable(func):  # if a property or some other not callable attribute was passed
                    def func_wrapper(*_, **__):  # properties cannot process parameters
                        return func
                    return func_wrapper
            except AttributeError:
                try:
                    mod, name = func.rsplit('.', 1)
                    m = __import__(mod)
                    for n in mod.split('.')[1:]:
                        m = getattr(m, n)
                    func = getattr(m, name)
                except (ImportError, AttributeError, ValueError):
                    raise AttributeError("Callable with name '%s' could neither be retrieved from the passed "
                                         "model nor imported from a module." % func)
        return func

    def _has_state(self, state, raise_error=False):
        found = state in self.states.values()
        if not found and raise_error:
            msg = 'State %s has not been added to the machine' % (state.name if hasattr(state, 'name') else state)
            raise ValueError(msg)
        return found

    def _process(self, trigger):

        # default processing
        if not self.has_queue:
            if not self._transition_queue:
                # if trigger raises an Error, it has to be handled by the Machine.process caller
                return trigger()
            else:
                raise MachineError("Attempt to process events synchronously while transition queue is not empty!")

        # process queued events
        self._transition_queue.append(trigger)
        # another entry in the queue implies a running transition; skip immediate execution
        if len(self._transition_queue) > 1:
            return True

        # execute as long as transition queue is not empty
        while self._transition_queue:
            try:
                self._transition_queue[0]()
                self._transition_queue.popleft()
            except Exception:
                # if a transition raises an exception, clear queue and delegate exception handling
                self._transition_queue.clear()
                raise
        return True

    @classmethod
    def _identify_callback(cls, name):
        # Does the prefix match a known callback?
        for callback in itertools.chain(cls.state_cls.dynamic_methods, cls.transition_cls.dynamic_methods):
            if name.startswith(callback):
                callback_type = callback
                break
        else:
            return None, None

        # Extract the target by cutting the string after the type and separator
        target = name[len(callback_type) + len(cls.separator):]

        # Make sure there is actually a target to avoid index error and enforce _ as a separator
        if target == '' or name[len(callback_type)] != cls.separator:
            return None, None

        return callback_type, target

    def __getattr__(self, name):
        # Machine.__dict__ does not contain double underscore variables.
        # Class variables will be mangled.
        if name.startswith('__'):
            raise AttributeError("'{}' does not exist on <Machine@{}>"
                                 .format(name, id(self)))

        # Could be a callback
        callback_type, target = self._identify_callback(name)

        if callback_type is not None:
            if callback_type in self.transition_cls.dynamic_methods:
                if target not in self.events:
                    raise AttributeError("event '{}' is not registered on <Machine@{}>"
                                         .format(target, id(self)))
                return partial(self.events[target].add_callback, callback_type)

            elif callback_type in self.state_cls.dynamic_methods:
                state = self.get_state(target)
                return partial(state.add_callback, callback_type[3:])

        try:
            return self.__getattribute__(name)
        except AttributeError:
            # Nothing matched
            raise AttributeError("'{}' does not exist on <Machine@{}>".format(name, id(self)))


class MachineError(Exception):
    """ MachineError is used for issues related to state transitions and current states.
    For instance, it is raised for invalid transitions or machine configuration issues.
    """

    def __init__(self, value):
        super(MachineError, self).__init__(value)
        self.value = value

    def __str__(self):
        return repr(self.value)


# TODO: Remove in 0.9.0
def _warning_wrapper_is(meth_name, func, *args, **kwargs):
    warnings.warn("Starting from transitions version 0.8.3, 'is_<state_name>' convenience functions will be"
                  " assigned to 'is_<model_attribute>_<state_name>' when 'model_attribute "
                  "!= \"state\"'. In 0.9.0, 'is_<state_name>' will NOT be assigned anymore when "
                  "'model_attribute != \"state\"'! Please adjust your code and use "
                  "'{0}' instead.".format(meth_name), DeprecationWarning)
    return func(*args, **kwargs)


def _warning_wrapper_to(meth_name, *args, **kwargs):
    warnings.warn("Starting from transitions version 0.8.3, 'to_<state_name>' convenience functions will be"
                  " assigned to 'to_<model_attribute>_<state_name>' when 'model_attribute "
                  "!= \"state\"'. In 0.9.0, 'to_<state_name>' will NOT be assigned anymore when "
                  "'model_attribute != \"state\"'! Please adjust your code and use "
                  "'{0}' instead.".format(meth_name), DeprecationWarning)
