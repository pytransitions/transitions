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
