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
