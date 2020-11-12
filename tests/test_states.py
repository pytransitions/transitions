from transitions import Machine
from transitions.extensions.states import *
from transitions.extensions import MachineFactory
from time import sleep

from unittest import TestCase
from .test_graphviz import TestDiagramsLockedNested

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

    def test_error_callback(self):
        @add_state_features(Error)
        class CustomMachine(Machine):
            pass

        mock_callback = MagicMock()

        states = ['A', {"name": "B", "on_enter": mock_callback}, 'C']
        transitions = [
            ["to_B", "A", "B"],
            ["to_C", "B", "C"],
        ]
        m = CustomMachine(states=states, transitions=transitions, auto_transitions=False, initial='A')
        m.to_B()
        self.assertEqual(m.state, "B")
        self.assertTrue(mock_callback.called)

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

    def test_timeout_callbacks(self):
        timeout = MagicMock()
        notification = MagicMock()
        counter = MagicMock()

        @add_state_features(Timeout)
        class CustomMachine(Machine):
            pass

        class Model(object):

            def on_timeout_B(self):
                counter()

            def timeout(self):
                timeout()

            def notification(self):
                notification()

            def another_notification(self):
                notification()

        states = ['A', {'name': 'B', 'timeout': 0.05, 'on_timeout': 'timeout'}]
        model = Model()
        machine = CustomMachine(model=model, states=states, initial='A')
        model.to_B()
        sleep(0.1)
        self.assertTrue(timeout.called)
        self.assertTrue(counter.called)
        machine.get_state('B').add_callback('timeout', 'notification')
        machine.on_timeout_B('another_notification')
        model.to_B()
        sleep(0.1)
        self.assertEqual(timeout.call_count, 2)
        self.assertEqual(counter.call_count, 2)
        self.assertTrue(notification.called)
        machine.get_state('B').on_timeout = []
        model.to_B()
        sleep(0.1)
        self.assertEqual(timeout.call_count, 2)
        self.assertEqual(notification.call_count, 2)

    def test_timeout_transitioning(self):
        timeout_mock = MagicMock()

        @add_state_features(Timeout)
        class CustomMachine(Machine):
            pass

        states = ['A', {'name': 'B', 'timeout': 0.05, 'on_timeout': ['to_A', timeout_mock]}]
        machine = CustomMachine(states=states, initial='A')
        machine.to_B()
        sleep(0.1)
        self.assertTrue(machine.is_A())
        self.assertTrue(timeout_mock.called)

    def test_volatile(self):

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

        m.to_B()
        self.assertEqual(m.scope.value, 5)

        # should call method of TemporalState
        m.scope.increase()
        self.assertEqual(m.scope.value, 6)

        # re-entering state should reset default volatile object
        m.to_A()
        self.assertFalse(hasattr(m.scope, 'value'))

        m.scope.foo = 'bar'
        m.to_B()
        # custom attribute of A should be gone
        self.assertFalse(hasattr(m.scope, 'foo'))
        # value should be reset
        self.assertEqual(m.scope.value, 5)


class TestStatesDiagramsLockedNested(TestDiagramsLockedNested):

    def setUp(self):

        machine_cls = MachineFactory.get_predefined(locked=True, nested=True, graph=True)

        @add_state_features(Error, Timeout, Volatile)
        class CustomMachine(machine_cls):
            pass

        super(TestStatesDiagramsLockedNested, self).setUp()
        self.machine_cls = CustomMachine

    def test_nested_notebook(self):
        # test will create a custom state machine already. This will cause errors when inherited.
        self.assertTrue(True)
