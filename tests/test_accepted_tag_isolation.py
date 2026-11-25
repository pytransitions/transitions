from unittest import TestCase

from transitions import Machine, MachineError
from transitions.extensions.states import Error, add_state_features


@add_state_features(Error)
class ErrorMachine(Machine):
    pass


class AcceptedTagIsolationTests(TestCase):
    def test_accepted_state_does_not_accept_another_terminal_state(self):
        tags = ['terminal']
        machine = ErrorMachine(
            states=['start', {'name': 'success', 'tags': tags, 'accepted': True},
                    {'name': 'failure', 'tags': tags}],
            initial='start', auto_transitions=False,
            transitions=[['succeed', 'start', 'success'],
                         ['fail', 'start', 'failure']])
        machine.succeed()
        self.assertTrue(machine.get_state('success').is_accepted)
        machine.set_state('start')
        with self.assertRaises(MachineError):
            machine.fail()
        self.assertEqual(tags, ['terminal'])

    def test_accepting_two_states_does_not_duplicate_tags(self):
        tags = ['terminal']
        machine = ErrorMachine(
            states=[{'name': 'first', 'tags': tags, 'accepted': True},
                    {'name': 'second', 'tags': tags, 'accepted': True}],
            initial='first')
        self.assertEqual(machine.get_state('first').tags, ['terminal', 'accepted'])
        self.assertEqual(machine.get_state('second').tags, ['terminal', 'accepted'])
        self.assertEqual(tags, ['terminal'])
