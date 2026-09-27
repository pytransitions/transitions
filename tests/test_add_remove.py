try:
    from builtins import object
except ImportError:
    pass

from transitions import Machine
from unittest import TestCase

import gc
import weakref
import threading


class Dummy(object):
    pass


class TestTransitionsAddRemove(TestCase):

    def test_queued_remove_other_model(self):
        active, removed = Dummy(), Dummy()
        machine = Machine([active, removed], states=['idle', 'busy'], initial='idle',
                          queued=True, auto_transitions=False)
        calls = []

        def remove_other():
            calls.append('start')
            machine.remove_model(removed)

        machine.add_transition('start', 'idle', 'busy', after=remove_other)
        self.assertTrue(active.start())
        self.assertEqual(calls, ['start'])
        self.assertEqual(active.state, 'busy')
        self.assertEqual(removed.state, 'idle')
        self.assertEqual(machine.models, [active])
        self.assertFalse(machine._transition_queue)

    def test_queued_remove_other_models_preserves_pending_order(self):
        active, removed, remaining, also_removed = Dummy(), Dummy(), Dummy(), Dummy()
        machine = Machine([active, removed, remaining, also_removed], states=['idle', 'busy', 'done'],
                          initial='idle', queued=True, auto_transitions=False, send_event=True)
        calls = []

        def after_start(event):
            calls.append((event.model, 'start'))
            if event.model is active:
                removed.start()
                active.finish()
                also_removed.start()
                remaining.start()
                machine.remove_model([removed, also_removed])

        machine.add_transition('start', 'idle', 'busy', after=after_start)
        machine.add_transition('finish', 'busy', 'done',
                               after=lambda event: calls.append((event.model, 'finish')))
        self.assertTrue(active.start())
        self.assertEqual(calls, [(active, 'start'), (active, 'finish'), (remaining, 'start')])
        self.assertEqual([model.state for model in [active, removed, remaining, also_removed]],
                         ['done', 'idle', 'busy', 'idle'])
        self.assertEqual(machine.models, [active, remaining])
        self.assertFalse(machine._transition_queue)

    def test_queued_remove_active_model_preserves_other_pending_events(self):
        active, remaining = Dummy(), Dummy()
        machine = Machine([active, remaining], states=['idle', 'busy', 'done'], initial='idle',
                          queued=True, auto_transitions=False, send_event=True)
        calls = []

        def after_start(event):
            calls.append(event.model)
            if event.model is active:
                active.finish()
                remaining.start()
                machine.remove_model(active)

        machine.add_transition('start', 'idle', 'busy', after=after_start)
        machine.add_transition('finish', 'busy', 'done')
        self.assertTrue(active.start())
        self.assertEqual(calls, [active, remaining])
        self.assertEqual([active.state, remaining.state], ['busy', 'busy'])
        self.assertEqual(machine.models, [remaining])
        self.assertFalse(machine._transition_queue)

    def test_garbage_collection(self):

        states = ['A', 'B', 'C', 'D', 'E', 'F']
        machine = Machine(model=[], states=states, initial='A', name='Test Machine')
        machine.add_transition('advance', 'A', 'B')
        machine.add_transition('advance', 'B', 'C')
        machine.add_transition('advance', 'C', 'D')

        s1 = Dummy()
        s2 = Dummy()

        s2_collected = threading.Event()
        s2_proxy = weakref.proxy(s2, lambda _: s2_collected.set())

        machine.add_model([s1, s2])

        self.assertTrue(s1.is_A())
        self.assertTrue(s2.is_A())
        s1.advance()

        self.assertTrue(s1.is_B())
        self.assertTrue(s2.is_A())

        self.assertFalse(s2_collected.is_set())
        machine.remove_model(s2)
        del s2
        gc.collect()
        self.assertTrue(s2_collected.is_set())

        s3 = Dummy()
        machine.add_model(s3)
        s3.advance()
        s3.advance()
        self.assertTrue(s3.is_C())

    def test_add_model_initial_state(self):
        states = ['A', 'B', 'C', 'D', 'E', 'F']
        machine = Machine(model=[], states=states, initial='A', name='Test Machine')
        machine.add_transition('advance', 'A', 'B')
        machine.add_transition('advance', 'B', 'C')
        machine.add_transition('advance', 'C', 'D')

        s1 = Dummy()
        s2 = Dummy()
        s3 = Dummy()

        machine.add_model(s1)
        machine.add_model(s2, initial='B')
        machine.add_model(s3, initial='C')

        s1.advance()
        s2.advance()
        s3.advance()

        self.assertTrue(s1.is_B())
        self.assertTrue(s2.is_C())
        self.assertTrue(s3.is_D())

    def test_add_model_no_initial_state(self):
        states = ['A', 'B', 'C', 'D', 'E', 'F']
        machine = Machine(model=[], states=states, name='Test Machine', initial=None)
        machine.add_transition('advance', 'A', 'B')
        machine.add_transition('advance', 'B', 'C')
        machine.add_transition('advance', 'C', 'D')

        s1 = Dummy()
        s2 = Dummy()
        s3 = Dummy()

        with self.assertRaises(ValueError):
            machine.add_model(s1)
        machine.add_model(s1, initial='A')
        machine.add_model(s2, initial='B')
        machine.add_model(s3, initial='C')

        s1.advance()
        s2.advance()
        s3.advance()

        self.assertTrue(s1.is_B())
        self.assertTrue(s2.is_C())
        self.assertTrue(s3.is_D())
