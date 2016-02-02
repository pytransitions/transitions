try:
    from builtins import object
except ImportError:
    pass

from transitions.extensions import MachineFactory
from transitions.extensions import NestedState as State
from .test_core import TestTransitions as TestsCore
from .utils import Stuff

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock


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
        self.assertEquals(m.initial, 'C_1')
        m = self.stuff.machine_cls(states=states, transitions=transitions)
        self.assertEquals(m.initial, 'initial')

    def test_transition_definitions(self):
        states = ['A', 'B', {'name': 'C', 'children': ['1', '2', '3']}, 'D']
        # Define with list of dictionaries
        transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'B'},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'D'},
            {'trigger': 'run', 'source': 'C_1', 'dest': 'C_2'}
        ]
        m = self.stuff.machine_cls(states=states, transitions=transitions, initial='A')
        m.walk()
        self.assertEquals(m.state, 'B')
        m.run()
        self.assertEquals(m.state, 'C_1')
        m.run()
        self.assertEquals(m.state, 'C_2')
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
        self.assertEqual(len(s.machine.events['reset'].transitions['C_1']), 1)
        s.advance()
        self.assertEquals(s.state, 'B')
        self.assertFalse(s.is_A())
        self.assertTrue(s.is_B())
        s.advance()
        self.assertEquals(s.state, 'C_1')

    def test_conditions(self):
        s = self.stuff
        s.machine.add_transition('advance', 'A', 'B', conditions='this_passes')
        s.machine.add_transition('advance', 'B', 'C', unless=['this_fails'])
        s.machine.add_transition('advance', 'C', 'D', unless=['this_fails',
                                                              'this_passes'])
        s.advance()
        self.assertEquals(s.state, 'B')
        s.advance()
        self.assertEquals(s.state, 'C_1')
        s.advance()
        self.assertEquals(s.state, 'C_1')

    def test_multiple_add_transitions_from_state(self):
        s = self.stuff
        s.machine.add_transition(
            'advance', 'A', 'B', conditions=['this_fails'])
        s.machine.add_transition('advance', 'A', 'C')
        s.machine.add_transition('advance', 'C_1', 'C_2')
        s.advance()
        self.assertEquals(s.state, 'C_1')
        s.advance()
        self.assertEquals(s.state, 'C_2')

    def test_use_machine_as_model(self):
        states = ['A', 'B', 'C', 'D']
        m = self.stuff.machine_cls(states=states, initial='A')
        m.add_transition('move', 'A', 'B')
        m.add_transition('move_to_C', 'B', 'C')
        m.move()
        self.assertEquals(m.state, 'B')

    def test_state_change_listeners(self):
        s = self.stuff
        s.machine.add_transition('advance', 'A', 'C')
        s.machine.add_transition('reverse', 'C', 'A')
        s.machine.add_transition('lower', 'C_1', 'C_3')
        s.machine.add_transition('rise', 'C_3', 'C_1')
        s.machine.add_transition('fast', 'A', 'C_3')
        s.machine.on_enter_C('hello_world')
        s.machine.on_exit_C('goodbye')
        s.machine.on_enter_C_3_a('greet')
        s.machine.on_exit_C_3('meet')
        s.advance()
        self.assertEquals(s.state, 'C_1')
        self.assertEquals(s.message, 'Hello World!')
        s.lower()
        self.assertEquals(s.state, 'C_3_a')
        self.assertEquals(s.message, 'Hi')
        s.rise()
        self.assertEquals(s.state, 'C_1')
        self.assertTrue(s.message.startswith('Nice to'))
        s.reverse()
        self.assertEquals(s.state, 'A')
        self.assertTrue(s.message.startswith('So long'))
        s.fast()
        self.assertEquals(s.state, 'C_3_a')
        self.assertEquals(s.message, 'Hi')
        s.to_A()
        self.assertEquals(s.state, 'A')
        self.assertTrue(s.message.startswith('So long'))

    def test_enter_exit_nested(self):
        s = self.stuff
        s.machine.add_transition('advance', 'A', 'C')
        s.machine.add_transition('reverse', 'C', 'A')
        s.machine.add_transition('lower', 'C_1', 'C_3')
        s.machine.add_transition('rise', 'C_3', 'C_1')
        s.machine.add_transition('fast', 'A', 'C_3')
        for name, state in s.machine.states.items():
            state.on_enter.append('increase_level')
            state.on_exit.append('decrease_level')

        s.advance()
        self.assertEquals(s.state, 'C_1')
        self.assertEquals(s.level, 2)
        s.lower()
        self.assertEquals(s.state, 'C_3_a')
        self.assertEquals(s.level, 3)
        s.rise()
        self.assertEquals(s.state, 'C_1')
        self.assertEquals(s.level, 2)
        s.reverse()
        self.assertEquals(s.state, 'A')
        self.assertEquals(s.level, 1)
        s.fast()
        self.assertEquals(s.state, 'C_3_a')
        self.assertEquals(s.level, 3)
        s.to_A()
        self.assertEquals(s.state, 'A')
        self.assertEquals(s.level, 1)
        s.to_C_3_a()
        self.assertEquals(s.state, 'C_3_a')
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

        states = ['A', 'B', 'C', 'D']
        # Define with list of dictionaries
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


class TestWithGraphTransitions(TestTransitions):

    def setUp(self):
        states = ['A', 'B', {'name': 'C', 'children': ['1', '2', {'name': '3', 'children': ['a', 'b', 'c']}]},
                  'D', 'E', 'F']

        machine_cls = MachineFactory.get_predefined(graph=True, nested=True)
        self.stuff = Stuff(states, machine_cls)
