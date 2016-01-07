try:
    from builtins import object
except ImportError:
    pass

import time
from threading import Thread

from transitions import LockedHierarchicalMachine as Machine
from .utils import Stuff
from unittest import TestCase

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock


def heavy_processing():
    time.sleep(1)


class TestTransitions(TestCase):

    def setUp(self):
        self.stuff = Stuff(machine_cls=Machine)
        self.stuff.heavy_processing = heavy_processing
        self.stuff.machine.add_transition('process', '*', 'B', before='heavy_processing')

    def tearDown(self):
        pass

    def test_thread_access(self):
        thread = Thread(target=self.stuff.process)
        thread.start()
        # give thread some time to start
        time.sleep(0.01)
        self.assertTrue(self.stuff.machine.is_state("B"))

    def test_parallel_access(self):
        thread = Thread(target=self.stuff.process)
        thread.start()
        # give thread some time to start
        time.sleep(0.01)
        self.stuff.to_C()
        # if 'process' has not been locked, it is still running
        # we have to wait to be sure it is done
        time.sleep(1)
        self.assertEqual(self.stuff.state, "C")

    def test_pickle(self):
        import sys
        if sys.version_info < (3, 4):
            import dill as pickle
        else:
            import pickle

        # go to non initial state B
        self.stuff.to_B()
        # pickle Stuff model
        dump = pickle.dumps(self.stuff)
        self.assertIsNotNone(dump)
        stuff2 = pickle.loads(dump)
        self.assertTrue(stuff2.machine.is_state("B"))
        # check if machines of stuff and stuff2 are truly separated
        stuff2.to_A()
        self.stuff.to_C()
        self.assertTrue(stuff2.machine.is_state("A"))
        thread = Thread(target=stuff2.process)
        thread.start()
        # give thread some time to start
        time.sleep(0.01)
        # both objects should be in different states
        # and also not share locks
        begin = time.time()
        # stuff should not be locked and execute fast
        self.assertTrue(self.stuff.machine.is_state("C"))
        fast = time.time()
        # stuff2 should be locked and take about 1 second
        # to be executed
        self.assertTrue(stuff2.machine.is_state("B"))
        blocked = time.time()
        self.assertAlmostEqual(fast-begin, 0, delta=0.1)
        self.assertAlmostEqual(blocked-begin, 1, delta=0.1)




