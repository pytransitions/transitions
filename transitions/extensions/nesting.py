from ..core import Machine, Transition, State, listify

from six import string_types
from os.path import commonprefix
import copy

import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# Added parent and children parameter children is a list of NestedStates
# and parent is the full name of the parent e.g. Foo_Bar_Baz.
class NestedState(State):

    def __init__(self, name, on_enter=None, on_exit=None, ignore_invalid_triggers=None, children=None, parent=None):
        super(NestedState, self).__init__(name=name, on_enter=on_enter, on_exit=on_exit,
                                          ignore_invalid_triggers=ignore_invalid_triggers)
        self.children = children
        self.parent = parent

    # A step with children will be initialized with the first child which
    # is a Leaf in the hierarchical tree and does not contain further children.
    def get_initial(self):
        state = self.children[0] if self.children is not None else self
        return state.get_initial() if state.children is not None else state


class NestedTransition(Transition):

    # The actual state change method 'execute' in Transition was restructured to allow overriding
    def _change_state(self, event_data):
        machine = event_data.machine
        dest_state = machine.get_state(self.dest)
        source_state = machine.get_state(self.source)
        shared_parent = None

        # First, we want to figure out if source and destination share
        # parent states. We do a simple string comparison.
        # E.g. Foo_Bar_Baz1_A and Foo_Ball_Boo_B will share 'Foo_Ba' which will be resolved later
        if source_state.parent is not None and dest_state.parent is not None:
            shared_parent = commonprefix([source_state.parent, dest_state.parent])

        while True:
            # We use the shared_parent to exit all parent states of the source which are not parents of destination
            source_state.exit(event_data)
            source_parent = source_state.parent

            # The loop is ended if we reach a root state or if source's parent is part of the shared_parent string
            # E.g. for Foo_Bar_Baz1_A with shared_parent Foo_Ba, Foo will not be exited.
            if source_parent is None or (shared_parent is not None and shared_parent.startswith(source_parent)):
                break
            source_state = machine.get_state(source_parent)

        enter_queue = []

        # Now we have to enter all the parent states of destination EXCEPT the ones still active (the shared_parents)
        # we achieve by generating a list top down from destination to shared parent
        source_name = machine.get_state(source_state.parent).name if source_state.parent is not None else None

        # If destination contains children, get the leaf state
        if dest_state.children is not None:
            dest_state = dest_state.get_initial()
        tmp_state = dest_state
        while True:
            # All states will be pushed into a list starting from the
            # destination state until the shared parent is reached
            enter_queue.append(tmp_state)
            if tmp_state.parent == source_name:
                break
            tmp_state = machine.get_state(tmp_state.parent)

        # change the active state
        event_data.machine.set_state(dest_state.name)
        event_data.update()

        # enter all states of the queue in reversed order, starting from topmost state
        for s in enter_queue[::-1]:
            s.enter(event_data)


class HierarchicalMachine(Machine):

    def __init__(self, *args, **kwargs):
        self.blueprints = {'states': [], 'transitions': []}
        self._buffered_transitions = []
        super(HierarchicalMachine, self).__init__(*args, **kwargs)

        # if the initial state is no leaf, traverse the tree
        initial = self.get_state(self._initial)
        if initial.children is not None:
            initial = initial.get_initial()
            self._initial = initial.name
            self.set_state(initial)
            self._last_state = initial

    # Instead of creating transitions directly, Machine now use a factory method which can be overridden
    @staticmethod
    def _create_transition(*args, **kwargs):
        return NestedTransition(*args, **kwargs)

    # The chosen approach for hierarchical state machines was 'flatten' which means that nested states
    # are converted into linked states with a naming scheme that concatenates the state name with
    # its parent's name. Substate Bar of Foo becomes Foo_Bar. An alternative approach would be to use actual nested
    # state machines.
    def _flatten(self, states, on_enter=None, on_exit=None,
                 ignore_invalid_triggers=None, parent=None, remap={}):
        states = listify(states)
        new_states = []
        ignore = ignore_invalid_triggers
        if ignore is None:
            ignore = self.ignore_invalid_triggers
        prefix = (parent + '_') if parent is not None else ''
        for state in states:
            tmp_states = []
            # other state representations are handled almost like in the base class but a parent parameter is added
            if isinstance(state, string_types):
                if state in remap:
                    continue
                tmp_states.append(NestedState(prefix + state, on_enter=on_enter, on_exit=on_exit, parent=parent,
                                              ignore_invalid_triggers=ignore))
            elif isinstance(state, dict):
                state = copy.deepcopy(state)
                if 'ignore_invalid_triggers' not in state:
                    state['ignore_invalid_triggers'] = ignore
                state['parent'] = parent
                state['name'] = prefix + state['name']

                if 'children' in state:

                    # Concat the state names with the current scope. The scope is the concatenation of all
                    # previous parents. Call _flatten again to check for more nested states.
                    children = self._flatten(state['children'], on_enter=on_enter, on_exit=on_exit,
                                             ignore_invalid_triggers=ignore,
                                             parent=state['name'], remap=state.get('remap', {}))
                    state['children'] = children
                    state.pop('remap', None)
                    tmp_states.extend(children)

                tmp_states.insert(0, NestedState(**state))
            elif isinstance(state, HierarchicalMachine):
                tmp_states.extend(self._flatten(state.blueprints['states'], on_enter=on_enter, on_exit=on_exit,
                                                ignore_invalid_triggers=ignore,
                                                parent=parent, remap=remap))
                for trans in state.blueprints['transitions']:
                    source = trans['source']
                    source = prefix + source if not source == '*' else source
                    dest = prefix + trans['dest'] if trans['dest'] not in remap else remap[trans['dest']]
                    self._buffered_transitions.append((trans['trigger'], source, dest, trans.get('conditions', None),
                                                       trans.get('unless', None), trans.get('before', None),
                                                       trans.get('after', None)))
            elif isinstance(state, NestedState):
                tmp_states.append(state)
                if state.children:
                    tmp_states.extend(self._flatten(state.children))
            new_states.extend(tmp_states)
        return new_states

    def _to_blueprint(self, states):
        states = listify(states)
        blueprints = []
        for state in states:
            if isinstance(state, string_types):
                bp = state
            elif isinstance(state, dict):
                bp = copy.deepcopy(state)
                bp.pop('parent', None)
                if 'children' in state:
                    bp['children'] = self._to_blueprint(state['children'])
            elif isinstance(state, NestedState):
                bp = {'name': state.name, 'on_enter': state.on_enter, 'on_exit': state.on_exit,
                      'ignore_invalid_triggers': state.ignore_invalid_triggers}
                if state.children is not None:
                    bp['children'] = self._to_blueprint(state.children)
            elif isinstance(state, Machine):
                # this happens if there
                if len(states) > 1:
                    raise ValueError("States arrays and nested machines cannot be mixed!")
                return state.blueprints['states']
            else:
                raise ValueError('Do not know state of type %s' % type(state))

            blueprints.append(bp)
        return blueprints

    def add_states(self, states, *args, **kwargs):
        self.blueprints['states'].extend(self._to_blueprint(states))

        # preprocess states to flatten the configuration and resolve nesting
        new_states = self._flatten(states, *args, **kwargs)
        super(HierarchicalMachine, self).add_states(new_states, *args, **kwargs)
        while len(self._buffered_transitions) > 0:
            args = self._buffered_transitions.pop()
            self.add_transition(*args)

    # collect the names of all children of a list of NestedSets
    def _traverse_nested(self, children):
        names = []
        for c in children:
            if c.children is not None:
                names.extend(self._traverse_nested(c.children))
            else:
                names.append(c.name)
        return names

    def add_transition(self, trigger, source, dest, conditions=None,
                       unless=None, before_transition=None, after=None, before_check=None, before=None):
        if not (trigger.startswith('to_') and source == '*'):
            bp_before_transition = before_transition if before_transition else before
            bp_before_check = before_check
            bp_after = after
            if self.before_state_change:
                bp_before_transition = listify(before_transition) + listify(self.before_state_change)
                bp_before_check = listify(before_check) + listify(self.before_state_change)
            if self.after_state_change:
                bp_after = listify(after) + listify(self.after_state_change)
            self.blueprints['transitions'].append({'trigger': trigger, 'source': source, 'dest': dest,
                                                   'conditions': conditions, 'unless': unless,
                                                   'before_transition': bp_before_transition,
                                                   'before_check': bp_before_check,
                                                   'after': bp_after})
        if isinstance(source, string_types):
            source = [x.name for x in self.states.values() if x.children is None] \
                if source == '*' else [source]

        for s in source:
            state = self.get_state(s)
            # if a transition should be possible from a branch state,
            # it should be possible from all its children as well.
            # e.g. C -advance-> A will also create C_1 -advance-> A, C_4_U -advance-> A and so so.
            if state.children is not None:
                source.remove(s)
                source.extend(self._traverse_nested(state.children))

        super(HierarchicalMachine, self).add_transition(trigger, source, dest, conditions=conditions, unless=unless,
                                                        before_check=before_check, before_transition=before_transition,
                                                        after=after)
