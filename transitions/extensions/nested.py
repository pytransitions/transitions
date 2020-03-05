from transitions.core import State, Machine, Transition, Event, listify, EventData, _get_trigger
from transitions.extensions.nesting import FunctionWrapper

from collections import OrderedDict
import logging
from six import string_types
import inspect
from functools import partial

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())


class NestedEvent(Event):

    def _trigger(self, model, state_name, *args, **kwargs):
        separator = self.machine.state_cls.separator
        state_name = state_name.split(separator)
        while state_name and separator.join(state_name) not in self.transitions:
            state_name.pop()
        state_name = separator.join(state_name)
        if state_name in self.transitions:
            state = self.machine.get_state(state_name)
            event_data = EventData(state, self, self.machine, model, args=args, kwargs=kwargs)
            return self._process(event_data, state_name)
        else:
            return False

    def _process(self, event_data, state_name):

        self.machine.callbacks(self.machine.prepare_event, event_data)
        _LOGGER.debug("%sExecuted machine preparation callbacks before conditions.", self.machine.name)

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
            self.machine.callbacks(self.machine.finalize_event, event_data)
            _LOGGER.debug("%sExecuted machine finalize callbacks", self.machine.name)
        return event_data.result


class NestedState(State):

    separator = '_'

    def __init__(self, name, on_enter=None, on_exit=None, ignore_invalid_triggers=None, initial=None, parent=None):
        super(NestedState, self).__init__(name=name, on_enter=on_enter, on_exit=on_exit,
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
        dest_name = self._root_nested(root, event_data)
        event_data.machine.set_state(dest_name, event_data.model)
        event_data.update(dest_name)

    def _root_nested(self, state_path, event_data):
        if state_path:
            with event_data.machine(state_path.pop(0)):
                return self._root_nested(state_path, event_data)
        else:
            src_name = event_data.machine.get_local_name(getattr(event_data.model, event_data.machine.model_attribute),
                                                         join=False)
            dst_name = event_data.machine.get_local_name(self.dest, join=False)
            if src_name:
                with event_data.machine(src_name.pop(0)):
                    self._exit_nested(src_name, event_data)
            if dst_name:
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


class NestedMachine(Machine):

    state_cls = NestedState
    transition_cls = NestedTransition
    event_cls = NestedEvent

    def __init__(self, *args, **kwargs):
        self._stack = []
        self.scoped = self
        super(NestedMachine, self).__init__(*args, **kwargs)

    def add_states(self, states, on_enter=None, on_exit=None, ignore_invalid_triggers=None, **kwargs):
        for state in listify(states):
            if isinstance(state, string_types):
                domains = state.split(self.state_cls.separator, 1)
                if len(domains) > 1:
                    try:
                        self.get_state(domains[0])
                    except ValueError:
                        self.add_state(domains[0], on_enter=on_enter, on_exit=on_exit, ignore_invalid_triggers=ignore_invalid_triggers, **kwargs)
                    with self(domains[0]):
                        self.add_states(domains[1], on_enter=on_enter, on_exit=on_exit, ignore_invalid_triggers=ignore_invalid_triggers, **kwargs)
                else:
                    self.states[state] = self._create_state(state)
                    self._init_state(self.states[state])

            elif isinstance(state, dict):
                # state = copy(state)
                # if 'ignore_invalid_triggers' not in state:
                #     state['ignore_invalid_triggers'] = ignore
                state_children = state.pop('children', [])  # throws KeyError when no children set
                transitions = state.pop('transitions', [])
                new_state = self._create_state(**state)
                self.states[new_state.name] = new_state
                self._init_state(new_state)
                with self(new_state.name):
                    if transitions:
                        self.add_transitions(transitions)
                    self.add_states(state_children)
            elif isinstance(state, NestedState):
                self.states[state.name] = state
                self._init_state(state)

    def _init_state(self, state):
        for model in self.models:
            self._add_model_to_state(state, model)
        if self.auto_transitions:
            state_name = self.get_global_name(state.name)
            parent = state_name.split(self.state_cls.separator, 1)[0]
            with self():
                for a_state in self.states:
                    if parent == a_state:
                        self.add_transition('to_%s' % state_name, self.wildcard_all, state_name)
                    else:
                        self.add_transition('to_%s' % a_state, parent, a_state)
            for substate in state.states.values():
                self._init_state(substate)

    def get_nested_triggers(self, dest=None):
        if dest:
            triggers = super(NestedMachine, self).get_triggers(dest)
        else:
            triggers = list(self.events.keys())
        for state in self.states.values():
            with self(state.name):
                triggers.extend(self.get_nested_triggers())
        return triggers

    def get_nested_states(self):
        states = list(self.states.values())
        for state in self.states.values():
            with self(state.name):
                states.extend(self.get_nested_states())
        return states

    def _add_model_to_state(self, state, model):
        name = self.get_global_name(state)
        if self.state_cls.separator == '_' or self.state_cls.separator not in name:
            self._checked_assignment(model, 'is_%s' % name, partial(self.is_state, state.value, model))
            # Add dynamic method callbacks (enter/exit) if there are existing bound methods in the model
            # except if they are already mentioned in 'on_enter/exit' of the defined state
            for callback in self.state_cls.dynamic_methods:
                method = "{0}_{1}".format(callback, name)
                if hasattr(model, method) and inspect.ismethod(getattr(model, method)) and \
                        method not in getattr(state, callback):
                    state.add_callback(callback[3:], method)
        with self(state.name):
            for state in self.states.values():
                self._add_model_to_state(state, model)

    def _add_trigger_to_model(self, trigger, model):
        trig_func = partial(self._trigger_event, model, trigger)
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

    def _trigger_event(self, model, trigger, *args, **kwargs):
        state_name = getattr(model, self.model_attribute)
        state_name = self.get_local_name(state_name)
        if trigger in self.events:
            res = self.events[trigger]._trigger(model, state_name, *args, **kwargs)
        else:
            res = False
        if not res and state_name:
            with self(state_name):
                res = self._trigger_event(model, trigger, *args, **kwargs)
        return res

    def is_state(self, state_name, model, allow_substates=False):
        current_name = getattr(model, self.model_attribute)
        if not allow_substates:
            return current_name == state_name
        return current_name.startswith(state_name)

    def add_model(self, model, initial=None):
        """ Extends transitions.core.Machine.add_model by applying a custom 'to' function to
            the added model.
        """
        super(NestedMachine, self).add_model(model, initial=initial)
        models = listify(model)
        initial_name = getattr(models[0] if models[0] != 'self' else self, self.model_attribute)
        initial_state = self.get_state(initial_name)
        while initial_state.initial:
            initial_name += self.state_cls.separator + initial_state.initial
            initial_state = initial_state.states[initial_state.initial]

        for mod in models:
            mod = self if mod == 'self' else mod
            self.set_state(initial_name, mod)
            # TODO: Remove 'mod != self' in 0.7.0
            if hasattr(mod, 'to') and mod != self:
                _LOGGER.warning("%sModel already has a 'to'-method. It will NOT "
                                "be overwritten by NestedMachine", self.name)
            else:
                to_func = partial(self.to_state, mod)
                setattr(mod, 'to', to_func)

    def get_global_name(self, state=None, join=True):
        if isinstance(state, State):
            state = state.name
        domains = self._nested_global_name(state) if state else [s[0].name for s in self._stack] + [self.scoped.name]
        return self.state_cls.separator.join(domains[1:]) if join else domains[1:]

    def _nested_global_name(self, state=None):
        if state in self.states:
            domains = [s[0].name for s in self._stack] + [self.scoped.name] + [state]
            return domains
        else:
            for child in self.states:
                with self(child):
                    domains = self._nested_global_name(state)
                    if domains:
                        return domains
            return []

    def get_local_name(self, state_name, join=True):
        if isinstance(state_name, State):
            if state_name == self.scoped:
                return '' if join else []
            state_name = self.get_global_name(state_name)
        state_name = state_name.split(self.state_cls.separator)
        domains = [s[0].name for s in self._stack[1:]] + [self.scoped.name]
        while domains and state_name[0] == domains[0]:
            state_name.pop(0)
            domains.pop(0)
        return self.state_cls.separator.join(state_name) if join else state_name

    def set_state(self, state, model=None):
        models = self.models if model is None else listify(model)
        for mod in models:
            setattr(mod, self.model_attribute, state)

    def get_state(self, state, hint=None):
        """ Return the State instance with the passed name. """
        if isinstance(state, string_types):
            state = state.split(self.state_cls.separator)
        if not hint:
            hint = state.copy()
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

    def get_triggers(self, *args):
        """ Extends transitions.core.Machine.get_triggers to also include parent state triggers. """
        # add parents to state set
        triggers = []
        for state_name in args:
            state_path = state_name.split(self.state_cls.separator)
            root = state_path[0]
            while state_path:
                triggers.extend(super(NestedMachine, self).get_triggers(self.state_cls.separator.join(state_path)))
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

    def to_state(self, model, state_name, *args, **kwargs):
        """ Helper function to add go to states in case a custom state separator is used.
        Args:
            model (class): The model that should be used.
            state_name (str): Name of the destination state.
        """

        event = EventData(self.get_model_state(model), Event('to', self), self,
                          model, args=args, kwargs=kwargs)
        self._create_transition(getattr(model, self.model_attribute), state_name).execute(event)

# state = {
#     'name': 'B',
#     'states': ['1', '2'],
#     'transitions': [['jo', '2', '1']],
#     'initial': '2'
# }
#
# m = NestedMachine(initial='A', states=['A', state],
#                   transitions=[['go', 'A', 'B'], ['go', 'B_2', 'B_1']])
# m.add_transition('flo', 'B', 'A')
# # print(m.states)
# # print(m.events)
# m.go()
# print(m.state)
# m.jo()
# print(m.state)
# m.flo()
# print(m.state)
# # m.states['B'].events['go'].trigger(m)
# # print('current', m.state)
