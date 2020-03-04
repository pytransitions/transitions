from transitions.core import State, Machine, Transition, Event, listify, EventData, _get_trigger

from collections import OrderedDict
import logging
from six import string_types
import inspect
from functools import partial

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())


class NestedEvent(Event):

    def _trigger(self, model, state_name, *args, **kwargs):
        substates = state_name.split(self.machine.state_cls.separator)
        state_name = substates.pop(0)
        while substates and state_name not in self.transitions:
            state_name += self.machine.state_cls.separator + substates.pop(0)
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
        self.states[state.name] = state


class NestedTransition(Transition):

    def _change_state(self, event_data):
        model = event_data.model
        machine = event_data.machine
        src_state = event_data.state
        src_name = machine.get_local_name(src_state, join=False)
        dst_name = machine.get_local_name(self.dest, join=False)
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
            src_name = event_data.machine.get_local_name(event_data.state, join=False)
            dst_name = event_data.machine.get_local_name(self.dest, join=False)
            if src_name:
                with event_data.machine(src_name.pop(0)):
                    self._exit_nested(src_name, event_data)
            if dst_name:
                with event_data.machine(dst_name.pop(0)):
                    dest_name = self._enter_nested(dst_name, event_data)
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

    def get_nested_triggers(self):
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

                for trigger in self.get_nested_triggers():
                    self._add_trigger_to_model(trigger, mod)

                for state in self.states.values():
                    self._add_model_to_state(state, mod)

                self.set_state(initial, model=mod)
                self.models.append(mod)

    def _add_model_to_state(self, state, model):
        name = self.get_global_name(state)
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
        self._checked_assignment(model, trigger, partial(self._trigger_event, model, trigger))

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

    def get_state(self, state):
        """ Return the State instance with the passed name. """
        if isinstance(state, string_types):
            state = state.split(self.state_cls.separator)

        if len(state) > 1:
            child = state.pop(0)
            try:
                with self(child):
                    return self.get_state(state)
            except KeyError:
                return self.get_global_state(state)
        elif state[0] not in self.states:
            raise ValueError("State '%s' is not a registered state." % state)
        return self.states[state[0]]

    def get_global_state(self, state):
        states = self._stack[0][1] if self._stack else self.states
        domains = [s[0].name for s in self._stack] + [self.scoped.name] + state
        for sco in domains[1:]:
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

    def __enter__(self):
        self._stack.append((self.scoped, self.states, self.events))
        self.scoped, self.states, self.events = self._next_scope
        self._next_scope = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.scoped, self.states, self.events = self._stack.pop()


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
