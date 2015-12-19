try:
    from builtins import object
except ImportError:
    pass

from transitions import MachineError
from transitions import HierarchicalMachine as Machine
from transitions import NestedState as State

from unittest import TestCase

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock


class Stuff(object):

    def __init__(self):

        self.state = None
        self.message = None

        states = ['A', 'B', {'name': 'C', 'children': ['1', '2', {'name': '3', 'children': ['a', 'b', 'c']}]},
                  'D', 'E', 'F']
        self.machine = Machine(self, states=states, initial='A')

    def this_passes(self):
        return True

    def this_fails(self):
        return False

    def this_fails_by_default(self, boolean=False):
        return boolean

    def extract_boolean(self, event_data):
        return event_data.kwargs['boolean']

    def goodbye(self):
        self.message = "So long, suckers!"

    def hello_world(self):
        self.message = "Hello World!"

    def greet(self):
        self.message = "Hi"

    def meet(self):
        self.message = "Nice to meet you"

    def hello_F(self):
        if not hasattr(self, 'message'):
            self.message = ''
        self.message += "Hello F!"

    def set_message(self, message="Hello World!"):
        self.message = message

    def extract_message(self, event_data):
        self.message = event_data.kwargs['message']

    def on_enter_E(self, msg=None):
        self.message = "I am E!" if msg is None else msg

    def on_exit_E(self):
        self.exit_message = "E go home..."

    def on_enter_F(self):
        self.message = "I am F!"


class InheritedStuff(Machine):

    def __init__(self, states, initial='A'):

        self.state = None

        Machine.__init__(self, states=states, initial=initial)

    def this_passes(self):
        return True

    def this_fails(self):
        return False


class TestTransitions(TestCase):

    def setUp(self):
        self.stuff = Stuff()

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
