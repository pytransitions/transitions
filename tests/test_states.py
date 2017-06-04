from transitions import Machine
from transitions.extensions.states import *
from transitions.extensions.factory import LockedHierarchicalGraphMachine
from time import sleep

from unittest import TestCase
from .test_graphing import TestDiagramsLockedNested

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock


class TestTransitions(TestCase):

    def test_tags(self):

        @add_state_features(Tags)
        class CustomMachine(Machine):
            pass

        states = [{"name": "A", "tags": ["initial", "success", "error_state"]}]
        m = CustomMachine(states=states, initial='A')
        s = m.get_state(m.state)
        self.assertTrue(s.is_initial)
        self.assertTrue(s.is_success)
        self.assertTrue(s.is_error_state)
        self.assertFalse(s.is_not_available)

    def test_error(self):

        @add_state_features(Error)
        class CustomMachine(Machine):
            pass

        states = ['A', 'B', 'F',
                  {'name': 'S1', 'tags': ['accepted']},
                  {'name': 'S2', 'accepted': True}]

        transitions = [['to_B', ['S1', 'S2'], 'B'], ['go', 'A', 'B'], ['fail', 'B', 'F'],
                       ['success1', 'B', 'S2'], ['success2', 'B', 'S2']]
        m = CustomMachine(states=states, transitions=transitions, auto_transitions=False, initial='A')
        m.go()
        m.success1()
        self.assertTrue(m.get_state(m.state).is_accepted)
        m.to_B()
        m.success2()
        self.assertTrue(m.get_state(m.state).is_accepted)
        m.to_B()
        with self.assertRaises(MachineError):
            m.fail()

    def test_timeout(self):
        mock = MagicMock()

        @add_state_features(Timeout)
        class CustomMachine(Machine):

            def timeout(self):
                mock()

        states = ['A',
                  {'name': 'B', 'timeout': 0.3, 'on_timeout': 'timeout'},
                  {'name': 'C', 'timeout': 0.3, 'on_timeout': mock}]

        m = CustomMachine(states=states)
        m.to_B()
        m.to_A()
        sleep(0.4)
        self.assertFalse(mock.called)
        m.to_B()
        sleep(0.4)
        self.assertTrue(mock.called)
        m.to_C()
        sleep(0.4)
        self.assertEqual(mock.call_count, 2)

        with self.assertRaises(AttributeError):
            m.add_state({'name': 'D', 'timeout': 0.3})

    def test_volatile(self):
        mock = MagicMock()

        class TemporalState(object):

            def __init__(self):
                self.value = 5

            def increase(self):
                self.value += 1

        @add_state_features(Volatile)
        class CustomMachine(Machine):
            pass

        states = ['A', {'name': 'B', 'volatile': TemporalState}]
        m = CustomMachine(states=states, initial='A')
        # retrieve states
        a = m.get_state('A')
        b = m.get_state('B')
        # add a new variable to empty default volatile object
        a.foo = 3
        self.assertEqual(a.volatile.foo, 3)
        # on_exit is an attribute of state; should be persistent
        b.on_exit = [mock]
        m.to_B()
        self.assertIn(mock, b.on_exit)
        # value has been set in __init__ of TemporalState
        self.assertEqual(b.value, 5)
        # should call method of TemporalState
        b.increase()
        self.assertEqual(b.value, 6)
        # re-entering state should reset default volatile object
        m.to_A()
        self.assertFalse(hasattr(a, 'foo'))

#
# class TestStatesDiagramsLockedNested(TestDiagramsLockedNested):
#
#     def setUp(self):
#
#         @add_state_features(Error, Timeout, Volatile)
#         class CustomMachine(LockedHierarchicalGraphMachine):
#             pass
#
#         super(TestStatesDiagramsLockedNested, self).setUp()
#         self.machine_cls = CustomMachine
