"""
    transitions.extensions.markup
    -----------------------------

    This module extends machines with markup functionality that can be used to retrieve the current machine
    configuration as a dictionary. This is used as the foundation for diagram generation with Graphviz but can
    also be used to store and transfer machines.
"""

from functools import partial
import importlib
import itertools
import numbers

from six import string_types, iteritems

try:
    # Enums are supported for Python 3.4+ and Python 2.7 with enum34 package installed
    from enum import Enum, EnumMeta
except ImportError:
    # If enum is not available, create dummy classes for type checks
    # typing must be prevent redefinition issues with mypy
    class Enum:  # type:ignore
        """ This is just an Enum stub for Python 2 and Python 3.3 and before without Enum support. """

    class EnumMeta:  # type:ignore
        """ This is just an EnumMeta stub for Python 2 and Python 3.3 and before without Enum support. """

from ..core import Machine
from .nesting import HierarchicalMachine


class MarkupMachine(Machine):
    """ Extends transitions.core.Machine with the capability to generate a dictionary representation of itself,
    its events, states and models.
    """

    # Special attributes such as NestedState._name/_parent or Transition._condition are handled differently
    state_attributes = ['on_exit', 'on_enter', 'ignore_invalid_triggers', 'timeout', 'on_timeout', 'tags', 'label']
    transition_attributes = ['source', 'dest', 'prepare', 'before', 'after', 'label']

    def __init__(self, model=Machine.self_literal, states=None, initial='initial', transitions=None,
                 send_event=False, auto_transitions=True,
                 ordered_transitions=False, ignore_invalid_triggers=None,
                 before_state_change=None, after_state_change=None, name=None,
                 queued=False, prepare_event=None, finalize_event=None, model_attribute='state', on_exception=None,
                 markup=None, auto_transitions_markup=False, **kwargs):
        self._markup = markup or {}
        self._auto_transitions_markup = auto_transitions_markup
        self._needs_update = True

        if self._markup:
            # remove models from config to process them AFTER the base machine has been initialized
            models = self._markup.pop('models', [])
            super(MarkupMachine, self).__init__(model=None, **self._markup)
            for mod in models:
                self._add_markup_model(mod)
        else:
            super(MarkupMachine, self).__init__(
                model=model, states=states, initial=initial, transitions=transitions,
                send_event=send_event, auto_transitions=auto_transitions,
                ordered_transitions=ordered_transitions, ignore_invalid_triggers=ignore_invalid_triggers,
                before_state_change=before_state_change, after_state_change=after_state_change, name=name,
                queued=queued, prepare_event=prepare_event, finalize_event=finalize_event,
                model_attribute=model_attribute, on_exception=on_exception, **kwargs
            )
            self._markup['before_state_change'] = [x for x in (rep(f) for f in self.before_state_change) if x]
            self._markup['after_state_change'] = [x for x in (rep(f) for f in self.before_state_change) if x]
            self._markup['prepare_event'] = [x for x in (rep(f) for f in self.prepare_event) if x]
            self._markup['finalize_event'] = [x for x in (rep(f) for f in self.finalize_event) if x]
            self._markup['send_event'] = self.send_event
            self._markup['auto_transitions'] = self.auto_transitions
            self._markup['ignore_invalid_triggers'] = self.ignore_invalid_triggers
            self._markup['queued'] = self.has_queue

    @property
    def auto_transitions_markup(self):
        """ Whether auto transitions should be included in the markup. """
        return self._auto_transitions_markup

    @auto_transitions_markup.setter
    def auto_transitions_markup(self, value):
        """ Whether auto transitions should be included in the markup. """
        self._auto_transitions_markup = value
        self._needs_update = True

    @property
    def markup(self):
        """ Returns the machine's configuration as a markup dictionary.
        Returns:
            dict of machine configuration parameters.
        """
        self._markup['models'] = self._convert_models()
        return self.get_markup_config()

    # the only reason why this not part of markup property is that pickle
    # has issues with properties during __setattr__ (self.markup is not set)
    def get_markup_config(self):
        """ Generates and returns all machine markup parameters except models.
        Returns:
            dict of machine configuration parameters.
        """
        if self._needs_update:
            self._convert_states_and_transitions(self._markup)
            self._needs_update = False
        return self._markup

    def add_transition(self, trigger, source, dest, conditions=None,
                       unless=None, before=None, after=None, prepare=None, **kwargs):
        super(MarkupMachine, self).add_transition(trigger, source, dest, conditions=conditions, unless=unless,
                                                  before=before, after=after, prepare=prepare, **kwargs)
        self._needs_update = True

    def add_states(self, states, on_enter=None, on_exit=None, ignore_invalid_triggers=None, **kwargs):
        super(MarkupMachine, self).add_states(states, on_enter=on_enter, on_exit=on_exit,
                                              ignore_invalid_triggers=ignore_invalid_triggers, **kwargs)
        self._needs_update = True

    @staticmethod
    def format_references(func):
        """ Creates a string representation of referenced callbacks.
        Returns:
            str that represents a callback reference.
        """
        try:
            return func.__name__
        except AttributeError:
            pass
        if isinstance(func, partial):
            return "%s(%s)" % (
                func.func.__name__,
                ", ".join(itertools.chain(
                    (str(_) for _ in func.args),
                    ("%s=%s" % (key, value)
                     for key, value in iteritems(func.keywords if func.keywords else {})))))
        return str(func)

    def _convert_states_and_transitions(self, root):
        state = getattr(self, 'scoped', self)
        if state.initial:
            root['initial'] = state.initial
        if state == self and state.name:
            root['name'] = self.name[:-2]
        self._convert_transitions(root)
        self._convert_states(root)

    def _convert_states(self, root):
        key = 'states' if getattr(self, 'scoped', self) == self else 'children'
        root[key] = []
        for state_name, state in self.states.items():
            s_def = _convert(state, self.state_attributes, self.format_references)
            if isinstance(state_name, Enum):
                s_def['name'] = state_name.name
            else:
                s_def['name'] = state_name
            if getattr(state, 'states', []):
                with self(state_name):
                    self._convert_states_and_transitions(s_def)
            root[key].append(s_def)

    def _convert_transitions(self, root):
        root['transitions'] = []
        for event in self.events.values():
            if self._omit_auto_transitions(event):
                continue

            for transitions in event.transitions.items():
                for trans in transitions[1]:
                    t_def = _convert(trans, self.transition_attributes, self.format_references)
                    t_def['trigger'] = event.name
                    con = [x for x in (rep(f.func, self.format_references) for f in trans.conditions
                                       if f.target) if x]
                    unl = [x for x in (rep(f.func, self.format_references) for f in trans.conditions
                                       if not f.target) if x]
                    if con:
                        t_def['conditions'] = con
                    if unl:
                        t_def['unless'] = unl
                    root['transitions'].append(t_def)

    def _add_markup_model(self, markup):
        initial = markup.get('state', None)
        if markup['class-name'] == 'self':
            self.add_model(self, initial)
        else:
            mod_name, cls_name = markup['class-name'].rsplit('.', 1)
            cls = getattr(importlib.import_module(mod_name), cls_name)
            self.add_model(cls(), initial)

    def _convert_models(self):
        models = []
        for model in self.models:
            state = getattr(model, self.model_attribute)
            model_def = dict(state=state.name if isinstance(state, Enum) else state)
            model_def['name'] = model.name if hasattr(model, 'name') else str(id(model))
            model_def['class-name'] = 'self' if model == self else model.__module__ + "." + model.__class__.__name__
            models.append(model_def)
        return models

    def _omit_auto_transitions(self, event):
        return self.auto_transitions_markup is False and self._is_auto_transition(event)

    # auto transition events commonly a) start with the 'to_' prefix, followed by b) the state name
    # and c) contain a transition from each state to the target state (including the target)
    def _is_auto_transition(self, event):
        if event.name.startswith('to_') and len(event.transitions) == len(self.states):
            state_name = event.name[len('to_'):]
            try:
                _ = self.get_state(state_name)
                return True
            except ValueError:
                pass
        return False

    def _identify_callback(self, name):
        callback_type, target = super(MarkupMachine, self)._identify_callback(name)
        if callback_type:
            self._needs_update = True
        return callback_type, target


class HierarchicalMarkupMachine(MarkupMachine, HierarchicalMachine):
    """ Extends transitions.extensions.nesting.HierarchicalMachine with markup capabilities. """


def rep(func, format_references=None):
    """ Return a string representation for `func`. """
    if isinstance(func, string_types):
        return func
    if isinstance(func, numbers.Number):
        return str(func)
    return format_references(func) if format_references is not None else None


def _convert(obj, attributes, format_references):
    definition = {}
    for key in attributes:
        val = getattr(obj, key, False)
        if not val:
            continue
        if isinstance(val, string_types):
            definition[key] = val
        else:
            try:
                definition[key] = [rep(v, format_references) for v in iter(val)]
            except TypeError:
                definition[key] = rep(val, format_references)
    return definition
