try:
    from builtins import object
except ImportError:
    pass
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

    def set_message(self, message="Hello World!"):
        self.message = message

    def extract_message(self, event_data):
        self.message = event_data.kwargs['message']


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
        m = Machine(
            model=s, states=states, transitions=transitions, initial='State2')
        s.advance()
        self.assertEquals(s.message, 'Hello World!')

    def test_transitioning(self):
        s = self.stuff
        s.machine.add_transition('advance', 'A', 'B')
        s.machine.add_transition('advance', 'B', 'C')
        s.machine.add_transition('advance', 'C', 'D')
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

    def test_send_event_data(self):
        states = ['A', 'B', 'C', 'D']
        s = Stuff()
        # First pass positional and keyword args directly to the callback
        m = Machine(model=s, states=states, initial='A', send_event=False)
        m.add_transition(
            trigger='advance', source='A', dest='B', before='set_message')
        s.advance(message='Hallo. My name is Inigo Montoya.')
        self.assertTrue(s.message.startswith('Hallo.'))
        # Now wrap arguments in an EventData instance
        m.send_event = True
        m.add_transition(
            trigger='advance', source='B', dest='C', before='extract_message')
        s.advance(message='You killed my father. Prepare to die.')
        self.assertTrue(s.message.startswith('You'))

    def test_auto_transitions(self):
        states = ['A', {'name':'B'}, State(name='C')]
        m = Machine(None, states, initial='A', auto_transitions=True)
        m.to_B()
        self.assertEquals(m.state, 'B')
        m.to_C()
        self.assertEquals(m.state, 'C')
        m.to_A()
        self.assertEquals(m.state, 'A')
        # Should fail if auto transitions is off...
        m = Machine(None, states, initial='A', auto_transitions=False)
        with self.assertRaises(TypeError):
            m.to_C()

    def test_ordered_transitions(self):
        states = ['beginning', 'middle', 'end']
        m = Machine(None, states)
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
        m = Machine(None, states)
        m.add_ordered_transitions(loop_includes_initial=False)
        m.to_end()
        m.next_state()
        self.assertEquals(m.state, 'beginning')

        # Test user-determined sequence and trigger name
        m = Machine(None, states, initial='beginning')
        m.add_ordered_transitions(['end', 'beginning'], trigger='advance')
        m.advance()
        self.assertEquals(m.state, 'end')
        m.advance()
        self.assertEquals(m.state, 'beginning')

        # Via init argument
        m = Machine(
            None, states, initial='beginning', ordered_transitions=True)
        m.next_state()
        self.assertEquals(m.state, 'middle')

