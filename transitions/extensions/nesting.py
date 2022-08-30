# -*- coding: utf-8 -*-
"""
    transitions.extensions.nesting
    ------------------------------

    Implements a hierarchical state machine based on transitions.core.Machine. Supports nested states, parallel states
    and the composition of multiple hierarchical state machines.
"""

from collections import OrderedDict
import copy
from functools import partial, reduce
import inspect
import logging

try:
    # Enums are supported for Python 3.4+ and Python 2.7 with enum34 package installed
    from enum import Enum, EnumMeta
except ImportError:
    # If enum is not available, create dummy classes for type checks
    class Enum:  # type: ignore
        """ This is just an Enum stub for Python 2 and Python 3.3 and before without Enum support. """

    class EnumMeta:  # type: ignore
        """ This is just an EnumMeta stub for Python 2 and Python 3.3 and before without Enum support. """

from six import string_types

from ..core import State, Machine, Transition, Event, listify, MachineError, EventData

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())


# converts a hierarchical tree into a list of current states
def _build_state_list(state_tree, separator, prefix=None):
    prefix = prefix or []
    res = []
    for key, value in state_tree.items():
        if value:
            res.append(_build_state_list(value, separator, prefix=prefix + [key]))
        else:
            res.append(separator.join(prefix + [key]))
    return res if len(res) > 1 else res[0]


def resolve_order(state_tree):
    """ Converts a (model) state tree into a list of state paths. States are ordered in the way in which states
    should be visited to process the event correctly (Breadth-first). This makes sure that ALL children are evaluated
    before parents in parallel states.
    Args:
        state_tree (dict): A dictionary representation of the model's state.
    Returns:
        list of lists of str representing the order of states to be processed.
    """
    queue = []
    res = []
    prefix = []
    while True:
        for state_name in reversed(list(state_tree.keys())):
            scope = prefix + [state_name]
            res.append(scope)
            if state_tree[state_name]:
                queue.append((scope, state_tree[state_name]))
        if not queue:
            break
        prefix, state_tree = queue.pop(0)
    return reversed(res)


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
            path (list of strings): Remaining segment of the substate path.
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


class NestedEvent(Event):
    """ An event type to work with nested states.
        This subclass is NOT compatible with simple Machine instances.
    """

    def trigger(self, model, *args, **kwargs):
        raise RuntimeError("NestedEvent.trigger must not be called directly. Call Machine.trigger_event instead.")

    def trigger_nested(self, event_data):
        """ Executes all transitions that match the current state,
        halting as soon as one successfully completes.
        It is up to the machine's configuration of the Event whether processing happens queued (sequentially) or
        whether further Events are processed as they occur. NOTE: This should only
        be called by HierarchicalMachine instances.
        Args:
            event_data (NestedEventData): The currently processed event
        Returns: boolean indicating whether or not a transition was
            successfully executed (True if successful, False if not).
        """
        machine = event_data.machine
        model = event_data.model
        state_tree = machine.build_state_tree(getattr(model, machine.model_attribute), machine.state_cls.separator)
        state_tree = reduce(dict.get, machine.get_global_name(join=False), state_tree)
        ordered_states = resolve_order(state_tree)
        done = set()
        event_data.event = self
        for state_path in ordered_states:
            state_name = machine.state_cls.separator.join(state_path)
            if state_name not in done and state_name in self.transitions:
                event_data.state = machine.get_state(state_name)
                event_data.source_name = state_name
                event_data.source_path = copy.copy(state_path)
                self._process(event_data)
                if event_data.result:
                    elems = state_path
                    while elems:
                        done.add(machine.state_cls.separator.join(elems))
                        elems.pop()
        return event_data.result

    def _process(self, event_data):
        machine = event_data.machine
        machine.callbacks(event_data.machine.prepare_event, event_data)
        _LOGGER.debug("%sExecuted machine preparation callbacks before conditions.", machine.name)
        for trans in self.transitions[event_data.source_name]:
            event_data.transition = trans
            event_data.result = trans.execute(event_data)
            if event_data.result:
                break


class NestedEventData(EventData):
    """ Collection of relevant data related to the ongoing nested transition attempt. """

    def __init__(self, state, event, machine, model, args, kwargs):
        super(NestedEventData, self).__init__(state, event, machine, model, args, kwargs)
        self.source_path = None
        self.source_name = None


class NestedState(State):
    """ A state which allows substates.
    Attributes:
        states (OrderedDict): A list of substates of the current state.
        events (dict): A list of events defined for the nested state.
        initial (list, str, NestedState or Enum): (Name of a) child or list of children that should be entered when the
        state is entered.
    """

    separator = '_'
    u""" Separator between the names of parent and child states. In case '_' is required for
        naming state, this value can be set to other values such as '.' or even unicode characters
        such as '↦' (limited to Python 3 though).
    """

    def __init__(self, name, on_enter=None, on_exit=None, ignore_invalid_triggers=None, initial=None):
        super(NestedState, self).__init__(name=name, on_enter=on_enter, on_exit=on_exit,
                                          ignore_invalid_triggers=ignore_invalid_triggers)
        self.initial = initial
        self.events = {}
        self.states = OrderedDict()
        self._scope = []

    def add_substate(self, state):
        """ Adds a state as a substate.
        Args:
            state (NestedState): State to add to the current state.
        """
        self.add_substates(state)

    def add_substates(self, states):
        """ Adds a list of states to the current state.
        Args:
            states (list): List of state to add to the current state.
        """
        for state in listify(states):
            self.states[state.name] = state

    def scoped_enter(self, event_data, scope=None):
        """ Enters a state with the provided scope.
        Args:
            event_data (NestedEventData): The currently processed event.
            scope (list(str)): Names of the state's parents starting with the top most parent.
        """
        self._scope = scope or []
        try:
            self.enter(event_data)
        finally:
            self._scope = []

    def scoped_exit(self, event_data, scope=None):
        """ Exits a state with the provided scope.
        Args:
            event_data (NestedEventData): The currently processed event.
            scope (list(str)): Names of the state's parents starting with the top most parent.
        """
        self._scope = scope or []
        try:
            self.exit(event_data)
        finally:
            self._scope = []

    @property
    def name(self):
        return self.separator.join(self._scope + [super(NestedState, self).name])


class NestedTransition(Transition):
    """ A transition which handles entering and leaving nested states. """

    def _resolve_transition(self, event_data):
        dst_name_path = self.dest.split(event_data.machine.state_cls.separator)
        _ = event_data.machine.get_state(dst_name_path)
        state_tree = event_data.machine.build_state_tree(
            listify(getattr(event_data.model, event_data.machine.model_attribute)),
            event_data.machine.state_cls.separator)

        scope = event_data.machine.get_global_name(join=False)
        tmp_tree = state_tree.get(dst_name_path[0], None)
        root = []
        while tmp_tree is not None:
            root.append(dst_name_path.pop(0))
            tmp_tree = tmp_tree.get(dst_name_path[0], None) if len(dst_name_path) > 0 else None

        # when destination is empty this means we are already in the state we want to enter
        # we deal with a reflexive transition here as internal transitions have been already dealt with
        # the 'root' of src and dest will be set to the parent and dst (and src) substate will be set as destination
        if not dst_name_path:
            dst_name_path = [root.pop()]

        scoped_tree = reduce(dict.get, scope + root, state_tree)

        exit_partials = [partial(event_data.machine.get_state(root + state_name).scoped_exit,
                                 event_data, scope + root + state_name[:-1])
                         for state_name in resolve_order(scoped_tree)]
        if dst_name_path:
            new_states, enter_partials = self._enter_nested(root, dst_name_path, scope + root, event_data)
        else:
            new_states, enter_partials = {}, []

        scoped_tree.clear()
        for new_key, value in new_states.items():
            scoped_tree[new_key] = value
            break

        return state_tree, exit_partials, enter_partials

    def _change_state(self, event_data):
        state_tree, exit_partials, enter_partials = self._resolve_transition(event_data)
        for func in exit_partials:
            func()
        self._update_model(event_data, state_tree)
        for func in enter_partials:
            func()

    def _enter_nested(self, root, dest, prefix_path, event_data):
        if root:
            state_name = root.pop(0)
            with event_data.machine(state_name):
                return self._enter_nested(root, dest, prefix_path, event_data)
        elif dest:
            new_states = OrderedDict()
            state_name = dest.pop(0)
            with event_data.machine(state_name):
                new_states[state_name], new_enter = self._enter_nested([], dest, prefix_path + [state_name], event_data)
                enter_partials = [partial(event_data.machine.scoped.scoped_enter, event_data, prefix_path)] + new_enter
            return new_states, enter_partials
        elif event_data.machine.scoped.initial:
            new_states = OrderedDict()
            enter_partials = []
            queue = []
            prefix = prefix_path
            scoped_tree = new_states
            initial_names = [i.name if hasattr(i, 'name') else i for i in listify(event_data.machine.scoped.initial)]
            initial_states = [event_data.machine.scoped.states[n] for n in initial_names]
            while True:
                event_data.scope = prefix
                for state in initial_states:
                    enter_partials.append(partial(state.scoped_enter, event_data, prefix))
                    scoped_tree[state.name] = OrderedDict()
                    if state.initial:
                        queue.append((scoped_tree[state.name], prefix + [state.name],
                                     [state.states[i.name] if hasattr(i, 'name') else state.states[i]
                                     for i in listify(state.initial)]))
                if not queue:
                    break
                scoped_tree, prefix, initial_states = queue.pop(0)
            return new_states, enter_partials
        else:
            return {}, []

    @staticmethod
    def _update_model(event_data, tree):
        model_states = _build_state_list(tree, event_data.machine.state_cls.separator)
        with event_data.machine():
            event_data.machine.set_state(model_states, event_data.model)
            states = event_data.machine.get_states(listify(model_states))
            event_data.state = states[0] if len(states) == 1 else states

    # Prevent deep copying of callback lists since these include either references to callable or
    # strings. Deep copying a method reference would lead to the creation of an entire new (model) object
    # (see https://github.com/pytransitions/transitions/issues/248)
    # Note: When conditions are handled like other dynamic callbacks the key == "conditions" clause can be removed
    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for key, value in self.__dict__.items():
            if key in cls.dynamic_methods or key == "conditions":
                setattr(result, key, copy.copy(value))
            else:
                setattr(result, key, copy.deepcopy(value, memo))
        return result


class HierarchicalMachine(Machine):
    """ Extends transitions.core.Machine by capabilities to handle nested states.
        A hierarchical machine REQUIRES NestedStates, NestedEvent and NestedTransitions
        (or any subclass of it) to operate.
    """

    state_cls = NestedState
    transition_cls = NestedTransition
    event_cls = NestedEvent

    def __init__(self, model=Machine.self_literal, states=None, initial='initial', transitions=None,
                 send_event=False, auto_transitions=True,
                 ordered_transitions=False, ignore_invalid_triggers=None,
                 before_state_change=None, after_state_change=None, name=None,
                 queued=False, prepare_event=None, finalize_event=None, model_attribute='state', on_exception=None,
                 **kwargs):
        assert issubclass(self.state_cls, NestedState)
        assert issubclass(self.event_cls, NestedEvent)
        assert issubclass(self.transition_cls, NestedTransition)
        self._stack = []
        self.prefix_path = []
        self.scoped = self
        self._next_scope = None
        super(HierarchicalMachine, self).__init__(
            model=model, states=states, initial=initial, transitions=transitions,
            send_event=send_event, auto_transitions=auto_transitions,
            ordered_transitions=ordered_transitions, ignore_invalid_triggers=ignore_invalid_triggers,
            before_state_change=before_state_change, after_state_change=after_state_change, name=name,
            queued=queued, prepare_event=prepare_event, finalize_event=finalize_event, model_attribute=model_attribute,
            on_exception=on_exception, **kwargs
        )

    def __call__(self, to_scope=None):
        if isinstance(to_scope, string_types):
            state_name = to_scope.split(self.state_cls.separator)[0]
            state = self.states[state_name]
            to_scope = (state, state.states, state.events, self.prefix_path + [state_name])
        elif isinstance(to_scope, Enum):
            state = self.states[to_scope.name]
            to_scope = (state, state.states, state.events, self.prefix_path + [to_scope.name])
        elif to_scope is None:
            if self._stack:
                to_scope = self._stack[0]
            else:
                to_scope = (self, self.states, self.events, [])
        self._next_scope = to_scope

        return self

    def __enter__(self):
        self._stack.append((self.scoped, self.states, self.events, self.prefix_path))
        self.scoped, self.states, self.events, self.prefix_path = self._next_scope
        self._next_scope = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.scoped, self.states, self.events, self.prefix_path = self._stack.pop()

    def add_model(self, model, initial=None):
        """ Extends transitions.core.Machine.add_model by applying a custom 'to' function to
            the added model.
        """
        models = [self if mod is self.self_literal else mod for mod in listify(model)]
        super(HierarchicalMachine, self).add_model(models, initial=initial)
        initial_name = getattr(models[0], self.model_attribute)
        if hasattr(initial_name, 'name'):
            initial_name = initial_name.name
        # initial states set by add_model or machine might contain initial states themselves.
        if isinstance(initial_name, string_types):
            initial_states = self._resolve_initial(models, initial_name.split(self.state_cls.separator))
        # when initial is set to a (parallel) state, we accept it as it is
        else:
            initial_states = initial_name
        for mod in models:
            self.set_state(initial_states, mod)
            if hasattr(mod, 'to'):
                _LOGGER.warning("%sModel already has a 'to'-method. It will NOT "
                                "be overwritten by NestedMachine", self.name)
            else:
                to_func = partial(self.to_state, mod)
                setattr(mod, 'to', to_func)

    @property
    def initial(self):
        """ Return the initial state. """
        return self._initial

    @initial.setter
    def initial(self, value):
        self._initial = self._recursive_initial(value)

    def add_ordered_transitions(self, states=None, trigger='next_state',
                                loop=True, loop_includes_initial=True,
                                conditions=None, unless=None, before=None,
                                after=None, prepare=None, **kwargs):
        if states is None:
            states = self.get_nested_state_names()
        super(HierarchicalMachine, self).add_ordered_transitions(states=states, trigger=trigger, loop=loop,
                                                                 loop_includes_initial=loop_includes_initial,
                                                                 conditions=conditions,
                                                                 unless=unless, before=before, after=after,
                                                                 prepare=prepare, **kwargs)

    def add_states(self, states, on_enter=None, on_exit=None, ignore_invalid_triggers=None, **kwargs):
        """ Add new nested state(s).
        Args:
            states (list, str, dict, Enum, NestedState or HierarchicalMachine): a list, a NestedState instance, the
                name of a new state, an enumeration (member) or a dict with keywords to pass on to the
                NestedState initializer. If a list, each element can be a string, dict, NestedState or
                enumeration member.
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
        remap = kwargs.pop('remap', None)
        ignore = self.ignore_invalid_triggers if ignore_invalid_triggers is None else ignore_invalid_triggers

        for state in listify(states):
            if isinstance(state, Enum):
                if isinstance(state.value, EnumMeta):
                    state = {'name': state, 'children': state.value}
                elif isinstance(state.value, dict):
                    state = dict(name=state, **state.value)
            if isinstance(state, string_types):
                self._add_string_state(state, on_enter, on_exit, ignore, remap, **kwargs)
            elif isinstance(state, Enum):
                self._add_enum_state(state, on_enter, on_exit, ignore, remap, **kwargs)
            elif isinstance(state, dict):
                self._add_dict_state(state, ignore, remap, **kwargs)
            elif isinstance(state, NestedState):
                if state.name in self.states:
                    raise ValueError("State {0} cannot be added since it already exists.".format(state.name))
                self.states[state.name] = state
                self._init_state(state)
            elif isinstance(state, HierarchicalMachine):
                self._add_machine_states(state, remap)
            elif isinstance(state, State) and not isinstance(state, NestedState):
                raise ValueError("A passed state object must derive from NestedState! "
                                 "A default State object is not sufficient")
            else:
                raise ValueError("Cannot add state of type {0}. ".format(type(state).__name__))

    def add_transition(self, trigger, source, dest, conditions=None,
                       unless=None, before=None, after=None, prepare=None, **kwargs):
        if source == self.wildcard_all and dest == self.wildcard_same:
            source = self.get_nested_state_names()
        else:
            if source != self.wildcard_all:
                source = [self.state_cls.separator.join(self._get_enum_path(s)) if isinstance(s, Enum) else s
                          for s in listify(source)]
            if dest != self.wildcard_same:
                dest = self.state_cls.separator.join(self._get_enum_path(dest)) if isinstance(dest, Enum) else dest
        super(HierarchicalMachine, self).add_transition(trigger, source, dest, conditions,
                                                        unless, before, after, prepare, **kwargs)

    def get_global_name(self, state=None, join=True):
        """ Returns the name of the passed state in context of the current prefix/scope.
        Args:
            state (str, Enum or NestedState): The state to be analyzed.
            join (bool): Whether this method should join the path elements or not
        Returns:
            str or list(str) of the global state name
        """
        domains = copy.copy(self.prefix_path)
        if state:
            state_name = state.name if hasattr(state, 'name') else state
            if state_name in self.states:
                domains.append(state_name)
            else:
                raise ValueError("State '{0}' not found in local states.".format(state))
        return self.state_cls.separator.join(domains) if join else domains

    def get_nested_state_names(self):
        """ Returns a list of global names of all states of a machine.
        Returns:
            list(str) of global state names.
        """
        ordered_states = []
        for state in self.states.values():
            ordered_states.append(self.get_global_name(state))
            with self(state.name):
                ordered_states.extend(self.get_nested_state_names())
        return ordered_states

    def get_nested_transitions(self, trigger="", src_path=None, dest_path=None):
        """ Retrieves a list of all transitions matching the passed requirements.
        Args:
            trigger (str): If set, return only transitions related to this trigger.
            src_path (list(str)): If set, return only transitions with this source state.
            dest_path (list(str)): If set, return only transitions with this destination.

        Returns:
            list(NestedTransitions) of valid transitions.
        """
        if src_path and dest_path:
            src = self.state_cls.separator.join(src_path)
            dest = self.state_cls.separator.join(dest_path)
            transitions = super(HierarchicalMachine, self).get_transitions(trigger, src, dest)
            if len(src_path) > 1 and len(dest_path) > 1:
                with self(src_path[0]):
                    transitions.extend(self.get_nested_transitions(trigger, src_path[1:], dest_path[1:]))
        elif src_path:
            src = self.state_cls.separator.join(src_path)
            transitions = super(HierarchicalMachine, self).get_transitions(trigger, src, "*")
            if len(src_path) > 1:
                with self(src_path[0]):
                    transitions.extend(self.get_nested_transitions(trigger, src_path[1:], None))
        elif dest_path:
            dest = self.state_cls.separator.join(dest_path)
            transitions = super(HierarchicalMachine, self).get_transitions(trigger, "*", dest)
            if len(dest_path) > 1:
                for state_name in self.states:
                    with self(state_name):
                        transitions.extend(self.get_nested_transitions(trigger, None, dest_path[1:]))
        else:
            transitions = super(HierarchicalMachine, self).get_transitions(trigger, "*", "*")
            for state_name in self.states:
                with self(state_name):
                    transitions.extend(self.get_nested_transitions(trigger, None, None))
        return transitions

    def get_nested_triggers(self, src_path=None):
        """ Retrieves a list of valid triggers.
        Args:
            src_path (list(str)): A list representation of the source state's name.
        Returns:
            list(str) of valid trigger names.
        """
        if src_path:
            triggers = super(HierarchicalMachine, self).get_triggers(self.state_cls.separator.join(src_path))
            if len(src_path) > 1 and src_path[0] in self.states:
                with self(src_path[0]):
                    triggers.extend(self.get_nested_triggers(src_path[1:]))
        else:
            triggers = list(self.events.keys())
            for state_name in self.states:
                with self(state_name):
                    triggers.extend(self.get_nested_triggers())
        return triggers

    def get_state(self, state, hint=None):
        """ Return the State instance with the passed name.
        Args:
            state (str, Enum or list(str)): A state name, enum or state path
            hint (list(str)): A state path to check for the state in question
        Returns:
            NestedState that belongs to the passed str (list) or Enum.
        """
        if isinstance(state, Enum):
            state = self._get_enum_path(state)
        elif isinstance(state, string_types):
            state = state.split(self.state_cls.separator)
        if not hint:
            state = copy.copy(state)
            hint = copy.copy(state)
        if len(state) > 1:
            child = state.pop(0)
            try:
                with self(child):
                    return self.get_state(state, hint)
            except (KeyError, ValueError):
                try:
                    with self():
                        state = self
                        for elem in hint:
                            state = state.states[elem]
                        return state
                except KeyError:
                    raise ValueError(
                        "State '%s' is not a registered state." % self.state_cls.separator.join(hint)
                    )  # from KeyError
        elif state[0] not in self.states:
            raise ValueError("State '%s' is not a registered state." % state)
        return self.states[state[0]]

    def get_states(self, states):
        """ Retrieves a list of NestedStates.
        Args:
            states (str, Enum or list of str or Enum): Names/values of the states to retrieve.
        Returns:
            list(NestedStates) belonging to the passed identifiers.
        """
        res = []
        for state in states:
            if isinstance(state, list):
                res.append(self.get_states(state))
            else:
                res.append(self.get_state(state))
        return res

    def get_transitions(self, trigger="", source="*", dest="*", delegate=False):
        """ Return the transitions from the Machine.
        Args:
            trigger (str): Trigger name of the transition.
            source (str, State or Enum): Limits list to transitions from a certain state.
            dest (str, State or Enum): Limits list to transitions to a certain state.
            delegate (Optional[bool]): If True, consider delegations to parents of source
        Returns:
            list(NestedTransitions): All transitions matching the request.
        """
        with self():
            source_path = [] if source == "*" \
                else source.split(self.state_cls.separator) if isinstance(source, string_types) \
                else self._get_enum_path(source) if isinstance(source, Enum) \
                else self._get_state_path(source)
            dest_path = [] if dest == "*" \
                else dest.split(self.state_cls.separator) if isinstance(dest, string_types) \
                else self._get_enum_path(dest) if isinstance(dest, Enum) \
                else self._get_state_path(dest)
            matches = self.get_nested_transitions(trigger, source_path, dest_path)
            # only consider delegations when source_path contains a nested state (len > 1)
            if delegate is False or len(source_path) < 2:
                return matches
            source_path.pop()
            while source_path:
                matches.extend(self.get_transitions(trigger,
                                                    source=self.state_cls.separator.join(source_path),
                                                    dest=dest))
                source_path.pop()
            return matches

    def _can_trigger(self, model, trigger, *args, **kwargs):
        state_tree = self.build_state_tree(getattr(model, self.model_attribute), self.state_cls.separator)
        ordered_states = resolve_order(state_tree)
        for state_path in ordered_states:
            with self():
                return self._can_trigger_nested(model, trigger, state_path, *args, **kwargs)

    def _can_trigger_nested(self, model, trigger, path, *args, **kwargs):
        evt = NestedEventData(None, None, self, model, args, kwargs)
        if trigger in self.events:
            source_path = copy.copy(path)
            while source_path:
                state_name = self.state_cls.separator.join(source_path)
                for transition in self.events[trigger].transitions.get(state_name, []):
                    try:
                        _ = self.get_state(transition.dest)
                    except ValueError:
                        continue
                    self.callbacks(self.prepare_event, evt)
                    self.callbacks(transition.prepare, evt)
                    if all(c.check(evt) for c in transition.conditions):
                        return True
                source_path.pop(-1)
        if path:
            with self(path.pop(0)):
                return self._can_trigger_nested(model, trigger, path, *args, **kwargs)
        return False

    def get_triggers(self, *args):
        """ Extends transitions.core.Machine.get_triggers to also include parent state triggers. """
        triggers = []
        with self():
            for state in args:
                state_name = state.name if hasattr(state, 'name') else state
                state_path = state_name.split(self.state_cls.separator)
                if len(state_path) > 1:  # we only need to check substates when 'state_name' refers to a substate
                    with self(state_path[0]):
                        triggers.extend(self.get_nested_triggers(state_path[1:]))
                while state_path:  # check all valid transitions for parent states
                    triggers.extend(super(HierarchicalMachine, self).get_triggers(
                        self.state_cls.separator.join(state_path)))
                    state_path.pop()
        return triggers

    def has_trigger(self, trigger, state=None):
        """ Check whether an event/trigger is known to the machine
        Args:
            trigger (str): Event/trigger name
            state (optional[NestedState]): Limits the recursive search to this state and its children
        Returns:
            bool: True if event is known and False otherwise
        """

        state = state or self
        return trigger in state.events or any(self.has_trigger(trigger, sta) for sta in state.states.values())

    def is_state(self, state, model, allow_substates=False):
        if allow_substates:
            current = getattr(model, self.model_attribute)
            current_name = self.state_cls.separator.join(self._get_enum_path(current))\
                if isinstance(current, Enum) else current
            state_name = self.state_cls.separator.join(self._get_enum_path(state))\
                if isinstance(state, Enum) else state
            return current_name.startswith(state_name)
        return getattr(model, self.model_attribute) == state

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

    def set_state(self, state, model=None):
        """ Set the current state.
        Args:
            state (list of str or Enum or State): value of state(s) to be set
            model (optional[object]): targeted model; if not set, all models will be set to 'state'
        """
        values = [self._set_state(value) for value in listify(state)]
        models = self.models if model is None else listify(model)
        for mod in models:
            setattr(mod, self.model_attribute, values if len(values) > 1 else values[0])

    def to_state(self, model, state_name, *args, **kwargs):
        """ Helper function to add go to states in case a custom state separator is used.
        Args:
            model (class): The model that should be used.
            state_name (str): Name of the destination state.
        """

        current_state = getattr(model, self.model_attribute)
        if isinstance(current_state, list):
            raise MachineError("Cannot use 'to_state' from parallel state")

        event = NestedEventData(self.get_state(current_state), Event('to', self), self,
                                model, args=args, kwargs=kwargs)
        if isinstance(current_state, Enum):
            event.source_path = self._get_enum_path(current_state)
            event.source_name = self.state_cls.separator.join(event.source_path)
        else:
            event.source_name = current_state
            event.source_path = current_state.split(self.state_cls.separator)
        self._create_transition(event.source_name, state_name).execute(event)

    def trigger_event(self, model, trigger, *args, **kwargs):
        """ Processes events recursively and forwards arguments if suitable events are found.
        This function is usually bound to models with model and trigger arguments already
        resolved as a partial. Execution will halt when a nested transition has been executed
        successfully.
        Args:
            model (object): targeted model
            trigger (str): event name
            *args: positional parameters passed to the event and its callbacks
            **kwargs: keyword arguments passed to the event and its callbacks
        Returns:
            bool: whether a transition has been executed successfully
        Raises:
            MachineError: When no suitable transition could be found and ignore_invalid_trigger
                          is not True. Note that a transition which is not executed due to conditions
                          is still considered valid.
        """
        event_data = NestedEventData(state=None, event=None, machine=self, model=model, args=args, kwargs=kwargs)
        event_data.result = None

        return self._process(partial(self._trigger_event, event_data, trigger))

    def _trigger_event(self, event_data, trigger):
        try:
            with self():
                res = self._trigger_event_nested(event_data, trigger, None)
            event_data.result = self._check_event_result(res, event_data.model, trigger)
        except Exception as err:  # pylint: disable=broad-except; Exception will be handled elsewhere
            event_data.error = err
            if self.on_exception:
                self.callbacks(self.on_exception, event_data)
            else:
                raise
        finally:
            try:
                self.callbacks(self.finalize_event, event_data)
                _LOGGER.debug("%sExecuted machine finalize callbacks", self.name)
            except Exception as err:  # pylint: disable=broad-except; Exception will be handled elsewhere
                _LOGGER.error("%sWhile executing finalize callbacks a %s occurred: %s.",
                              self.name,
                              type(err).__name__,
                              str(err))
        return event_data.result

    def _add_model_to_state(self, state, model):
        name = self.get_global_name(state)
        if self.state_cls.separator == '_':
            value = state.value if isinstance(state.value, Enum) else name
            self._checked_assignment(model, 'is_%s' % name, partial(self.is_state, value, model))
            # Add dynamic method callbacks (enter/exit) if there are existing bound methods in the model
            # except if they are already mentioned in 'on_enter/exit' of the defined state
            for callback in self.state_cls.dynamic_methods:
                method = "{0}_{1}".format(callback, name)
                if hasattr(model, method) and inspect.ismethod(getattr(model, method)) and \
                        method not in getattr(state, callback):
                    state.add_callback(callback[3:], method)
        else:
            path = name.split(self.state_cls.separator)
            value = state.value if isinstance(state.value, Enum) else name
            trig_func = partial(self.is_state, value, model)
            if hasattr(model, 'is_' + path[0]):
                getattr(model, 'is_' + path[0]).add(trig_func, path[1:])
            else:
                self._checked_assignment(model, 'is_' + path[0], FunctionWrapper(trig_func, path[1:]))
        with self(state.name):
            for event in self.events.values():
                if not hasattr(model, event.name):
                    self._add_trigger_to_model(event.name, model)
            for a_state in self.states.values():
                self._add_model_to_state(a_state, model)

    def _add_dict_state(self, state, ignore_invalid_triggers, remap, **kwargs):
        if remap is not None and state['name'] in remap:
            return
        state = state.copy()  # prevent messing with the initially passed dict
        remap = state.pop('remap', None)
        if 'ignore_invalid_triggers' not in state:
            state['ignore_invalid_triggers'] = ignore_invalid_triggers

        # parallel: [states] is just a short handle for {children: [states], initial: [state_names]}
        state_parallel = state.pop('parallel', [])
        if state_parallel:
            state_children = state_parallel
            state['initial'] = [s['name'] if isinstance(s, dict)
                                else s for s in state_children]
        else:
            state_children = state.pop('children', state.pop('states', []))
        transitions = state.pop('transitions', [])
        new_state = self._create_state(**state)
        self.states[new_state.name] = new_state
        self._init_state(new_state)
        remapped_transitions = []
        with self(new_state.name):
            self.add_states(state_children, remap=remap, **kwargs)
            if transitions:
                self.add_transitions(transitions)
            if remap is not None:
                remapped_transitions.extend(self._remap_state(new_state, remap))

        self.add_transitions(remapped_transitions)

    def _add_enum_state(self, state, on_enter, on_exit, ignore_invalid_triggers, remap, **kwargs):
        if remap is not None and state.name in remap:
            return
        if self.state_cls.separator in state.name:
            raise ValueError("State '{0}' contains '{1}' which is used as state name separator. "
                             "Consider changing the NestedState.separator to avoid this issue."
                             "".format(state.name, self.state_cls.separator))
        if state.name in self.states:
            raise ValueError("State {0} cannot be added since it already exists.".format(state.name))
        new_state = self._create_state(state, on_enter=on_enter, on_exit=on_exit,
                                       ignore_invalid_triggers=ignore_invalid_triggers, **kwargs)
        self.states[new_state.name] = new_state
        self._init_state(new_state)

    def _add_machine_states(self, state, remap):
        new_states = [s for s in state.states.values() if remap is None or s not in remap]
        self.add_states(new_states)
        for evt in state.events.values():
            self.events[evt.name] = evt
        if self.scoped.initial is None:
            self.scoped.initial = state.initial

    def _add_string_state(self, state, on_enter, on_exit, ignore_invalid_triggers, remap, **kwargs):
        if remap is not None and state in remap:
            return
        domains = state.split(self.state_cls.separator, 1)
        if len(domains) > 1:
            try:
                self.get_state(domains[0])
            except ValueError:
                self.add_state(domains[0], on_enter=on_enter, on_exit=on_exit,
                               ignore_invalid_triggers=ignore_invalid_triggers, **kwargs)
            with self(domains[0]):
                self.add_states(domains[1], on_enter=on_enter, on_exit=on_exit,
                                ignore_invalid_triggers=ignore_invalid_triggers, **kwargs)
        else:
            if state in self.states:
                raise ValueError("State {0} cannot be added since it already exists.".format(state))
            new_state = self._create_state(state, on_enter=on_enter, on_exit=on_exit,
                                           ignore_invalid_triggers=ignore_invalid_triggers, **kwargs)
            self.states[new_state.name] = new_state
            self._init_state(new_state)

    def _add_trigger_to_model(self, trigger, model):
        trig_func = partial(self.trigger_event, model, trigger)
        self._add_may_transition_func_for_trigger(trigger, model)
        # FunctionWrappers are only necessary if a custom separator is used
        if trigger.startswith('to_') and self.state_cls.separator != '_':
            path = trigger[3:].split(self.state_cls.separator)
            if hasattr(model, 'to_' + path[0]):
                # add path to existing function wrapper
                getattr(model, 'to_' + path[0]).add(trig_func, path[1:])
            else:
                # create a new function wrapper
                self._checked_assignment(model, 'to_' + path[0], FunctionWrapper(trig_func, path[1:]))
        else:
            self._checked_assignment(model, trigger, trig_func)

    def build_state_tree(self, model_states, separator, tree=None):
        """ Converts a list of current states into a hierarchical state tree.
        Args:
            model_states (str or list(str)):
            separator (str): The character used to separate state names
            tree (OrderedDict): The current branch to use. If not passed, create a new tree.
        Returns:
            OrderedDict: A state tree dictionary
        """
        tree = tree if tree is not None else OrderedDict()
        if isinstance(model_states, list):
            for state in model_states:
                _ = self.build_state_tree(state, separator, tree)
        else:
            tmp = tree
            if isinstance(model_states, (Enum, EnumMeta)):
                with self():
                    path = self._get_enum_path(model_states)
            else:
                path = model_states.split(separator)
            for elem in path:
                tmp = tmp.setdefault(elem.name if hasattr(elem, 'name') else elem, OrderedDict())
        return tree

    def _get_enum_path(self, enum_state, prefix=None):
        prefix = prefix or []
        if enum_state.name in self.states and self.states[enum_state.name].value == enum_state:
            return prefix + [enum_state.name]
        for name in self.states:
            with self(name):
                res = self._get_enum_path(enum_state, prefix=prefix + [name])
                if res:
                    return res
        # if we reach this point without a prefix, we looped over all nested states
        # and could not find a suitable enum state
        if not prefix:
            raise ValueError("Could not find path of {0}.".format(enum_state))
        return None

    def _get_state_path(self, state, prefix=None):
        prefix = prefix or []
        if state in self.states.values():
            return prefix + [state.name]
        for name in self.states:
            with self(name):
                res = self._get_state_path(state, prefix=prefix + [name])
                if res:
                    return res
        return []

    def _check_event_result(self, res, model, trigger):
        if res is None:
            state_names = getattr(model, self.model_attribute)
            msg = "%sCan't trigger event '%s' from state(s) %s!" % (self.name, trigger, state_names)
            for state_name in listify(state_names):
                state = self.get_state(state_name)
                ignore = state.ignore_invalid_triggers if state.ignore_invalid_triggers is not None \
                    else self.ignore_invalid_triggers
                if not ignore:
                    # determine whether a MachineError (valid event but invalid state) ...
                    if self.has_trigger(trigger):
                        raise MachineError(msg)
                    # or AttributeError (invalid event) is appropriate
                    raise AttributeError("Do not know event named '%s'." % trigger)
            _LOGGER.warning(msg)
            res = False
        return res

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
        return self.trigger_event(model, trigger_name, *args, **kwargs)

    def _has_state(self, state, raise_error=False):
        """ This function
        Args:
            state (NestedState): state to be tested
            raise_error (bool): whether ValueError should be raised when the state
                                is not registered
       Returns:
            bool: Whether state is registered in the machine
        Raises:
            ValueError: When raise_error is True and state is not registered
        """
        found = super(HierarchicalMachine, self)._has_state(state)
        if not found:
            for a_state in self.states:
                with self(a_state):
                    if self._has_state(state):
                        return True
        if not found and raise_error:
            msg = 'State %s has not been added to the machine' % (state.name if hasattr(state, 'name') else state)
            raise ValueError(msg)
        return found

    def _init_state(self, state):
        for model in self.models:
            self._add_model_to_state(state, model)
        if self.auto_transitions:
            state_name = self.get_global_name(state.name)
            parent = state_name.split(self.state_cls.separator, 1)
            with self():
                for a_state in self.get_nested_state_names():
                    if a_state == parent[0]:
                        self.add_transition('to_%s' % state_name, self.wildcard_all, state_name)
                    elif len(parent) == 1:
                        self.add_transition('to_%s' % a_state, state_name, a_state)
        with self(state.name):
            for substate in self.states.values():
                self._init_state(substate)

    def _recursive_initial(self, value):
        if isinstance(value, string_types):
            path = value.split(self.state_cls.separator, 1)
            if len(path) > 1:
                state_name, suffix = path
                # make sure the passed state has been created already
                super(HierarchicalMachine, self.__class__).initial.fset(self, state_name)
                with self(state_name):
                    self.initial = suffix
                    self._initial = state_name + self.state_cls.separator + self._initial
            else:
                super(HierarchicalMachine, self.__class__).initial.fset(self, value)
        elif isinstance(value, (list, tuple)):
            return [self._recursive_initial(v) for v in value]
        else:
            super(HierarchicalMachine, self.__class__).initial.fset(self, value)
        return self._initial[0] if isinstance(self._initial, list) and len(self._initial) == 1 else self._initial

    def _remap_state(self, state, remap):
        drop_event = []
        remapped_transitions = []
        for evt in self.events.values():
            self.events[evt.name] = copy.copy(evt)
        for trigger, event in self.events.items():
            drop_source = []
            event.transitions = copy.deepcopy(event.transitions)
            for source_name, trans_source in event.transitions.items():
                if source_name in remap:
                    drop_source.append(source_name)
                    continue
                drop_trans = []
                for trans in trans_source:
                    if trans.dest in remap:
                        conditions, unless = [], []
                        for cond in trans.conditions:
                            # split a list in two lists based on the accessors (cond.target) truth value
                            (unless, conditions)[cond.target].append(cond.func)
                        remapped_transitions.append({
                            'trigger': trigger,
                            'source': state.name + self.state_cls.separator + trans.source,
                            'dest': remap[trans.dest],
                            'conditions': conditions,
                            'unless': unless,
                            'prepare': trans.prepare,
                            'before': trans.before,
                            'after': trans.after})
                        drop_trans.append(trans)
                for d_trans in drop_trans:
                    trans_source.remove(d_trans)
                if not trans_source:
                    drop_source.append(source_name)
            for d_source in drop_source:
                del event.transitions[d_source]
            if not event.transitions:
                drop_event.append(trigger)
        for d_event in drop_event:
            del self.events[d_event]
        return remapped_transitions

    def _resolve_initial(self, models, state_name_path, prefix=None):
        prefix = prefix or []
        if state_name_path:
            state_name = state_name_path.pop(0)
            with self(state_name):
                return self._resolve_initial(models, state_name_path, prefix=prefix + [state_name])
        if self.scoped.initial:
            entered_states = []
            for initial_state_name in listify(self.scoped.initial):
                with self(initial_state_name):
                    entered_states.append(self._resolve_initial(models, [], prefix=prefix + [self.scoped.name]))
            return entered_states if len(entered_states) > 1 else entered_states[0]
        return self.state_cls.separator.join(prefix)

    def _set_state(self, state_name):
        if isinstance(state_name, list):
            return [self._set_state(value) for value in state_name]
        a_state = self.get_state(state_name)
        return a_state.value if isinstance(a_state.value, Enum) else state_name

    def _trigger_event_nested(self, event_data, trigger, _state_tree):
        model = event_data.model
        if _state_tree is None:
            _state_tree = self.build_state_tree(listify(getattr(model, self.model_attribute)),
                                                self.state_cls.separator)
        res = {}
        for key, value in _state_tree.items():
            if value:
                with self(key):
                    tmp = self._trigger_event_nested(event_data, trigger, value)
                    if tmp is not None:
                        res[key] = tmp
            if res.get(key, False) is False and trigger in self.events:
                event_data.event = self.events[trigger]
                tmp = event_data.event.trigger_nested(event_data)
                if tmp is not None:
                    res[key] = tmp
        return None if not res or all(v is None for v in res.values()) else any(res.values())
