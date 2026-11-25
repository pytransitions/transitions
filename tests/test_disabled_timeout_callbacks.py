from unittest import TestCase
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

from transitions import Machine
from transitions.extensions.states import Timeout, add_state_features


@add_state_features(Timeout)
class TimeoutMachine(Machine):
    pass


class CallbackModel(object):
    def __init__(self):
        self.calls = []

    def expired(self):
        self.calls.append('expired')

    def extra(self):
        self.calls.append('extra')


class DisabledTimeoutTests(TestCase):
    def test_dynamic_registration_with_disabled_timeout(self):
        for kind in ('string', 'callable', 'none', 'list'):
            model = CallbackModel()
            callback = {'string': 'expired', 'callable': model.expired,
                        'none': None, 'list': ['expired']}[kind]
            machine = TimeoutMachine(model=model, initial='A', states=[
                'A', {'name': 'B', 'timeout': 0, 'on_timeout': callback}])
            machine.on_timeout_B('extra')
            state = machine.get_state('B')
            state.timeout = 1
            with patch('transitions.extensions.states.Timer') as timer:
                model.to_B()
                args, kwargs = timer.call_args
                args[1](*kwargs['args'])
            expected = ['extra'] if kind == 'none' else ['expired', 'extra']
            self.assertEqual(model.calls, expected)

    def test_default_callbacks_can_be_registered(self):
        model = CallbackModel()
        machine = TimeoutMachine(model=model, initial='A', states=['A', 'B'])
        machine.on_timeout_B('extra')
        self.assertEqual(machine.get_state('B').on_timeout, ['extra'])
