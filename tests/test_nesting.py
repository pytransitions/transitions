# -*- coding: utf-8 -*-

try:
    from builtins import object
except ImportError:
    pass

import sys

from transitions.extensions import MachineFactory
from transitions.extensions.nesting import NestedState as State
from .test_core import TestTransitions as TestsCore
from .utils import Stuff

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock


state_separator = State.separator

class TestTransitions(TestsCore):

    def setUp(self):
        states = ['A', 'B', {'name': 'C', 'children': ['1', '2', {'name': '3', 'children': ['a', 'b', 'c']}]},
                  'D', 'E', 'F']
        machine_cls = MachineFactory.get_predefined(nested=True)
        self.stuff = Stuff(states, machine_cls)

    def tearDown(self):
        pass

    def test_init_machine_with_hella_arguments(self):
        states = [
            State('State1'),
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
        self.assertEquals(s.message, 'Hello World!')

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
        self.assertEquals(m.initial, 'A')
        m = self.stuff.machine_cls(states=states, transitions=transitions, initial='C')
        self.assertEquals(m.initial, 'C')
        m = self.stuff.machine_cls(states=states, transitions=transitions)
        self.assertEquals(m.initial, 'initial')

    def test_transition_definitions(self):
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
        self.assertEquals(m.state, 'B')
        m.run()
        self.assertEquals(m.state, 'C')
        m.run()
        self.assertEquals(m.state, 'C%s1' % State.separator)
        # Define with list of lists
        transitions = [
            ['walk', 'A', 'B'],
            ['run', 'B', 'C'],
            ['sprint', 'C', 'D']
        ]
        m = self.stuff.machine_cls(states=states, transitions=transitions, initial='A')
        m.to_C()
        m.sprint()
        self.assertEquals(m.state, 'D')

    def test_transitioning(self):
        s = self.stuff
        s.machine.add_transition('advance', 'A', 'B')
        s.machine.add_transition('advance', 'B', 'C')
        s.machine.add_transition('advance', 'C', 'D')
        s.machine.add_transition('reset', '*', 'A')
        self.assertEqual(len(s.machine.events['reset'].transitions['C%s1' % State.separator]), 1)
        s.advance()
        self.assertEquals(s.state, 'B')
        self.assertFalse(s.is_A())
        self.assertTrue(s.is_B())
        s.advance()
        self.assertEquals(s.state, 'C')

    def test_conditions(self):
        s = self.stuff
        s.machine.add_transition('advance', 'A', 'B', conditions='this_passes')
        s.machine.add_transition('advance', 'B', 'C', unless=['this_fails'])
        s.machine.add_transition('advance', 'C', 'D', unless=['this_fails',
                                                              'this_passes'])
        s.advance()
        self.assertEquals(s.state, 'B')
        s.advance()
        self.assertEquals(s.state, 'C')
        s.advance()
        self.assertEquals(s.state, 'C')

    def test_multiple_add_transitions_from_state(self):
        s = self.stuff
        s.machine.add_transition(
            'advance', 'A', 'B', conditions=['this_fails'])
        s.machine.add_transition('advance', 'A', 'C')
        s.machine.add_transition('advance', 'C', 'C%s2' % State.separator)
        s.advance()
        self.assertEquals(s.state, 'C')
        s.advance()
        self.assertEquals(s.state, 'C%s2' % State.separator)
        self.assertFalse(s.is_C())
        self.assertTrue(s.is_C(allow_substates=True))

    def test_use_machine_as_model(self):
        states = ['A', 'B', 'C', 'D']
        m = self.stuff.machine_cls(states=states, initial='A')
        m.add_transition('move', 'A', 'B')
        m.add_transition('move_to_C', 'B', 'C')
        m.move()
        self.assertEquals(m.state, 'B')

    def test_add_custom_state(self):
        s = self.stuff
        s.machine.add_states([{'name': 'E', 'children': ['1', '2', '3']}])
        s.machine.add_transition('go', '*', 'E%s1' % State.separator)
        s.machine.add_transition('run', 'E', 'C{0}3{0}a'.format(State.separator))
        s.go()
        s.run()

    def test_state_change_listeners(self):
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
        self.assertEquals(s.state, 'C%s1' % State.separator)
        self.assertEquals(s.message, 'Hello World!')
        s.lower()
        self.assertEquals(s.state, 'C{0}3{0}a'.format(State.separator))
        self.assertEquals(s.message, 'Hi')
        s.rise()
        self.assertEquals(s.state, 'C%s1' % State.separator)
        self.assertTrue(s.message.startswith('Nice to'))
        s.reverse()
        self.assertEquals(s.state, 'A')
        self.assertTrue(s.message.startswith('So long'))
        s.fast()
        self.assertEquals(s.state, 'C{0}3{0}a'.format(State.separator))
        self.assertEquals(s.message, 'Hi')
        s.to_A()
        self.assertEquals(s.state, 'A')
        self.assertTrue(s.message.startswith('So long'))

    def test_enter_exit_nested(self):
        s = self.stuff
        s.machine.add_transition('advance', 'A', 'C%s1' % State.separator)
        s.machine.add_transition('reverse', 'C', 'A')
        s.machine.add_transition('lower', 'C%s1' % State.separator, 'C{0}3{0}a'.format(State.separator))
        s.machine.add_transition('rise', 'C%s3' % State.separator, 'C%s1' % State.separator)
        s.machine.add_transition('fast', 'A', 'C{0}3{0}a'.format(State.separator))
        for name, state in s.machine.states.items():
            state.on_enter.append('increase_level')
            state.on_exit.append('decrease_level')

        s.advance()
        self.assertEquals(s.state, 'C%s1' % State.separator)
        self.assertEquals(s.level, 2)
        s.lower()
        self.assertEquals(s.state, 'C{0}3{0}a'.format(State.separator))
        self.assertEquals(s.level, 3)
        s.rise()
        self.assertEquals(s.state, 'C%s1' % State.separator)
        self.assertEquals(s.level, 2)
        s.reverse()
        self.assertEquals(s.state, 'A')
        self.assertEquals(s.level, 1)
        s.fast()
        self.assertEquals(s.state, 'C{0}3{0}a'.format(State.separator))
        self.assertEquals(s.level, 3)
        s.to_A()
        self.assertEquals(s.state, 'A')
        self.assertEquals(s.level, 1)
        if State.separator in '_':
            s.to_C_3_a()
        else:
            s.to_C.s3.a()
        self.assertEquals(s.state, 'C{0}3{0}a'.format(State.separator))
        self.assertEquals(s.level, 3)

    def test_ordered_transitions(self):
        states = ['beginning', 'middle', 'end']
        m = self.stuff.machine_cls(None, states)
        m.add_ordered_transitions()
        self.assertEquals(m.state, 'initial')
        m.next_state()
        self.assertEquals(m.state, 'beginning')
        m.next_state()
        m.next_state()
        self.assertEquals(m.state, 'end')
        m.next_state()
        self.assertEquals(m.state, 'initial')

        # Include initial state in loop
        m = self.stuff.machine_cls(None, states)
        m.add_ordered_transitions(loop_includes_initial=False)
        m.to_end()
        m.next_state()
        self.assertEquals(m.state, 'beginning')

        # Test user-determined sequence and trigger name
        m = self.stuff.machine_cls(None, states, initial='beginning')
        m.add_ordered_transitions(['end', 'beginning'], trigger='advance')
        m.advance()
        self.assertEquals(m.state, 'end')
        m.advance()
        self.assertEquals(m.state, 'beginning')

        # Via init argument
        m = self.stuff.machine_cls(
            None, states, initial='beginning', ordered_transitions=True)
        m.next_state()
        self.assertEquals(m.state, 'middle')

    def test_pickle(self):
        import sys
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
        if State.separator in '_':
            m2.to_C_3_a()
            m2.to_C_3_b()
        else:
            m2.to_C.s3.a()
            m2.to_C.s3.b()

    def test_callbacks_duplicate(self):

        transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'C', 'before': 'before_state_change',
             'after': 'after_state_change'},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'}
        ]

        m = self.stuff.machine_cls(None, states=['A', 'B', 'C'], transitions=transitions,
                    before_state_change='before_state_change',
                    after_state_change='after_state_change', send_event=True,
                    initial='A', auto_transitions=True)

        m.before_state_change = MagicMock()
        m.after_state_change = MagicMock()

        m.walk()
        self.assertEqual(m.before_state_change.call_count, 2)
        self.assertEqual(m.after_state_change.call_count, 2)

    def test_with_custom_separator(self):
        State.separator = '.'
        self.setUp()
        self.test_enter_exit_nested()
        self.setUp()
        self.test_state_change_listeners()
        self.test_nested_auto_transitions()
        State.separator = '.' if sys.version_info[0] < 3 else u'↦'
        self.setUp()
        self.test_enter_exit_nested()
        self.setUp()
        self.test_state_change_listeners()
        self.test_nested_auto_transitions()

    def test_nested_auto_transitions(self):
        s = self.stuff
        s.to_C()
        self.assertEqual(s.state, 'C')
        state = 'C{0}3{0}a'.format(State.separator)
        s.machine.to(state)
        self.assertEqual(s.state, state)

    def test_example_one(self):
        State.separator = '_'
        states = ['standing', 'walking', {'name': 'caffeinated', 'children':['dithering', 'running']}]
        transitions = [
          ['walk', 'standing', 'walking'],
          ['stop', 'walking', 'standing'],
          ['drink', '*', 'caffeinated'],
          ['walk', 'caffeinated', 'caffeinated_running'],
          ['relax', 'caffeinated', 'standing']]
        machine = self.stuff.machine_cls(states=states, transitions=transitions, initial='standing',
                                         ignore_invalid_triggers=True, name='Machine 1')

        machine.walk() # Walking now
        machine.stop() # let's stop for a moment
        machine.drink() # coffee time
        machine.state
        self.assertEqual(machine.state, 'caffeinated')
        machine.walk() # we have to go faster
        self.assertEqual(machine.state, 'caffeinated_running')
        machine.stop() # can't stop moving!
        machine.state
        self.assertEqual(machine.state, 'caffeinated_running')
        machine.relax() # leave nested state
        machine.state # phew, what a ride
        self.assertEqual(machine.state, 'standing')
        machine.to_caffeinated_running() # auto transition fast track
        machine.on_enter_caffeinated_running('callback_method')

    def test_example_two(self):
        State.separator = '.' if sys.version_info[0] < 3 else u'↦'
        states = ['A', 'B',
          {'name': 'C', 'children':['1', '2',
            {'name': '3', 'children': ['a', 'b', 'c']}
          ]}
        ]

        transitions = [
            ['reset', 'C', 'A'],
            ['reset', 'C%s2' % State.separator, 'C']  # overwriting parent reset
        ]

        # we rely on auto transitions
        machine = self.stuff.machine_cls(states=states, transitions=transitions, initial='A')

        machine.to_B()  # exit state A, enter state B
        machine.to_C()  # exit B, enter C
        machine.to_C.s3.a()  # enter C↦a; enter C↦3↦a;
        self.assertEqual(machine.state, 'C{0}3{0}a'.format(State.separator))
        machine.to_C.s2()  # exit C↦3↦a, exit C↦3, enter C↦2
        machine.reset()  # exit C↦2; reset C has been overwritten by C↦3
        self.assertEqual(machine.state, 'C')
        machine.reset()  # exit C, enter A
        self.assertEqual(machine.state, 'A')


class TestWithGraphTransitions(TestTransitions):

    def setUp(self):
        State.separator = state_separator
        states = ['A', 'B', {'name': 'C', 'children': ['1', '2', {'name': '3', 'children': ['a', 'b', 'c']}]},
                  'D', 'E', 'F']

        machine_cls = MachineFactory.get_predefined(graph=True, nested=True)
        self.stuff = Stuff(states, machine_cls)
