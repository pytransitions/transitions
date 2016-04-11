try:
    from builtins import object
except ImportError:
    pass

from transitions import Machine, State, MachineError
from unittest import TestCase
from .utils import Stuff, InheritedStuff

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock


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
        m = Machine(model=s, states=states, transitions=transitions, initial='State2')
        s.advance()
        self.assertEquals(s.message, 'Hello World!')

    def test_property_initial(self):
        states = ['A', 'B', 'C', 'D']
        # Define with list of dictionaries
        transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'B'},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'D'}
        ]
        m = Machine(states=states, transitions=transitions, initial='A')
        self.assertEquals(m.initial, 'A')
        m = Machine(states=states, transitions=transitions, initial='C')
        self.assertEquals(m.initial, 'C')
        m = Machine(states=states, transitions=transitions)
        self.assertEquals(m.initial, 'initial')

    def test_transition_definitions(self):
        states = ['A', 'B', 'C', 'D']
        # Define with list of dictionaries
        transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'B'},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'D'}
        ]
        m = Machine(states=states, transitions=transitions, initial='A')
        m.walk()
        self.assertEquals(m.state, 'B')
        # Define with list of lists
        transitions = [
            ['walk', 'A', 'B'],
            ['run', 'B', 'C'],
            ['sprint', 'C', 'D']
        ]
        m = Machine(states=states, transitions=transitions, initial='A')
        m.to_C()
        m.sprint()
        self.assertEquals(m.state, 'D')

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

    def test_before_after_callback_addition(self):
        m = Machine(Stuff(), states=['A', 'B', 'C'], initial='A')
        m.add_transition('move', 'A', 'B')
        trans = m.events['move'].transitions['A'][0]
        trans.add_callback('after', 'increase_level')
        m.model.move()
        self.assertEquals(m.model.level, 2)

    def test_before_after_transition_listeners(self):
        m = Machine(Stuff(), states=['A', 'B', 'C'], initial='A')
        m.add_transition('move', 'A', 'B')
        m.add_transition('move', 'B', 'C')

        m.before_move('increase_level')
        m.model.move()
        self.assertEquals(m.model.level, 2)
        m.model.move()
        self.assertEquals(m.model.level, 3)

    def test_state_model_change_listeners(self):
        s = self.stuff
        s.machine.add_transition('go_e', 'A', 'E')
        s.machine.add_transition('go_f', 'E', 'F')
        s.machine.on_enter_F('hello_F')
        s.go_e()
        self.assertEquals(s.state, 'E')
        self.assertEquals(s.message, 'I am E!')
        s.go_f()
        self.assertEquals(s.state, 'F')
        self.assertEquals(s.exit_message, 'E go home...')
        assert 'I am F!' in s.message
        assert 'Hello F!' in s.message

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

    def test_send_event_data_callbacks(self):
        states = ['A', 'B', 'C', 'D', 'E']
        s = Stuff()
        # First pass positional and keyword args directly to the callback
        m = Machine(model=s, states=states, initial='A', send_event=False,
                    auto_transitions=True)
        m.add_transition(
            trigger='advance', source='A', dest='B', before='set_message')
        s.advance(message='Hallo. My name is Inigo Montoya.')
        self.assertTrue(s.message.startswith('Hallo.'))
        # Make sure callbacks handle arguments properly
        s.to_E("Optional message")
        self.assertEquals(s.message, 'Optional message')
        s.to_B()
        # Now wrap arguments in an EventData instance
        m.send_event = True
        m.add_transition(
            trigger='advance', source='B', dest='C', before='extract_message')
        s.advance(message='You killed my father. Prepare to die.')
        self.assertTrue(s.message.startswith('You'))

    def test_send_event_data_conditions(self):
        states = ['A', 'B', 'C', 'D']
        s = Stuff()
        # First pass positional and keyword args directly to the condition
        m = Machine(model=s, states=states, initial='A', send_event=False)
        m.add_transition(
            trigger='advance', source='A', dest='B',
            conditions='this_fails_by_default')
        s.advance(boolean=True)
        self.assertEquals(s.state, 'B')
        # Now wrap arguments in an EventData instance
        m.send_event = True
        m.add_transition(
            trigger='advance', source='B', dest='C',
            conditions='extract_boolean')
        s.advance(boolean=False)
        self.assertEquals(s.state, 'B')

    def test_auto_transitions(self):
        states = ['A', {'name': 'B'}, State(name='C')]
        m = Machine(None, states, initial='A', auto_transitions=True)
        m.to_B()
        self.assertEquals(m.state, 'B')
        m.to_C()
        self.assertEquals(m.state, 'C')
        m.to_A()
        self.assertEquals(m.state, 'A')
        # Should fail if auto transitions is off...
        m = Machine(None, states, initial='A', auto_transitions=False)
        with self.assertRaises(AttributeError):
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

    def test_ignore_invalid_triggers(self):
        a_state = State('A')
        transitions = [['a_to_b', 'A', 'B']]
        # Exception is triggered by default
        b_state = State('B')
        m1 = Machine(None, states=[a_state, b_state], transitions=transitions,
                     initial='B')
        with self.assertRaises(MachineError):
            m1.a_to_b()
        # Exception is suppressed, so this passes
        b_state = State('B', ignore_invalid_triggers=True)
        m2 = Machine(None, states=[a_state, b_state], transitions=transitions,
                     initial='B')
        m2.a_to_b()
        # Set for some states but not others
        new_states = ['C', 'D']
        m1.add_states(new_states, ignore_invalid_triggers=True)
        m1.to_D()
        m1.a_to_b()  # passes because exception suppressed for D
        m1.to_B()
        with self.assertRaises(MachineError):
            m1.a_to_b()
        # Set at machine level
        m3 = Machine(None, states=[a_state, b_state], transitions=transitions,
                     initial='B', ignore_invalid_triggers=True)
        m3.a_to_b()

    def test_string_callbacks(self):

        m = Machine(None, states=['A', 'B'],
                    before_state_change='before_state_change',
                    after_state_change='after_state_change', send_event=True,
                    initial='A', auto_transitions=True)

        m.before_state_change = MagicMock()
        m.after_state_change = MagicMock()

        m.to_B()
        self.assertTrue(m.before_state_change.called)
        self.assertTrue(m.after_state_change.called)

    def test_function_callbacks(self):
        before_state_change = MagicMock()
        after_state_change = MagicMock()

        m = Machine(None, states=['A', 'B'],
                    before_state_change=before_state_change,
                    after_state_change=after_state_change, send_event=True,
                    initial='A', auto_transitions=True)

        m.to_B()
        self.assertTrue(m.before_state_change.called)
        self.assertTrue(m.after_state_change.called)

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
        m = Machine(states=states, transitions=transitions, initial='A')
        m.walk()
        dump = pickle.dumps(m)
        self.assertIsNotNone(dump)
        m2 = pickle.loads(dump)
        self.assertEqual(m.state, m2.state)
        m2.run()

    def test_async(self):
        states = ['A', 'B', 'C', 'D']
        # Define with list of dictionaries

        def change_state(machine):
            self.assertEqual(machine.current_state.name, 'A')
            if machine.async:
                machine.run(machine=machine)
                self.assertEqual(machine.current_state.name, 'A')
            else:
                with self.assertRaises(MachineError):
                    machine.run(machine=machine)

        transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'B', 'before': change_state},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'D'}
        ]

        m = Machine(states=states, transitions=transitions, initial='A')
        m.walk(machine=m)
        self.assertEqual(m.current_state.name, 'B')
        m = Machine(states=states, transitions=transitions, initial='A', async=True)
        m.walk(machine=m)
        self.assertEqual(m.current_state.name, 'C')
