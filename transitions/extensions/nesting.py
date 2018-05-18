# -*- coding: utf-8 -*-
"""
    transitions.extensions.nesting
    ------------------------------

    Adds the capability to work with nested states also known as hierarchical state machines.
"""

from copy import copy, deepcopy
from functools import partial
import logging
import warnings
from six import string_types

from ..core import Machine, Transition, State, Event, listify, MachineError, EventData

# make deprecation warnings of transition visible for module users
warnings.filterwarnings(action='default', message=r".*transitions version.*")


_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())

# This is a workaround for dill issues when partials and super is used in conjunction
# without it, Python 3.0 - 3.3 will not support pickling
# https://github.com/pytransitions/transitions/issues/236
_super = super


class FunctionWrapper(object):
    """ A wrapper to enable transitions' convenience function to_<state> for nested states.
        This allows to call model.to_A.s1.C() in case a custom separator has been chosen."""
    def __init__(self, func, path):
        """
        Args:
            func: Function to be called at the end of the path.
            path: If path is an empty string, assign function
        """
        if path:
            self.add(func, path)
            self._func = None
        else:
            self._func = func

    def add(self, func, path):
        """ Assigns a `FunctionWrapper` as an attribute named like the next segment of the substates
            path.
        Args:
            func (callable): Function to be called at the end of the path.
            path (string): Remaining segment of the substate path.
        """
        if path:
            name = path[0]
            if name[0].isdigit():
                name = 's' + name
            if hasattr(self, name):
                getattr(self, name).add(func, path[1:])
            else:
                setattr(self, name, FunctionWrapper(func, path[1:]))
        else:
            self._func = func

    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)


class NestedState(State):
    """ A state which allows substates.
    Attributes:
        parent (NestedState): The parent of the current state.
        children (list): A list of child states of the current state.
    """

    separator = '_'
    u""" Separator between the names of parent and child states. In case '_' is required for
        naming state, this value can be set to other values such as '.' or even unicode characters
        such as '↦' (limited to Python 3 though).
    """

    def __init__(self, name, on_enter=None, on_exit=None, ignore_invalid_triggers=None, parent=None, initial=None):
        self._name = name
        self._initial = initial
        self._parent = None
        self.parent = parent
        _super(NestedState, self).__init__(name=name, on_enter=on_enter, on_exit=on_exit,
                                           ignore_invalid_triggers=ignore_invalid_triggers)
        self.children = []

    @property
    def parent(self):
        """ The parent state of this state. """
        return self._parent

    @parent.setter
    def parent(self, value):
        if value is not None:
            self._parent = value
            self._parent.children.append(self)

    @property
    def initial(self):
        """ When this state is entered it will automatically enter
            the child with this name if not None. """
        return self.name + NestedState.separator + self._initial if self._initial else self._initial

    @initial.setter
    def initial(self, value):
        self._initial = value

    @property
    def level(self):
        """ Tracks how deeply nested this state is. This property is calculated from
            the state's parent (+1) or 0 when there is no parent. """
        return self.parent.level + 1 if self.parent is not None else 0

    @property
    def name(self):
        """ The computed name of this state. """
        return (self.parent.name + NestedState.separator + self._name) if self.parent else self._name

    @name.setter
    def name(self, value):
        self._name = value

    def is_substate_of(self, state_name):
        """Check whether this state is a substate of a state named `state_name`
        Args:
            state_name (str): Name of the parent state to be checked

        Returns: bool True when `state_name` is a parent of this state
        """

        temp_state = self
        while not temp_state.name == state_name and temp_state.level > 0:
            temp_state = temp_state.parent
        return temp_state.name == state_name

    def exit_nested(self, event_data, target_state):
        """ Tracks child states to exit when the states is exited itself. This should not
            be triggered by the user but will be handled by the hierarchical machine.
        Args:
            event_data (EventData): Event related data.
            target_state (NestedState): The state to be entered.

        Returns: int level of the currently investigated (sub)state.

        """
        if self == target_state:
            self.exit(event_data)
            return self.level
        elif self.level > target_state.level:
            self.exit(event_data)
            return self.parent.exit_nested(event_data, target_state)
        elif self.level <= target_state.level:
            tmp_state = target_state
            while self.level != tmp_state.level:
                tmp_state = tmp_state.parent
            tmp_self = self
            while tmp_self.level > 0 and tmp_state.parent.name != tmp_self.parent.name:
                tmp_self.exit(event_data)
                tmp_self = tmp_self.parent
                tmp_state = tmp_state.parent
            if tmp_self == tmp_state:
                return tmp_self.level + 1
            tmp_self.exit(event_data)
            return tmp_self.level

    def enter_nested(self, event_data, level=None):
        """ Tracks parent states to be entered when the states is entered itself. This should not
            be triggered by the user but will be handled by the hierarchical machine.
        Args:
            event_data (EventData): Event related data.
            level (int): The level of the currently entered parent.
        """
        if level is not None and level <= self.level:
            if level != self.level:
                self.parent.enter_nested(event_data, level)
            self.enter(event_data)

    # Prevent deep copying of callback lists since these include either references to callables or
    # strings. Deep copying a method reference would lead to the creation of an entire new (model) object
    # (see https://github.com/pytransitions/transitions/issues/248)
    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for key, value in self.__dict__.items():
            if key in cls.dynamic_methods:
                setattr(result, key, copy(value))
            else:
                setattr(result, key, deepcopy(value, memo))
        return result


class NestedTransition(Transition):
    """ A transition which handles entering and leaving nested states.
    Attributes:
        dest (NestedState): The resolved transition destination in respect
            to initial states of nested states.
    """

    def execute(self, event_data):
        """ Extends transitions.core.transitions to handle nested states. """
        if self.dest is None:
            return _super(NestedTransition, self).execute(event_data)
        dest_state = event_data.machine.get_state(self.dest)
        while dest_state.initial:
            dest_state = event_data.machine.get_state(dest_state.initial)
        self.dest = dest_state.name
        return _super(NestedTransition, self).execute(event_data)

    # The actual state change method 'execute' in Transition was restructured to allow overriding
    def _change_state(self, event_data):
        machine = event_data.machine
        model = event_data.model
        dest_state = machine.get_state(self.dest)
        source_state = machine.get_state(model.state)
        lvl = source_state.exit_nested(event_data, dest_state)
        event_data.machine.set_state(self.dest, model)
        event_data.update(model)
        dest_state.enter_nested(event_data, lvl)

    # Prevent deep copying of callback lists since these include either references to callable or
    # strings. Deep copying a method reference would lead to the creation of an entire new (model) object
    # (see https://github.com/pytransitions/transitions/issues/248)
    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for key, value in self.__dict__.items():
            if key in cls.dynamic_methods:
                setattr(result, key, copy(value))
            else:
                setattr(result, key, deepcopy(value, memo))
        return result


class NestedEvent(Event):
    """ An event type to work with nested states. """

    def _trigger(self, model, *args, **kwargs):
        state = self.machine.get_state(model.state)
        while state.parent and state.name not in self.transitions:
            state = state.parent
        if state.name not in self.transitions:
            msg = "%sCan't trigger event %s from state %s!" % (self.machine.name, self.name,
                                                               model.state)
            if self.machine.get_state(model.state).ignore_invalid_triggers:
                _LOGGER.warning(msg)
            else:
                raise MachineError(msg)
        event_data = EventData(state, self, self.machine,
                               model, args=args, kwargs=kwargs)
        return self._process(event_data)


class HierarchicalMachine(Machine):
    """ Extends transitions.core.Machine by capabilities to handle nested states.
        A hierarchical machine REQUIRES NestedStates (or any subclass of it) to operate.
    """

    state_cls = NestedState
    transition_cls = NestedTransition
    event_cls = NestedEvent

    def __init__(self, *args, **kwargs):
        self._buffered_transitions = []
        _super(HierarchicalMachine, self).__init__(*args, **kwargs)

    @Machine.initial.setter
    def initial(self, value):
        if isinstance(value, NestedState):
            if value.name not in self.states:
                self.add_state(value)
            else:
                assert self._has_state(value)
            state = value
        else:
            if value not in self.states:
                self.add_state(value)
            state = self.get_state(value)
        if state.initial:
            self.initial = state.initial
        else:
            self._initial = state.name

    def add_model(self, model, initial=None):
        """ Extends transitions.core.Machine.add_model by applying a custom 'to' function to
            the added model.
        """
        _super(HierarchicalMachine, self).add_model(model, initial=initial)
        models = listify(model)
        for mod in models:
            mod = self if mod == 'self' else mod
            # TODO: Remove 'mod != self' in 0.7.0
            if hasattr(mod, 'to') and mod != self:
                _LOGGER.warning("%sModel already has a 'to'-method. It will NOT "
                                "be overwritten by NestedMachine", self.name)
            else:
                to_func = partial(self.to_state, mod)
                setattr(mod, 'to', to_func)

    def is_state(self, state_name, model, allow_substates=False):
        """ Extends transitions.core.Machine.is_state with an additional parameter (allow_substates)
            to
        Args:
            state_name (str): Name of the checked state.
            model (class): The model to be investigated.
            allow_substates (bool): Whether substates should be allowed or not.

        Returns: bool Whether the passed model is in queried state (or a substate of it) or not.

        """
        if not allow_substates:
            return model.state == state_name

        return self.get_state(model.state).is_substate_of(state_name)

    def _traverse(self, states, on_enter=None, on_exit=None,
                  ignore_invalid_triggers=None, parent=None, remap=None):
        """ Parses passed value to build a nested state structure recursively.
        Args:
            states (list, string, dict, or State): a list, a State instance, the
                name of a new state, or a dict with keywords to pass on to the
                State initializer. If a list, each element can be of any of the
                latter three types.
            on_enter (string or list): callbacks to trigger when the state is
                entered. Only valid if first argument is string.
            on_exit (string or list): callbacks to trigger when the state is
                exited. Only valid if first argument is string.
            ignore_invalid_triggers: when True, any calls to trigger methods
                that are not valid for the present state (e.g., calling an
                a_to_b() trigger when the current state is c) will be silently
                ignored rather than raising an invalid transition exception.
                Note that this argument takes precedence over the same
                argument defined at the Machine level, and is in turn
                overridden by any ignore_invalid_triggers explicitly
                passed in an individual state's initialization arguments.
            parent (NestedState or string): parent state for nested states.
            remap (dict): reassigns transitions named `key from nested machines to parent state `value`.
        Returns: list of new `NestedState` objects
        """
        states = listify(states)
        new_states = []
        ignore = ignore_invalid_triggers
        remap = {} if remap is None else remap
        parent = self.get_state(parent) if isinstance(parent, string_types) else parent

        if ignore is None:
            ignore = self.ignore_invalid_triggers
        for state in states:
            tmp_states = []
            # other state representations are handled almost like in the base class but a parent parameter is added
            if isinstance(state, string_types):
                if state in remap:
                    continue
                tmp_states.append(self._create_state(state, on_enter=on_enter, on_exit=on_exit, parent=parent,
                                                     ignore_invalid_triggers=ignore))
            elif isinstance(state, dict):
                if state['name'] in remap:
                    continue

                # shallow copy the dictionary to alter/add some parameters
                state = copy(state)
                if 'ignore_invalid_triggers' not in state:
                    state['ignore_invalid_triggers'] = ignore
                if 'parent' not in state:
                    state['parent'] = parent

                try:
                    state_children = state.pop('children')  # throws KeyError when no children set
                    state_remap = state.pop('remap', None)
                    state_parent = self._create_state(**state)
                    nested = self._traverse(state_children, parent=state_parent, remap=state_remap)
                    tmp_states.append(state_parent)
                    tmp_states.extend(nested)
                except KeyError:
                    tmp_states.insert(0, self._create_state(**state))
            elif isinstance(state, HierarchicalMachine):
                # set initial state of parent if it is None
                if parent.initial is None:
                    parent.initial = state.initial
                # (deep) copy only states not mentioned in remap
                copied_states = [s for s in deepcopy(state.states).values() if s.name not in remap]
                # inner_states are the root states of the passed machine
                # which have be attached to the parent
                inner_states = [s for s in copied_states if s.level == 0]
                for inner in inner_states:
                    inner.parent = parent
                tmp_states.extend(copied_states)
                for trigger, event in state.events.items():
                    if trigger.startswith('to_'):
                        path = trigger[3:].split(NestedState.separator)
                        # do not copy auto_transitions since they would not be valid anymore;
                        # trigger and destination do not exist in the new environment
                        if path[0] in remap:
                            continue
                        ppath = parent.name.split(NestedState.separator)
                        path = ['to_' + ppath[0]] + ppath[1:] + path
                        trigger = '.'.join(path)
                    # (deep) copy transitions and
                    # adjust all transition start and end points to new state names
                    for transitions in deepcopy(event.transitions).values():
                        for transition in transitions:
                            src = transition.source
                            # transitions from remapped states will be filtered to prevent
                            # unexpected behaviour in the parent machine
                            if src in remap:
                                continue
                            dst = parent.name + NestedState.separator + transition.dest\
                                if transition.dest not in remap else remap[transition.dest]
                            conditions, unless = [], []
                            for cond in transition.conditions:
                                # split a list in two lists based on the accessors (cond.target) truth value
                                (unless, conditions)[cond.target].append(cond.func)
                            self._buffered_transitions.append({'trigger': trigger,
                                                               'source': parent.name + NestedState.separator + src,
                                                               'dest': dst,
                                                               'conditions': conditions,
                                                               'unless': unless,
                                                               'prepare': transition.prepare,
                                                               'before': transition.before,
                                                               'after': transition.after})

            elif isinstance(state, NestedState):
                tmp_states.append(state)
                if state.children:
                    tmp_states.extend(self._traverse(state.children, on_enter=on_enter, on_exit=on_exit,
                                                     ignore_invalid_triggers=ignore_invalid_triggers,
                                                     parent=state, remap=remap))
            else:
                raise ValueError("%s is not an instance or subclass of NestedState "
                                 "required by HierarchicalMachine." % state)
            new_states.extend(tmp_states)

        duplicate_check = []
        for new in new_states:
            if new.name in duplicate_check:
                # collect state names for the following error message
                state_names = [s.name for s in new_states]
                raise ValueError("State %s cannot be added since it is already in state list %s."
                                 % (new.name, state_names))
            else:
                duplicate_check.append(new.name)
        return new_states

    def add_states(self, states, on_enter=None, on_exit=None,
                   ignore_invalid_triggers=None, **kwargs):
        """ Extends transitions.core.Machine.add_states by calling traverse to parse possible
            substates first."""
        # preprocess states to flatten the configuration and resolve nesting
        new_states = self._traverse(states, on_enter=on_enter, on_exit=on_exit,
                                    ignore_invalid_triggers=ignore_invalid_triggers, **kwargs)
        _super(HierarchicalMachine, self).add_states(new_states, on_enter=on_enter, on_exit=on_exit,
                                                     ignore_invalid_triggers=ignore_invalid_triggers,
                                                     **kwargs)

        while self._buffered_transitions:
            args = self._buffered_transitions.pop()
            self.add_transition(**args)

    def get_triggers(self, *args):
        """ Extends transitions.core.Machine.get_triggers to also include parent state triggers. """
        # add parents to state set
        states = []
        for state_name in args:
            state = self.get_state(state_name)
            while state.parent:
                states.append(state.parent.name)
                state = state.parent
        states.extend(args)
        return _super(HierarchicalMachine, self).get_triggers(*states)

    def _add_trigger_to_model(self, trigger, model):
        # FunctionWrappers are only necessary if a custom separator is used
        if trigger.startswith('to_') and NestedState.separator != '_':
            path = trigger[3:].split(NestedState.separator)
            trig_func = partial(self.events[trigger].trigger, model)
            if hasattr(model, 'to_' + path[0]):
                # add path to existing function wrapper
                getattr(model, 'to_' + path[0]).add(trig_func, path[1:])
            else:
                # create a new function wrapper
                setattr(model, 'to_' + path[0], FunctionWrapper(trig_func, path[1:]))
        else:
            _super(HierarchicalMachine, self)._add_trigger_to_model(trigger, model)  # pylint: disable=protected-access

    def on_enter(self, state_name, callback):
        """ Helper function to add callbacks to states in case a custom state separator is used.
        Args:
            state_name (str): Name of the state
            callback (str or callable): Function to be called. Strings will be resolved to model functions.
        """
        self.get_state(state_name).add_callback('enter', callback)

    def on_exit(self, state_name, callback):
        """ Helper function to add callbacks to states in case a custom state separator is used.
        Args:
            state_name (str): Name of the state
            callback (str or callable): Function to be called. Strings will be resolved to model functions.
        """
        self.get_state(state_name).add_callback('exit', callback)

    def to_state(self, model, state_name, *args, **kwargs):
        """ Helper function to add go to states in case a custom state separator is used.
        Args:
            model (class): The model that should be used.
            state_name (str): Name of the destination state.
        """

        # TODO: Remove in 0.7.0
        if not isinstance(state_name, string_types):
            warnings.warn("'HierarchicalMachine.to' has been renamed to 'HierarchicalMachine.to_state' and "
                          "will be removed in transitions version 0.7.0.", DeprecationWarning)
            model = state_name
            state_name = args[0]
            args = tuple(x for idx, x in enumerate(args) if idx > 0)

        event = EventData(self.get_state(model.state), Event('to', self), self,
                          model, args=args, kwargs=kwargs)
        self._create_transition(model.state, state_name).execute(event)

    # TODO: Remove in 0.7.0
    def to(self, model, state_name, *args, **kwargs):
        """ DEPRECATED! See `to_state` instead """
        warnings.warn("'HierarchicalMachine.to' has been renamed to 'HierarchicalMachine.to_state' and "
                      "will be removed in transitions version 0.7.0.", DeprecationWarning)
        self.to_state(model, state_name, *args, **kwargs)
