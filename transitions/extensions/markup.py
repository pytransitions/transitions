from six import string_types, iteritems
from functools import partial
import itertools
import importlib
from enum import Enum
from collections import defaultdict

from ..core import Machine
import numbers


class MarkupMachine(Machine):

    # Special attributes such as NestedState._name/_parent or Transition._condition are handled differently
    state_attributes = ['on_exit', 'on_enter', 'ignore_invalid_triggers', 'timeout', 'on_timeout', 'tags']
    transition_attributes = ['source', 'dest', 'prepare', 'before', 'after']

    def __init__(self, *args, **kwargs):
        self._markup = kwargs.pop('markup', {})
        self._auto_transitions_markup = kwargs.pop('auto_transitions_markup', False)
        self.skip_references = True

        if self._markup:
            models_markup = self._markup.pop('models', [])
            super(MarkupMachine, self).__init__(None, **self._markup)
            for m in models_markup:
                self._add_markup_model(m)
        else:
            super(MarkupMachine, self).__init__(*args, **kwargs)
            self._markup['initial'] = self.initial
            self._markup['before_state_change'] = [x for x in (rep(f) for f in self.before_state_change) if x]
            self._markup['after_state_change'] = [x for x in (rep(f) for f in self.before_state_change) if x]
            self._markup['prepare_event'] = [x for x in (rep(f) for f in self.prepare_event) if x]
            self._markup['finalize_event'] = [x for x in (rep(f) for f in self.finalize_event) if x]
            self._markup['name'] = "" if not self.name else self.name[:-2]
            self._markup['send_event'] = self.send_event
            self._markup['auto_transitions'] = self.auto_transitions
            self._markup['ignore_invalid_triggers'] = self.ignore_invalid_triggers
            self._markup['queued'] = self.has_queue

    @property
    def auto_transitions_markup(self):
        return self._auto_transitions_markup

    @auto_transitions_markup.setter
    def auto_transitions_markup(self, value):
        self._auto_transitions_markup = value
        self._markup['transitions'] = self._convert_transitions()

    @property
    def markup(self):
        self._markup['models'] = self._convert_models()
        return self._markup

    def add_transition(self, trigger, source, dest, conditions=None,
                       unless=None, before=None, after=None, prepare=None, **kwargs):
        super(MarkupMachine, self).add_transition(trigger, source, dest, conditions=conditions, unless=unless,
                                                  before=before, after=after, prepare=prepare, **kwargs)
        self._markup['transitions'] = self._convert_transitions()

    def add_states(self, states, on_enter=None, on_exit=None, ignore_invalid_triggers=None, **kwargs):
        super(MarkupMachine, self).add_states(states, on_enter=on_enter, on_exit=on_exit,
                                              ignore_invalid_triggers=ignore_invalid_triggers, **kwargs)
        self._markup['states'] = self._convert_states([s for s in self.states.values()
                                                       if not getattr(s, 'parent', False)])

    def _convert_states(self, states):
        markup_states = []
        for state in states:
            s_def = _convert(state, self.state_attributes, self.skip_references)
            if isinstance(state, Enum):
                s_def['name'] = state.name
            else:
                s_def['name'] = getattr(state, '_name', state.name)
            if getattr(state, 'children', False):
                s_def['children'] = self._convert_states(state.children)
            markup_states.append(s_def)
        return markup_states

    def _convert_transitions(self):
        markup_transitions = []
        for event in self.events.values():
            if self._omit_auto_transitions(event):
                continue

            for transitions in event.transitions.items():
                for trans in transitions[1]:
                    t_def = _convert(trans, self.transition_attributes, self.skip_references)
                    t_def['trigger'] = event.name
                    con = [x for x in (rep(f.func, self.skip_references) for f in trans.conditions
                                       if f.target) if x]
                    unl = [x for x in (rep(f.func, self.skip_references) for f in trans.conditions
                                       if not f.target) if x]
                    if con:
                        t_def['conditions'] = con
                    if unl:
                        t_def['unless'] = unl
                    markup_transitions.append(t_def)
        return markup_transitions

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
        for m in self.models:
            model_def = dict(state=m.state)
            model_def['name'] = m.name if hasattr(m, 'name') else str(id(m))
            model_def['class-name'] = 'self' if m == self else m.__module__ + "." + m.__class__.__name__
            models.append(model_def)
        return models

    def _omit_auto_transitions(self, event):
        return self.auto_transitions_markup is False and self._is_auto_transition(event)

    # auto transition events commonly a) start with the 'to_' prefix, followed by b) the state name
    # and c) contain a transition from each state to the target state (including the target)
    def _is_auto_transition(self, event):
        if event.name.startswith('to_') and len(event.transitions) == len(self.states):
            state_name = event.name[len('to_'):]
            if state_name in self.states:
                return True
        return False


def rep(func, skip_references=False):
    """ Return a string representation for `func`. """
    if isinstance(func, string_types):
        return func
    if isinstance(func, numbers.Number):
        return str(func)
    if skip_references:
        return None
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


def _convert(obj, attributes, skip):
    s = {}
    for key in attributes:
        val = getattr(obj, key, False)
        if not val:
            continue
        if isinstance(val, Enum):
            s[key] = val.name
        elif isinstance(val, string_types):
            s[key] = val
        else:
            try:
                s[key] = [rep(v, skip) for v in iter(val)]
            except TypeError:
                s[key] = rep(val, skip)
    return s
