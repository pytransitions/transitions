from ..core import State, Machine, Transition, Event, listify, EventData, MachineError, Enum

from collections import OrderedDict
import logging
from six import string_types
import inspect
from functools import partial
import copy

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())

# this is a workaround for dill issues when partials and super is used in conjunction
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


class NestedEvent(Event):

    def _trigger(self, model, state_name, machine, *args, **kwargs):
        separator = machine.state_cls.separator
        state_name = state_name.split(separator)
        while state_name and separator.join(state_name) not in self.transitions:
            state_name.pop()
        state_name = separator.join(state_name)
        if state_name in self.transitions:
            state = machine.get_state(state_name)
            event_data = EventData(state, self, machine, model, args=args, kwargs=kwargs)
            return self._process(event_data, state_name)
        else:
            return None

    def _process(self, event_data, state_name):
        machine = event_data.machine
        machine.callbacks(event_data.machine.prepare_event, event_data)
        _LOGGER.debug("%sExecuted machine preparation callbacks before conditions.", machine.name)

        try:
            for trans in self.transitions[state_name]:
                event_data.transition = trans
                if trans.execute(event_data):
                    event_data.result = True
                    break
        except Exception as err:
            event_data.error = err
            raise
        finally:
            machine.callbacks(machine.finalize_event, event_data)
            _LOGGER.debug("%sExecuted machine finalize callbacks", machine.name)
        return event_data.result


class NestedState(State):

    separator = '_'

    def __init__(self, name, on_enter=None, on_exit=None, ignore_invalid_triggers=None, initial=None, parent=None):
        _super(NestedState, self).__init__(name=name, on_enter=on_enter, on_exit=on_exit,
                                           ignore_invalid_triggers=ignore_invalid_triggers)
        self.initial = initial
        self.events = {}
        self.states = OrderedDict()

    def add_substate(self, state):
        self.add_substates(state)

    def add_substates(self, states):
        for state in listify(states):
            self.states[state.name] = state


class NestedTransition(Transition):

    def _change_state(self, event_data):
        model = event_data.model
        machine = event_data.machine
        src_name = machine.get_local_name(getattr(model, machine.model_attribute), join=False)
        dst_name = machine.get_local_name(self.dest, join=False)
        if src_name == dst_name:
            root = src_name[:-1]
        else:
            root = []
            while dst_name and src_name and src_name[0] == dst_name[0]:
                root.append(src_name.pop(0))
                dst_name.pop(0)
        dest_name = self._root_nested(root, src_name, dst_name, event_data)
        with machine():
            event_data.machine.set_state(dest_name, event_data.model)
        event_data.update(dest_name)

    def _root_nested(self, state_path, src_name, dst_name, event_data):
        if state_path:
            with event_data.machine(state_path.pop(0)):
                return self._root_nested(state_path, src_name, dst_name, event_data)
        else:
            if src_name:
                with event_data.machine(src_name.pop(0)):
                    self._exit_nested(src_name, event_data)
            if dst_name:
                # check if state actually exists
                _ = event_data.machine.get_state(event_data.machine.state_cls.separator.join(dst_name))
                with event_data.machine(dst_name.pop(0)):
                    dest_name = self._enter_nested(dst_name, event_data)
            else:
                dest_name = event_data.machine.get_global_name()
            return dest_name

    def _exit_nested(self, state_path, event_data):
        if state_path:
            with event_data.machine(state_path.pop(0)):
                self._exit_nested(state_path, event_data)
        event_data.machine.scoped.exit(event_data)

    def _enter_nested(self, state_path, event_data):
        state = event_data.machine.scoped
        state.enter(event_data)
        if state_path:
            state_name = state_path.pop(0)
            with event_data.machine(state_name):
                return self._enter_nested(state_path, event_data)
        elif state.initial:
            with event_data.machine(state.initial):
                return self._enter_nested([], event_data)
        else:
            return event_data.machine.get_global_name()


class HierarchicalMachine(Machine):

    state_cls = NestedState
    transition_cls = NestedTransition
    event_cls = NestedEvent

    def __init__(self, *args, **kwargs):
        self._stack = []
        self.scoped = self
        _super(HierarchicalMachine, self).__init__(*args, **kwargs)

    def add_states(self, states, on_enter=None, on_exit=None, ignore_invalid_triggers=None, **kwargs):
        remap = kwargs.pop('remap', None)
        for state in listify(states):
            if isinstance(state, string_types):
                if remap is not None and state in remap:
                    return
                domains = state.split(self.state_cls.separator, 1)
                if len(domains) > 1:
                    try:
                        self.get_state(domains[0])
                    except ValueError:
                        self.add_state(domains[0], on_enter=on_enter, on_exit=on_exit, ignore_invalid_triggers=ignore_invalid_triggers, **kwargs)
                    with self(domains[0]):
                        self.add_states(domains[1], on_enter=on_enter, on_exit=on_exit, ignore_invalid_triggers=ignore_invalid_triggers, **kwargs)
                else:
                    if state in self.states:
                        raise ValueError("State {0} cannot be added since it already exists.".format(state))
                    new_state = self._create_state(state)
                    self.states[new_state.name] = new_state
                    self._init_state(new_state)
            elif isinstance(state, Enum):
                if remap is not None and state.name in remap:
                    return
                if self.scoped != self:
                    raise ValueError("HierarchicalMachine does not support nested enumerations.")
                new_state = self._create_state(state)
                if state.name in self.states:
                    raise ValueError("State {0} cannot be added since it already exists.".format(state.name))
                self.states[new_state.name] = new_state
                self._init_state(new_state)
            elif isinstance(state, dict):
                if remap is not None and state['name'] in remap:
                    return
                state = state.copy()  # prevent messing with the initially passed dict
                remap = state.pop('remap', None)
                state_children = state.pop('children', [])
                transitions = state.pop('transitions', [])
                new_state = self._create_state(**state)
                self.states[new_state.name] = new_state
                self._init_state(new_state)
                remapped_transitions = []
                with self(new_state.name):
                    self.add_states(state_children, remap=remap, **kwargs)
                    if remap is not None:
                        drop_event = []
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
                                            'source': new_state.name + self.state_cls.separator + trans.source,
                                            'dest': remap[trans.dest],
                                            'conditions': conditions,
                                            'unless': unless,
                                            'prepare': trans.prepare,
                                            'before': trans.before,
                                            'after': trans.after})
                                        drop_trans.append(trans)
                                for t in drop_trans:
                                    trans_source.remove(t)
                                if not trans_source:
                                    drop_source.append(source_name)
                            for s in drop_source:
                                del event.transitions[s]
                            if not event.transitions:
                                drop_event.append(trigger)
                        for e in drop_event:
                            del self.events[e]
                    if transitions:
                        self.add_transitions(transitions)
                self.add_transitions(remapped_transitions)
            elif isinstance(state, NestedState):
                if state.name in self.states:
                    raise ValueError("State {0} cannot be added since it already exists.".format(state.name))
                self.states[state.name] = state
                self._init_state(state)
            elif isinstance(state, Machine):
                new_states = [s for s in state.states.values() if remap is None or s not in remap]
                self.add_states(new_states)
                for ev in state.events.values():
                    self.events[ev.name] = ev
                if self.scoped.initial is None:
                    self.scoped.initial = state.initial
            else:
                raise ValueError("Cannot add state of type {0}.".format(type(state).__name__))

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

    def _has_state(self, state, raise_error=False):
        found = _super(HierarchicalMachine, self)._has_state(state)
        if not found:
            for a_state in self.states:
                with self(a_state):
                    if self.has_state(state):
                        return True
        if not found and raise_error:
            msg = 'State %s has not been added to the machine' % (state.name if hasattr(state, 'name') else state)
            raise ValueError(msg)
        return found

    def add_ordered_transitions(self, states=None, trigger='next_state',
                                loop=True, loop_includes_initial=True,
                                conditions=None, unless=None, before=None,
                                after=None, prepare=None, **kwargs):
        if states is None:
            states = self.get_nested_state_names()
        _super(HierarchicalMachine, self).add_ordered_transitions(states=states, trigger=trigger, loop=loop,
                                                                  loop_includes_initial=loop_includes_initial,
                                                                  conditions=conditions,
                                                                  unless=unless, before=before, after=after,
                                                                  prepare=prepare, **kwargs)

    def get_nested_triggers(self, dest=None):
        if dest:
            triggers = _super(HierarchicalMachine, self).get_triggers(dest)
        else:
            triggers = list(self.events.keys())
        for state in self.states.values():
            with self(state.name):
                triggers.extend(self.get_nested_triggers())
        return triggers

    def get_nested_state_names(self):
        ordered_states = []
        for state in self.states.values():
            ordered_states.append(self.get_global_name(state))
            with self(state.name):
                ordered_states.extend(self.get_nested_state_names())
        return ordered_states

    def _add_model_to_state(self, state, model):
        name = self.get_global_name(state)
        if self.state_cls.separator == '_' or self.state_cls.separator not in name:
            value = state.value if isinstance(state.value, Enum) else name
            self._checked_assignment(model, 'is_%s' % name, partial(self.is_state, value, model))
            # Add dynamic method callbacks (enter/exit) if there are existing bound methods in the model
            # except if they are already mentioned in 'on_enter/exit' of the defined state
            for callback in self.state_cls.dynamic_methods:
                method = "{0}_{1}".format(callback, name)
                if hasattr(model, method) and inspect.ismethod(getattr(model, method)) and \
                        method not in getattr(state, callback):
                    state.add_callback(callback[3:], method)
        with self(state.name):
            for event in self.events.values():
                if not hasattr(model, event.name):
                    self._add_trigger_to_model(event.name, model)
            for state in self.states.values():
                self._add_model_to_state(state, model)

    def _add_trigger_to_model(self, trigger, model):
        trig_func = partial(self.trigger_event, model, trigger)
        # FunctionWrappers are only necessary if a custom separator is used
        if trigger.startswith('to_') and NestedState.separator != '_':
            path = trigger[3:].split(NestedState.separator)
            if hasattr(model, 'to_' + path[0]):
                # add path to existing function wrapper
                getattr(model, 'to_' + path[0]).add(trig_func, path[1:])
            else:
                # create a new function wrapper
                self._checked_assignment(model, 'to_' + path[0], FunctionWrapper(trig_func, path[1:]))
        else:
            self._checked_assignment(model, trigger, trig_func)

    def trigger_event(self, model, trigger, *args, **kwargs):
        with self():
            res = self._trigger_event(model, trigger, *args, **kwargs)
        if res is None:
            state_name = getattr(model, self.model_attribute)
            msg = "%sCan't trigger event %s from state %s!" % (self.name, trigger, state_name)
            state = self.get_state(state_name)
            ignore = state.ignore_invalid_triggers if state.ignore_invalid_triggers is not None \
                else self.ignore_invalid_triggers
            if ignore:
                _LOGGER.warning(msg)
                return False
            else:
                raise MachineError(msg)
        return res

    def _trigger_event(self, model, trigger, *args, **kwargs):
        state_name = getattr(model, self.model_attribute)
        state_name = self.get_local_name(state_name)
        res = None
        if state_name:
            with self(state_name):
                res = self._trigger_event(model, trigger, *args, **kwargs)
        if not res and trigger in self.events:
            res = self.events[trigger]._trigger(model, state_name, self, *args, **kwargs)
        return res

    def is_state(self, state_name, model, allow_substates=False):
        current_name = getattr(model, self.model_attribute)
        if allow_substates:
            return current_name.startswith(state_name.name if hasattr(state_name, 'name') else state_name)
        return current_name == state_name

    def add_model(self, model, initial=None):
        """ Extends transitions.core.Machine.add_model by applying a custom 'to' function to
            the added model.
        """
        models = [mod if mod != 'self' else self for mod in listify(model)]
        _super(HierarchicalMachine, self).add_model(models, initial=initial)
        initial_name = getattr(models[0], self.model_attribute)
        if hasattr(initial_name, 'name'):
            initial_name = initial_name.name
        initial_state = self.get_state(initial_name)
        if initial_state.initial:
            while initial_state.initial:
                initial_name += self.state_cls.separator + initial_state.initial
                initial_state = initial_state.states[initial_state.initial]
            for mod in models:
                self.set_state(initial_name, mod)

        for mod in models:
            # TODO: Remove 'mod != self' in 0.7.0
            if hasattr(mod, 'to') and mod != self:
                _LOGGER.warning("%sModel already has a 'to'-method. It will NOT "
                                "be overwritten by NestedMachine", self.name)
            else:
                to_func = partial(self.to_state, mod)
                setattr(mod, 'to', to_func)

    def get_global_name(self, state=None, join=True):
        local_stack = [s[0] for s in self._stack] + [self.scoped]
        local_stack_start = len(local_stack) - local_stack[::-1].index(self)
        domains = [s.name for s in local_stack[local_stack_start:]]
        if state:
            if isinstance(state, State):
                state = state.name
            domains = self._get_global_name(state, domains)
        return self.state_cls.separator.join(domains) if join else domains[1:]

    def _get_global_name(self, state=None, domains=[]):
        domains.append(state)
        if state in self.states:
            return domains
        else:
            for child in self.states:
                with self(child):
                    domains = self._global_name(state, domains)
                    if domains:
                        return [child] + domains
            return []

    def get_local_name(self, state_name, join=True):
        if isinstance(state_name, Enum):
            state_name = state_name.name
        elif isinstance(state_name, State):
            if state_name == self.scoped:
                return '' if join else []
            state_name = self.get_global_name(state_name)
        state_name = state_name.split(self.state_cls.separator)
        local_stack = [s[0] for s in self._stack] + [self.scoped]
        local_stack_start = len(local_stack) - local_stack[::-1].index(self)
        domains = [s.name for s in local_stack[local_stack_start:]]
        if domains and state_name and state_name[0] != domains[0]:
            return self.state_cls.separator.join(state_name) if join else state_name
        while domains and state_name and state_name[0] == domains[0]:
            state_name.pop(0)
            domains.pop(0)
        return self.state_cls.separator.join(state_name) if join else state_name

    def set_state(self, state, model=None):
        state_name = state
        state = self.get_state(state_name)
        value = state.value if isinstance(state.value, Enum) else state_name
        models = self.models if model is None else listify(model)
        for mod in models:
            setattr(mod, self.model_attribute, value)

    def get_state(self, state, hint=None):
        """ Return the State instance with the passed name. """
        if isinstance(state, Enum):
            state = [state.name]
        elif isinstance(state, string_types):
            state = state.split(self.state_cls.separator)
        if not hint:
            hint = copy.copy(state)
        if len(state) > 1:
            child = state.pop(0)
            try:
                with self(child):
                    return self.get_state(state, hint)
            except KeyError:
                return self.get_global_state(hint)
        elif state[0] not in self.states:
            raise ValueError("State '%s' is not a registered state." % state)
        return self.states[state[0]]

    def get_global_state(self, state):
        states = self._stack[0][1] if self._stack else self.states
        domains = state
        for sco in domains:
            states = states[sco].states
        return states

    def __call__(self, to_scope=None):
        if isinstance(to_scope, string_types):
            state_name = to_scope.split(self.state_cls.separator)[0]
            state = self.states[state_name]
            to_scope = (state, state.states, state.events)
        elif to_scope is None:
            if self._stack:
                to_scope = self._stack[0]
            else:
                to_scope = (self, self.states, self.events)
        self._next_scope = to_scope

        return self

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
            return self.trigger_event(model, trigger_name, *args, **kwargs)
        except MachineError:
            raise AttributeError("Do not know event named '%s'." % trigger_name)

    def get_triggers(self, *args):
        """ Extends transitions.core.Machine.get_triggers to also include parent state triggers. """
        # add parents to state set
        triggers = []
        with self():
            for state_name in args:
                state_path = state_name.split(self.state_cls.separator)
                root = state_path[0]
                while state_path:
                    triggers.extend(_super(HierarchicalMachine, self).get_triggers(self.state_cls.separator.join(state_path)))
                    with self(root):
                        triggers.extend(self.get_nested_triggers(self.state_cls.separator.join(state_path)))
                    state_path.pop()
        return triggers

    def __enter__(self):
        self._stack.append((self.scoped, self.states, self.events))
        self.scoped, self.states, self.events = self._next_scope
        self._next_scope = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.scoped, self.states, self.events = self._stack.pop()

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

        event = EventData(self.get_model_state(model), Event('to', self), self,
                          model, args=args, kwargs=kwargs)
        self._create_transition(getattr(model, self.model_attribute), state_name).execute(event)
