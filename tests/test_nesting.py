# -*- coding: utf-8 -*-

try:
    from builtins import object
except ImportError:
    pass

import sys
import tempfile
from os.path import getsize
from os import unlink

from transitions.extensions.nesting import NestedState
from transitions.extensions import MachineFactory

from unittest import skipIf
from .test_core import TestTransitions, TestCase
from .utils import Stuff, DummyModel

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

try:
    # Just to skip tests if graphviz not installed
    import graphviz as pgv  # @UnresolvedImport
except ImportError:  # pragma: no cover
    pgv = None


default_separator = NestedState.separator


class Dummy(object):
    pass


test_states = ['A', 'B',
               {'name': 'C', 'children': ['1', '2', {'name': '3', 'children': ['a', 'b', 'c']}]}, 'D', 'E', 'F']


class TestNestedTransitions(TestTransitions):

    def setUp(self):
        self.states = test_states
        self.machine_cls = MachineFactory.get_predefined(nested=True)
        self.state_cls = NestedState
        self.stuff = Stuff(self.states, self.machine_cls)

    def test_add_model(self):
        model = Dummy()
        self.stuff.machine.add_model(model, initial='E')

    def test_init_machine_with_hella_arguments(self):
        states = [
            self.state_cls('State1'),
            'State2',
            {
                'name': 'State3',
                'on_enter': 'hello_world'
            }
        ]
        transitions = [
            {'trigger': 'advance',
                'source': 'State2',
                'dest': 'State3'
             }
        ]
        s = Stuff()
        self.stuff.machine_cls(
            model=s, states=states, transitions=transitions, initial='State2')
        s.advance()
        self.assertEqual(s.message, 'Hello World!')

    def test_init_machine_with_nested_states(self):
        State = self.state_cls
        a = State('A')
        b = State('B')
        b_1 = State('1')
        b_2 = State('2')
        b.add_substate(b_1)
        b.add_substates([b_2])
        m = self.stuff.machine_cls(states=[a, b])
        self.assertEqual(m.states['B'].states['1'], b_1)
        m.to("B{0}1".format(State.separator))
        self.assertEqual(m.state, "B{0}1".format(State.separator))

    def test_property_initial(self):
        # Define with list of dictionaries
        states = ['A', 'B', {'name': 'C', 'children': ['1', '2', '3']}, 'D']
        # Define with list of dictionaries
        transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'B'},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'D'}
        ]
        m = self.stuff.machine_cls(states=states, transitions=transitions, initial='A')
        self.assertEqual(m.initial, 'A')
        m = self.stuff.machine_cls(states=states, transitions=transitions, initial='C')
        self.assertEqual(m.initial, 'C')
        m = self.stuff.machine_cls(states=states, transitions=transitions)
        self.assertEqual(m.initial, 'initial')

    def test_transition_definitions(self):
        State = self.state_cls
        states = ['A', 'B', {'name': 'C', 'children': ['1', '2', '3']}, 'D']
        # Define with list of dictionaries
        transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'B'},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'D'},
            {'trigger': 'run', 'source': 'C', 'dest': 'C%s1' % State.separator}
        ]
        m = self.stuff.machine_cls(states=states, transitions=transitions, initial='A')
        m.walk()
        self.assertEqual(m.state, 'B')
        m.run()
        self.assertEqual(m.state, 'C')
        m.run()
        self.assertEqual(m.state, 'C%s1' % State.separator)
        # Define with list of lists
        transitions = [
            ['walk', 'A', 'B'],
            ['run', 'B', 'C'],
            ['sprint', 'C', 'D']
        ]
        m = self.stuff.machine_cls(states=states, transitions=transitions, initial='A')
        m.to_C()
        m.sprint()
        self.assertEqual(m.state, 'D')

    def test_nested_definitions(self):
        separator = self.state_cls.separator
        state = {
            'name': 'B',
            'children': ['1', '2'],
            'transitions': [['jo', '1', '2']],
            'initial': '2'
        }
        m = self.stuff.machine_cls(initial='A', states=['A', state],
                                   transitions=[['go', 'A', 'B'], ['go', 'B{0}2'.format(separator),
                                                                   'B{0}1'.format(separator)]])
        self.assertTrue(m.is_A())
        m.go()
        self.assertEqual(m.state, 'B{0}2'.format(separator))
        m.go()
        self.assertEqual(m.state, 'B{0}1'.format(separator))
        m.jo()

    def test_transitioning(self):
        s = self.stuff
        s.machine.add_transition('advance', 'A', 'B')
        s.machine.add_transition('advance', 'B', 'C')
        s.machine.add_transition('advance', 'C', 'D')
        s.machine.add_transition('reset', '*', 'A')
        self.assertEqual(len(s.machine.events['reset'].transitions), 6)
        self.assertEqual(len(s.machine.events['reset'].transitions['C']), 1)
        s.advance()
        self.assertEqual(s.state, 'B')
        self.assertFalse(s.is_A())
        self.assertTrue(s.is_B())
        s.advance()
        self.assertEqual(s.state, 'C')

    def test_conditions(self):
        s = self.stuff
        s.machine.add_transition('advance', 'A', 'B', conditions='this_passes')
        s.machine.add_transition('advance', 'B', 'C', unless=['this_fails'])
        s.machine.add_transition('advance', 'C', 'D', unless=['this_fails',
                                                              'this_passes'])
        s.advance()
        self.assertEqual(s.state, 'B')
        s.advance()
        self.assertEqual(s.state, 'C')
        s.advance()
        self.assertEqual(s.state, 'C')

    def test_multiple_add_transitions_from_state(self):
        State = self.state_cls
        s = self.stuff
        s.machine.add_transition(
            'advance', 'A', 'B', conditions=['this_fails'])
        s.machine.add_transition('advance', 'A', 'C')
        s.machine.add_transition('advance', 'C', 'C%s2' % State.separator)
        s.advance()
        self.assertEqual(s.state, 'C')
        s.advance()
        self.assertEqual(s.state, 'C%s2' % State.separator)
        self.assertFalse(s.is_C())
        self.assertTrue(s.is_C(allow_substates=True))

    def test_use_machine_as_model(self):
        states = ['A', 'B', 'C', 'D']
        m = self.stuff.machine_cls(states=states, initial='A')
        m.add_transition('move', 'A', 'B')
        m.add_transition('move_to_C', 'B', 'C')
        m.move()
        self.assertEqual(m.state, 'B')

    def test_add_custom_state(self):
        State = self.state_cls
        s = self.stuff
        s.machine.add_states([{'name': 'E', 'children': ['1', '2']}])
        s.machine.add_state('E%s3' % State.separator)
        s.machine.add_transition('go', '*', 'E%s1' % State.separator)
        s.machine.add_transition('walk', '*', 'E%s3' % State.separator)
        s.machine.add_transition('run', 'E', 'C{0}3{0}a'.format(State.separator))
        s.go()
        self.assertEqual('E{0}1'.format(State.separator), s.state)
        s.walk()
        self.assertEqual('E{0}3'.format(State.separator), s.state)
        s.run()
        self.assertEqual('C{0}3{0}a'.format(State.separator), s.state)

    def test_add_nested_state(self):
        m = self.machine_cls(states=['A'], initial='A')
        m.add_state('B{0}1{0}a'.format(self.state_cls.separator))
        self.assertIn('B', m.states)
        self.assertIn('1', m.states['B'].states)
        self.assertIn('a', m.states['B'].states['1'].states)

        with self.assertRaises(ValueError):
            m.add_state(m.states['A'])

    def test_enter_exit_nested_state(self):
        State = self.state_cls
        mock = MagicMock()

        def callback():
            mock()
        states = ['A', 'B', {'name': 'C', 'on_enter': callback, 'on_exit': callback,
                             'children': [{'name': '1', 'on_enter': callback, 'on_exit': callback}, '2', '3']},
                            {'name': 'D', 'on_enter': callback, 'on_exit': callback}]
        transitions = [['go', 'A', 'C{0}1'.format(State.separator)],
                       ['go', 'C', 'D']]
        m = self.stuff.machine_cls(states=states, transitions=transitions, initial='A')
        m.go()
        self.assertTrue(mock.called)
        self.assertEqual(2, mock.call_count)
        m.go()
        self.assertTrue(m.is_D())
        self.assertEqual(5, mock.call_count)
        m.to_C()
        self.assertEqual(7, mock.call_count)
        m.to('C{0}1'.format(State.separator))
        self.assertEqual(8, mock.call_count)
        m.to('C{0}2'.format(State.separator))
        self.assertEqual(9, mock.call_count)

    def test_ordered_transitions(self):
        State = self.state_cls
        states = [{'name': 'first', 'children': ['second', 'third', {'name': 'fourth', 'children': ['fifth', 'sixth']},
                                                 'seventh']}, 'eighth', 'ninth']
        m = self.stuff.machine_cls(states=states)
        m.add_ordered_transitions()
        self.assertEqual('initial', m.state)
        m.next_state()
        self.assertEqual('first', m.state)
        m.next_state()
        m.next_state()
        self.assertEqual('first{0}third'.format(State.separator), m.state)
        m.next_state()
        m.next_state()
        self.assertEqual('first{0}fourth{0}fifth'.format(State.separator), m.state)
        m.next_state()
        m.next_state()
        self.assertEqual('first{0}seventh'.format(State.separator), m.state)
        m.next_state()
        m.next_state()
        self.assertEqual('ninth', m.state)

        # Include initial state in loop
        m = self.stuff.machine_cls('self', states)
        m.add_ordered_transitions(loop_includes_initial=False)
        m.to_ninth()
        m.next_state()
        self.assertEqual(m.state, 'first')

        # Test user-determined sequence and trigger name
        m = self.stuff.machine_cls('self', states, initial='first')
        m.add_ordered_transitions(['first', 'ninth'], trigger='advance')
        m.advance()
        self.assertEqual(m.state, 'ninth')
        m.advance()
        self.assertEqual(m.state, 'first')

        # Via init argument
        m = self.stuff.machine_cls('self', states, initial='first', ordered_transitions=True)
        m.next_state()
        self.assertEqual(m.state, 'first{0}second'.format(State.separator))

    def test_pickle(self):
        print("separator", self.state_cls.separator)
        if sys.version_info < (3, 4):
            import dill as pickle
        else:
            import pickle

        states = ['A', 'B', {'name': 'C', 'children': ['1', '2', {'name': '3', 'children': ['a', 'b', 'c']}]},
                  'D', 'E', 'F']
        transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'B'},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'D'}
        ]
        m = self.stuff.machine_cls(states=states, transitions=transitions, initial='A')
        m.walk()
        dump = pickle.dumps(m)
        self.assertIsNotNone(dump)
        m2 = pickle.loads(dump)
        self.assertEqual(m.state, m2.state)
        m2.run()
        m2.to_C_3_a()
        m2.to_C_3_b()

    def test_callbacks_duplicate(self):

        transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'C', 'before': 'before_change',
             'after': 'after_change'},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'}
        ]

        m = self.stuff.machine_cls(states=['A', 'B', 'C'], transitions=transitions,
                                   before_state_change='before_change',
                                   after_state_change='after_change', send_event=True,
                                   initial='A', auto_transitions=True)

        m.before_change = MagicMock()
        m.after_change = MagicMock()

        m.walk()
        self.assertEqual(m.before_change.call_count, 2)
        self.assertEqual(m.after_change.call_count, 2)

    def test_example_one(self):
        State = self.state_cls
        State.separator = '_'
        states = ['standing', 'walking', {'name': 'caffeinated', 'children': ['dithering', 'running']}]
        transitions = [['walk', 'standing', 'walking'],
                       ['stop', 'walking', 'standing'],
                       ['drink', '*', 'caffeinated'],
                       ['walk', 'caffeinated', 'caffeinated_running'],
                       ['relax', 'caffeinated', 'standing']]
        machine = self.stuff.machine_cls(states=states, transitions=transitions, initial='standing',
                                         ignore_invalid_triggers=True, name='Machine 1')

        machine.walk()   # Walking now
        machine.stop()   # let's stop for a moment
        machine.drink()  # coffee time
        machine.state
        self.assertEqual(machine.state, 'caffeinated')
        machine.walk()   # we have to go faster
        self.assertEqual(machine.state, 'caffeinated_running')
        machine.stop()   # can't stop moving!
        machine.state
        self.assertEqual(machine.state, 'caffeinated_running')
        machine.relax()  # leave nested state
        machine.state    # phew, what a ride
        self.assertEqual(machine.state, 'standing')
        machine.to_caffeinated_running()  # auto transition fast track
        machine.on_enter_caffeinated_running('callback_method')

    def test_multiple_models(self):
        class Model(object):
            pass
        s1, s2 = Model(), Model()
        m = self.stuff.machine_cls(model=[s1, s2], states=['A', 'B', 'C'], initial='A')
        self.assertEqual(len(m.models), 2)
        m.add_transition('advance', 'A', 'B')
        self.assertNotEqual(s1.advance, s2.advance)
        s1.advance()
        self.assertEqual(s1.state, 'B')
        self.assertEqual(s2.state, 'A')

    def test_excessive_nesting(self):
        states = [{'name': 'A', 'children': []}]
        curr = states[0]
        for i in range(10):
            curr['children'].append({'name': str(i), 'children': []})
            curr = curr['children'][0]
        m = self.stuff.machine_cls(states=states, initial='A')

    def test_intial_state(self):
        separator = self.state_cls.separator
        states = [{'name': 'A', 'children': ['1', '2'], 'initial': '2'},
                  {'name': 'B', 'initial': '2',
                   'children': ['1', {'name': '2', 'initial': 'a',
                                      'children': ['a', 'b']}]}]
        transitions = [['do', 'A', 'B'],
                       ['do', 'B{0}2'.format(separator),
                        'B{0}1'.format(separator)]]
        m = self.stuff.machine_cls(states=states, transitions=transitions, initial='A')
        self.assertEqual(m.state, 'A{0}2'.format(separator))
        m.do()
        self.assertEqual(m.state, 'B{0}2{0}a'.format(separator))
        self.assertTrue(m.is_B(allow_substates=True))
        m.do()
        self.assertEqual(m.state, 'B{0}1'.format(separator))

    def test_get_triggers(self):
        seperator = self.state_cls.separator
        states = ['standing', 'walking', {'name': 'caffeinated', 'children': ['dithering', 'running']}]
        transitions = [
            ['walk', 'standing', 'walking'],
            ['go', 'standing', 'walking'],
            ['stop', 'walking', 'standing'],
            {'trigger': 'drink', 'source': '*', 'dest': 'caffeinated{0}dithering'.format(seperator),
             'conditions': 'is_hot', 'unless': 'is_too_hot'},
            ['walk', 'caffeinated{0}dithering'.format(seperator), 'caffeinated{0}running'.format(seperator)],
            ['relax', 'caffeinated', 'standing']
        ]

        machine = self.stuff.machine_cls(states=states, transitions=transitions, auto_transitions=False)
        trans = machine.get_triggers('caffeinated{0}dithering'.format(seperator))
        self.assertEqual(len(trans), 3)
        self.assertTrue('relax' in trans)

    def test_internal_transitions(self):
        s = self.stuff
        s.machine.add_transition('internal', 'A', None, prepare='increase_level')
        s.internal()
        self.assertEqual(s.state, 'A')
        self.assertEqual(s.level, 2)

    def test_transition_with_unknown_state(self):
        s = self.stuff
        with self.assertRaises(ValueError):
            s.machine.add_transition('next', 'A', s.machine.state_cls('X'))

    def test_skip_to_override(self):
        mock = MagicMock()

        class Model:

            def to(self):
                mock()

        model1 = Model()
        model2 = DummyModel()
        machine = self.machine_cls([model1, model2], states=['A', 'B'], initial='A')
        model1.to()
        model2.to('B')
        self.assertTrue(mock.called)
        self.assertTrue(model2.is_B())

    def test_trigger_parent(self):
        parent_mock = MagicMock()
        exit_mock = MagicMock()
        enter_mock = MagicMock()

        class Model():

            def on_exit_A(self):
                parent_mock()

            def on_exit_A_1(self):
                exit_mock()

            def on_enter_A_2(self):
                enter_mock()

        model = Model()
        machine = self.machine_cls(model, states=[{'name': 'A', 'children': ['1', '2']}],
                                   transitions=[['go', 'A', 'A_2'], ['enter', 'A', 'A_1']], initial='A')

        model.enter()
        self.assertFalse(parent_mock.called)
        model.go()
        self.assertTrue(exit_mock.called)
        self.assertTrue(enter_mock.called)
        self.assertFalse(parent_mock.called)


class TestSeparatorsBase(TestCase):

    separator = default_separator

    def setUp(self):

        class CustomNestedState(NestedState):
            separator = self.separator

        class CustomHierarchicalMachine(MachineFactory.get_predefined(nested=True)):
            state_cls = CustomNestedState

        self.states = test_states
        self.machine_cls = CustomHierarchicalMachine
        self.state_cls = CustomNestedState
        self.stuff = Stuff(self.states, self.machine_cls)

    def test_enter_exit_nested(self):
        separator = self.state_cls.separator
        s = self.stuff
        s.machine.add_transition('advance', 'A', 'C{0}3'.format(separator))
        s.machine.add_transition('reverse', 'C', 'A')
        s.machine.add_transition('lower', ['C{0}1'.format(separator),
                                           'C{0}3'.format(separator)], 'C{0}3{0}a'.format(separator))
        s.machine.add_transition('rise', 'C{0}3'.format(separator), 'C{0}1'.format(separator))
        s.machine.add_transition('fast', 'A', 'C{0}3{0}a'.format(separator))

        for state_name in s.machine.get_nested_state_names():
            state = s.machine.get_state(state_name)
            state.on_enter.append('increase_level')
            state.on_exit.append('decrease_level')

        s.advance()
        self.assertEqual('C{0}3'.format(separator), s.state)
        self.assertEqual(2, s.level)
        self.assertEqual(3, s.transitions)  # exit A; enter C,3
        s.lower()
        self.assertEqual(s.state, 'C{0}3{0}a'.format(separator))
        self.assertEqual(3, s.level)
        self.assertEqual(4, s.transitions)  # enter a
        s.rise()
        self.assertEqual('C%s1' % separator, s.state)
        self.assertEqual(2, s.level)
        self.assertEqual(7, s.transitions)  # exit a, 3; enter 1
        s.reverse()
        self.assertEqual('A', s.state)
        self.assertEqual(1, s.level)
        self.assertEqual(10, s.transitions)  # exit 1, C; enter A
        s.fast()
        self.assertEqual(s.state, 'C{0}3{0}a'.format(separator))
        self.assertEqual(s.level, 3)
        self.assertEqual(s.transitions, 14)  # exit A; enter C, 3, a
        s.to_A()
        self.assertEqual(s.state, 'A')
        self.assertEqual(s.level, 1)
        self.assertEqual(s.transitions, 18)  # exit a, 3, C; enter A
        s.to_A()
        self.assertEqual(s.state, 'A')
        self.assertEqual(s.level, 1)
        self.assertEqual(s.transitions, 20)  # exit A; enter A
        if separator == '_':
            s.to_C_3_a()
        else:
            print("separator", separator)
            s.to_C.s3.a()
        self.assertEqual(s.state, 'C{0}3{0}a'.format(separator))
        self.assertEqual(s.level, 3)
        self.assertEqual(s.transitions, 24)  # exit A; enter C, 3, a

    def test_state_change_listeners(self):
        State = self.state_cls
        s = self.stuff
        s.machine.add_transition('advance', 'A', 'C%s1' % State.separator)
        s.machine.add_transition('reverse', 'C', 'A')
        s.machine.add_transition('lower', 'C%s1' % State.separator, 'C{0}3{0}a'.format(State.separator))
        s.machine.add_transition('rise', 'C%s3' % State.separator, 'C%s1' % State.separator)
        s.machine.add_transition('fast', 'A', 'C{0}3{0}a'.format(State.separator))
        s.machine.on_enter_C('hello_world')
        s.machine.on_exit_C('goodbye')
        s.machine.on_enter('C{0}3{0}a'.format(State.separator), 'greet')
        s.machine.on_exit('C%s3' % State.separator, 'meet')
        s.advance()
        self.assertEqual(s.state, 'C%s1' % State.separator)
        self.assertEqual(s.message, 'Hello World!')
        s.lower()
        self.assertEqual(s.state, 'C{0}3{0}a'.format(State.separator))
        self.assertEqual(s.message, 'Hi')
        s.rise()
        self.assertEqual(s.state, 'C%s1' % State.separator)
        self.assertTrue(s.message.startswith('Nice to'))
        s.reverse()
        self.assertEqual(s.state, 'A')
        self.assertTrue(s.message.startswith('So long'))
        s.fast()
        self.assertEqual(s.state, 'C{0}3{0}a'.format(State.separator))
        self.assertEqual(s.message, 'Hi')
        s.to_A()
        self.assertEqual(s.state, 'A')
        self.assertTrue(s.message.startswith('So long'))

    def test_nested_auto_transitions(self):
        State = self.state_cls
        s = self.stuff
        s.to_C()
        self.assertEqual(s.state, 'C')
        state = 'C{0}3{0}a'.format(State.separator)
        s.to(state)
        self.assertEqual(s.state, state)
        # backwards compatibility check (can be removed in 0.7)
        self.assertEqual(s.state, state)
        for state_name in s.machine.get_nested_state_names():
            event_name = 'to_{0}'.format(state_name)
            num_base_states = len(s.machine.states)
            self.assertTrue(event_name in s.machine.events)
            self.assertEqual(len(s.machine.events[event_name].transitions), num_base_states)

    @skipIf(pgv is None, 'NestedGraph diagram test requires graphviz')
    def test_ordered_with_graph(self):
        GraphMachine = MachineFactory.get_predefined(graph=True, nested=True)

        class CustomHierarchicalGraphMachine(GraphMachine):
            state_cls = self.state_cls

        states = ['A', 'B', {'name': 'C', 'children': ['1', '2',
                                                       {'name': '3', 'children': ['a', 'b', 'c']}]}, 'D', 'E', 'F']

        machine = CustomHierarchicalGraphMachine('self', states, initial='A', auto_transitions=False,
                                                 ignore_invalid_triggers=True, use_pygraphviz=False)
        machine.add_ordered_transitions(trigger='next_state')
        machine.next_state()
        self.assertEqual(machine.state, 'B')
        target = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        machine.get_graph().draw(target.name, prog='dot')
        self.assertTrue(getsize(target.name) > 0)
        target.close()
        unlink(target.name)

    def test_example_two(self):
        separator = self.state_cls.separator
        states = ['A', 'B',
                  {'name': 'C', 'children': ['1', '2',
                                             {'name': '3', 'children': ['a', 'b', 'c']}]
                   }]

        transitions = [
            ['reset', 'C', 'A'],
            ['reset', 'C%s2' % separator, 'C']  # overwriting parent reset
        ]

        # we rely on auto transitions
        machine = self.stuff.machine_cls(states=states, transitions=transitions, initial='A')

        machine.to_B()  # exit state A, enter state B
        machine.to_C()  # exit B, enter C
        if separator == '_':
            machine.to_C_3_a()
        else:
            machine.to_C.s3.a()  # enter C↦a; enter C↦3↦a;
        self.assertEqual(machine.state, 'C{0}3{0}a'.format(separator))
        machine.to('C{0}2'.format(separator))  # exit C↦3↦a, exit C↦3, enter C↦2
        self.assertEqual(machine.state, 'C{0}2'.format(separator))
        machine.reset()  # exit C↦2; reset C has been overwritten by C↦3
        self.assertEqual('C', machine.state)
        machine.reset()  # exit C, enter A
        self.assertEqual('A', machine.state)


class TestSeparatorsSlash(TestSeparatorsBase):
    separator = '/'


class TestSeparatorsDot(TestSeparatorsBase):
    separator = '.'


@skipIf(sys.version_info[0] < 3, "Unicode separators are only supported for Python 3")
class TestSeparatorUnicode(TestSeparatorsBase):
    separator = u'↦'
