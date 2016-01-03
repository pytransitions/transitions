try:
    from builtins import object
except ImportError:
    pass

from transitions import MachineError
from transitions import HierarchicalMachine as Machine
from .utils import Stuff

from unittest import TestCase

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock


class TestTransitions(TestCase):

    def setUp(self):
        states = ['A', 'B', {'name': 'C', 'children': ['1', '2', {'name': '3', 'children': ['a', 'b', 'c']}]},
                  'D', 'E', 'F']
        self.stuff = Stuff(states, Machine)

    def tearDown(self):
        pass

    def test_blueprint_simple(self):
        states = ['A', 'B', 'C', 'D']
        # Define with list of dictionaries
        transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'B'},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'D'}
        ]
        m = Machine(states=states, transitions=transitions, before_state_change='before_state_change',
                    after_state_change='after_state_change', initial='A')

        self.assertEqual(len(m.blueprints['states']), 4)
        self.assertEqual(m.blueprints['states'][3], 'D')
        self.assertEqual(len(m.blueprints['transitions']), 3)
        self.assertEqual(m.blueprints['transitions'][2]['trigger'], 'sprint')

        m.add_transition('fly', 'D', 'A')
        self.assertEqual(len(m.blueprints['transitions']), 4)
        self.assertEqual(m.blueprints['transitions'][3]['source'], 'D')

    def test_blueprint_nested(self):
        states = ['A', {'name': 'B', 'on_enter': 'chirp', 'children': ['1', '2', '3']}, 'C', 'D']
        # Define with list of dictionaries
        transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'B'},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'D'}
        ]
        m = Machine(states=states, transitions=transitions, before_state_change='before_state_change',
                    after_state_change='after_state_change', initial='A')

        self.assertEqual(len(m.blueprints['states']), 4)
        self.assertEqual(m.blueprints['states'][3], 'D')
        self.assertEqual(len(m.blueprints['transitions']), 3)
        self.assertEqual(m.blueprints['transitions'][2]['trigger'], 'sprint')

        m.add_transition('fly', 'D', 'A')
        self.assertEqual(len(m.blueprints['transitions']), 4)
        self.assertEqual(m.blueprints['transitions'][3]['source'], 'D')

    def test_blueprint_reuse(self):
        states = ['1', '2', '3']
        transitions = [
            {'trigger': 'increase', 'source': '1', 'dest': '2'},
            {'trigger': 'increase', 'source': '2', 'dest': '3'},
            {'trigger': 'decrease', 'source': '3', 'dest': '2'},
            {'trigger': 'decrease', 'source': '1', 'dest': '1'},
            {'trigger': 'reset', 'source': '*', 'dest': '1'},
        ]

        counter = Machine(states=states, transitions=transitions, before_state_change='check',
                          after_state_change='clear', initial='1')

        new_states = ['A', 'B', {'name':'C', 'children': counter}]
        new_transitions = [
            {'trigger': 'forward', 'source': 'A', 'dest': 'B'},
            {'trigger': 'forward', 'source': 'B', 'dest': 'C'},
            {'trigger': 'backward', 'source': 'C', 'dest': 'B'},
            {'trigger': 'backward', 'source': 'B', 'dest': 'A'},
            {'trigger': 'calc', 'source': '*', 'dest': 'C'},
        ]

        walker = Machine(states=new_states, transitions=new_transitions, before_state_change='watch',
                         after_state_change='look_back', initial='A')

        walker.watch = lambda: 'walk'
        walker.look_back = lambda: 'look_back'
        walker.check = lambda: 'check'
        walker.clear = lambda: 'clear'

        with self.assertRaises(MachineError):
            walker.increase()
        self.assertEqual(walker.state, 'A')
        walker.forward()
        walker.forward()
        self.assertEqual(walker.state, 'C_1')
        walker.increase()
        self.assertEqual(walker.state, 'C_2')
        walker.reset()
        self.assertEqual(walker.state, 'C_1')
        walker.to_A()
        self.assertEqual(walker.state, 'A')
        walker.calc()
        self.assertEqual(walker.state, 'C_1')

    def test_blueprint_remap(self):
        states = ['1', '2', '3', 'finished']
        transitions = [
            {'trigger': 'increase', 'source': '1', 'dest': '2'},
            {'trigger': 'increase', 'source': '2', 'dest': '3'},
            {'trigger': 'decrease', 'source': '3', 'dest': '2'},
            {'trigger': 'decrease', 'source': '1', 'dest': '1'},
            {'trigger': 'reset', 'source': '*', 'dest': '1'},
            {'trigger': 'done', 'source': '3', 'dest': 'finished'}
        ]

        counter = Machine(states=states, transitions=transitions, initial='1')

        new_states = ['A', 'B', {'name': 'C', 'children': counter, 'remap': {'finished': 'A'}}]
        new_transitions = [
            {'trigger': 'forward', 'source': 'A', 'dest': 'B'},
            {'trigger': 'forward', 'source': 'B', 'dest': 'C'},
            {'trigger': 'backward', 'source': 'C', 'dest': 'B'},
            {'trigger': 'backward', 'source': 'B', 'dest': 'A'},
            {'trigger': 'calc', 'source': '*', 'dest': 'C'},
        ]

        walker = Machine(states=new_states, transitions=new_transitions, before_state_change='watch',
                         after_state_change='look_back', initial='A')

        walker.watch = lambda: 'walk'
        walker.look_back = lambda: 'look_back'

        counter.increase()
        counter.increase()
        counter.done()
        self.assertEqual(counter.state, 'finished')

        with self.assertRaises(MachineError):
            walker.increase()
        self.assertEqual(walker.state, 'A')
        walker.forward()
        walker.forward()
        self.assertEqual(walker.state, 'C_1')
        walker.increase()
        self.assertEqual(walker.state, 'C_2')
        walker.reset()
        self.assertEqual(walker.state, 'C_1')
        walker.to_A()
        self.assertEqual(walker.state, 'A')
        walker.calc()
        self.assertEqual(walker.state, 'C_1')
        walker.increase()
        walker.increase()
        walker.done()
        self.assertEqual(walker.state, 'A')