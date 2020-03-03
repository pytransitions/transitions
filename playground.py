from transitions.core import State, Machine, Transition, Event, listify, EventData, _get_trigger

from collections import OrderedDict
import logging
from six import string_types
from copy import copy
from functools import partial

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())

# class StateContext:
#
#     separator = '_'
#
#     def __init__(self, *args, **kwargs):
#         self.states = OrderedDict()
#         self.events = {}
#         self.parent = None
#         self._enter_state = None
#         super(StateContext, self).__init__(*args, **kwargs)
#
#     def add_substate(self, state):
#         self.states[state.name] = state
#         state.parent = self
#
#     @property
#     def name(self):
#         return self.parent.name + self.separator + self._name if self.parent else self._name
#
#     @property
#     def value(self):
#         return self.name if isinstance(self._name, string_types) else super(NestedState, self).value
#
#     @property
#     def namespace(self):
#         return self.parent.namespace + [self._name] if self.parent else [self._name]
#
#     @name.setter
#     def name(self, value):
#         self._name = value
#
#     def get_state(self, state_name):
#         if isinstance(state_name, string_types):
#             state_name = state_name.split(self.separator)
#         if len(state_name) > 1:
#             with self(state_name.pop(0)) as state:
#                 return state.get_state(state_name)
#         else:
#             return self.states[state_name[0]]


class NestedEvent(Event):

    def _trigger(self, model, state, *args, **kwargs):
        if state.name in self.transitions:
            event_data = EventData(state, self, self.machine, model, args=args, kwargs=kwargs)
            return self._process(event_data)
        else:
            return False


class NestedState(State):

    separator = '_'

    def __init__(self, name, on_enter=None, on_exit=None, ignore_invalid_triggers=None, initial=None, parent=None):
        super(NestedState, self).__init__(name=name, on_enter=on_enter, on_exit=on_exit,
                                          ignore_invalid_triggers=ignore_invalid_triggers)
        self.initial = initial
        self.events = {}
        self.states = OrderedDict()
        self._parent = None
        self.parent = parent

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        self._parent = value
        if self._parent is not None:
            self._parent.states[self._name] = self

    @property
    def name(self):
        name = super(NestedState, self).name
        return self.parent.name + self.separator + name if self.parent is not None else name

    @property
    def value(self):
        return self.name if isinstance(self._name, string_types) else super(NestedState, self).value

    def enter(self, event_data):
        super(NestedState, self).enter(event_data)
        if self.initial:
            return self.states[self.initial].enter(event_data)
        else:
            return self


class NestedTransition(Transition):

    def _change_state(self, event_data):
        model = event_data.model
        machine = event_data.machine
        src_state = event_data.state
        dest_state = machine.get_state(self.dest)
        src_state.exit(event_data)
        res = dest_state.enter(event_data)
        event_data.machine.set_state(res, model)
        event_data.update(dest_state)


class NestedMachine(Machine):

    state_cls = NestedState
    transition_cls = NestedTransition
    event_cls = NestedEvent

    def __init__(self, *args, **kwargs):
        self._stack = []
        self.scoped = None
        super(NestedMachine, self).__init__(*args, **kwargs)

    def add_states(self, states, on_enter=None, on_exit=None, ignore_invalid_triggers=None, **kwargs):
        for state in listify(states):
            if isinstance(state, string_types):
                self.states[state] = self._create_state(state, parent=self.scoped)
            elif isinstance(state, dict):
                # state = copy(state)
                # if 'ignore_invalid_triggers' not in state:
                #     state['ignore_invalid_triggers'] = ignore
                state_children = state.pop('states')  # throws KeyError when no children set
                state['parent'] = self.scoped
                transitions = state.pop('transitions', [])
                new_state = self._create_state(**state)
                self.states[new_state.name] = new_state
                with self(new_state):
                    if transitions:
                        self.add_transitions(transitions)
                    self.add_states(state_children)

    def _get_nested_triggers(self):

        triggers = list(self.events.keys())
        for state in self.states.values():
            with self(state):
                triggers.extend(self._get_nested_triggers())
        return triggers

    def _get_nested_states(self):
        states = list(self.states.values())
        for state in self.states.values():
            with self(state):
                states.extend(self._get_nested_states())
        return states

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
                self._checked_assignment(mod, 'trigger', partial(_get_trigger, mod, self))

                for trigger in self._get_nested_triggers():
                    self._add_trigger_to_model(trigger, mod)

                for state in self._get_nested_states():
                    self._add_model_to_state(state, mod)

                self.set_state(initial, model=mod)
                self.models.append(mod)

    def _add_trigger_to_model(self, trigger, model):
        self._checked_assignment(model, trigger, partial(self._trigger_event, model, trigger))

    def _trigger_event(self, model, trigger, *args, **kwargs):
        state = self.get_model_state(model)
        if state == self.scoped:
            return False
        if trigger in self.events:
            res = self.events[trigger]._trigger(model, state, *args, **kwargs)
        else:
            res = False
        if not res:
            with self(state):
                self._trigger_event(model, trigger, *args, **kwargs)

    def get_state(self, state):
        idx = len(self._stack) if self._stack else 0
        scope = state.split(self.state_cls.separator)[idx:]
        scoped = self.scoped if self.scoped else self
        while len(scope) > 1:
            scoped = scoped.states[scope.pop(0)]
        if not scope:
            return scoped
        if scope[0] not in scoped.states:
            raise ValueError("State '%s' is not a registered state." % state)
        return scoped.states[scope[0]]

    def __call__(self, child):
        states = [child]
        state = child
        while state.parent:
            states.append(state.parent)
            state = state.parent

        idx = 1
        states = [None] + states[::-1]
        while len(self._stack) > idx and states[idx] == self._stack[idx][0]:
            idx += 1
        if states[idx] == self.scoped:
            idx += 1
        self._child = states[idx]
        return self

    def __enter__(self):
        self._stack.append((self.scoped, self.states, self.events))
        self.scoped = self._child
        self.states = self.scoped.states
        self.events = self.scoped.events
        self._child = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.scoped, self.states, self.events = self._stack.pop()


state = {
    'name': 'B',
    'states': ['1', '2'],
    'transitions': [['jo', '2', '1']],
    'initial': '2'
}

m = NestedMachine(initial='A', states=['A', state],
                  transitions=[['go', 'A', 'B'], ['go', 'B_2', 'B_1']])
# print(m.states)
# print(m.events)
m.go()
m.jo()
print(m.state)
# m.states['B'].events['go'].trigger(m)
# print('current', m.state)
