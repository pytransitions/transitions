try:
    from builtins import object
except ImportError:
    pass

import time
from threading import Thread
import logging

from transitions.extensions import MachineFactory
from .test_nesting import TestTransitions as TestsNested
from .test_core import TestTransitions as TestCore
from .utils import Stuff

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def heavy_processing():
    time.sleep(1)


def heavy_checking():
    time.sleep(1)
    return False


class TestLockedTransitions(TestCore):

    def setUp(self):
        self.stuff = Stuff(machine_cls=MachineFactory.get_predefined(locked=True))
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

    def test_conditional_access(self):
        self.stuff.heavy_checking = heavy_checking # checking takes 1s and returns False
        self.stuff.machine.add_transition('advance', 'A', 'B', conditions='heavy_checking')
        self.stuff.machine.add_transition('advance', 'A', 'D')
        t = Thread(target=self.stuff.advance)
        t.start()
        time.sleep(0.1)
        logger.info('Check if state transition done...')
        # Thread will release lock before Transition is finished
        self.assertTrue(self.stuff.machine.is_state('D'))

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
        print(stuff2)
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


# Same as TestLockedTransition but with LockedHierarchicalMachine
class TestLockedHierarchicalTransitions(TestsNested, TestLockedTransitions):
    def setUp(self):
        states = ['A', 'B', {'name': 'C', 'children': ['1', '2', {'name': '3', 'children': ['a', 'b', 'c']}]},
          'D', 'E', 'F']
        self.stuff = Stuff(states, machine_cls=MachineFactory.get_predefined(locked=True, nested=True))
        self.stuff.heavy_processing = heavy_processing
        self.stuff.machine.add_transition('process', '*', 'B', before='heavy_processing')

    def test_parallel_access(self):
        thread = Thread(target=self.stuff.process)
        thread.start()
        # give thread some time to start
        time.sleep(0.01)
        self.stuff.to_C()
        # if 'process' has not been locked, it is still running
        # we have to wait to be sure it is done
        time.sleep(1)
        self.assertEqual(self.stuff.state, "C_1")

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
        self.assertTrue(self.stuff.machine.is_state("C_1"))
        fast = time.time()
        # stuff2 should be locked and take about 1 second
        # to be executed
        self.assertTrue(stuff2.machine.is_state("B"))
        blocked = time.time()
        self.assertAlmostEqual(fast-begin, 0, delta=0.1)
        self.assertAlmostEqual(blocked-begin, 1, delta=0.1)
