from transitions.core import *
from unittest import TestCase

class Stuff(object):

    def __init__(self):

        self.state = None

        states = ['A', 'B', 'C', 'D', 'E']
        self.machine = Machine(self, states=states, initial='A')

    def this_passes(self):
        return True

    def this_fails(self):
        return False

    def goodbye(self):
        self.message = "So long, suckers!"

    def hello_world(self):
        self.message = "Hello World!"


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

    # def test_machine_initialization(self):
        # Minimal init without arguments
        # m = Machine()


    def test_transitioning(self):
        s = self.stuff
        s.machine.add_transition('advance', 'A', 'B', conditions='this_passes')
        s.machine.add_transition('advance', 'B', 'C')
        s.machine.add_transition('advance', 'C', 'D')
        s.advance()
        self.assertEquals(s.state, 'B')
        self.assertFalse(s.is_A())
        self.assertTrue(s.is_B())
        s.advance()
        self.assertEquals(s.state, 'C')

    def test_multiple_add_transitions_from_state(self):
        s = self.stuff
        s.machine.add_transition('advance', 'A', 'B', conditions=['this_fails'])
        s.machine.add_transition('advance', 'A', 'C')
        s.advance()
        self.assertEquals(s.state, 'C')

    def test_use_machine_as_model(self):
        states = ['A', 'B', 'C', 'D']
        m = Machine(states=states, initial='A')
        m.add_transition('move', 'A', 'B')
        m.add_transition('move_to_C', 'B', 'C')
        m.move()
        self.assertEquals(m.state, 'B')

    def test_state_change_listeners(self):
        s = self.stuff
        s.machine.add_transition('advance', 'A', 'B')
        s.machine.add_transition('reverse', 'B', 'A')
        s.machine.on_enter_B('hello_world')
        s.machine.on_exit_B('goodbye')
        s.advance()
        self.assertEquals(s.state, 'B')
        self.assertEquals(s.message, 'Hello World!')
        s.reverse()
        self.assertEquals(s.state, 'A')
        self.assertTrue(s.message.startswith('So long'))

    def test_inheritance(self):
        states = ['A', 'B', 'C', 'D', 'E']
        s = InheritedStuff(states=states, initial='A')
        s.add_transition('advance', 'A', 'B', conditions='this_passes')
        s.add_transition('advance', 'B', 'C')
        s.add_transition('advance', 'C', 'D')
        s.advance()
        self.assertEquals(s.state, 'B')
        self.assertFalse(s.is_A())
        self.assertTrue(s.is_B())
        s.advance()
        self.assertEquals(s.state, 'C')

