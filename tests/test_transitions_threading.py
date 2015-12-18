try:
    from builtins import object
except ImportError:
    pass

import time
import thread

from transitions import State, MachineError
from transitions import MutexMachine as Machine
from unittest import TestCase

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock


class Stuff(object):

    def __init__(self):

        self.state = None

        states = ['A', 'B', 'C', 'D', 'E', 'F']
        self.machine = Machine(self, states=states, initial='A')

    def on_enter_B(self):
        time.sleep(1)

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

    def test_thread_access(self):
        thread.start_new_thread ( self.stuff.to_B, ())
        # give thread some time to start
        time.sleep(0.01)
        self.assertTrue( self.stuff.machine.is_state("B"))

    def test_parallel_access(self):
        thread.start_new_thread(self.stuff.to_B, ())
        # give thread some time to start
        time.sleep(0.01)
        self.stuff.to_C()
        self.assertEqual(self.stuff.state, "C")