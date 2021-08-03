try:
    from builtins import object
except ImportError:
    pass

import time
from threading import Thread
import logging

from transitions.extensions import MachineFactory
from .test_nesting import TestNestedTransitions as TestsNested
from .test_core import TestTransitions as TestCore
from .utils import Stuff, DummyModel, SomeContext

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def heavy_processing():
    time.sleep(1)


def heavy_checking():
    time.sleep(0.5)
    return False


class TestLockedTransitions(TestCore):

    def setUp(self):
        self.machine_cls = MachineFactory.get_predefined(locked=True)
        self.stuff = Stuff(machine_cls=self.machine_cls)
        self.stuff.heavy_processing = heavy_processing
        self.stuff.machine.add_transition('forward', 'A', 'B', before='heavy_processing')

    def tearDown(self):
        pass

    def test_thread_access(self):
        thread = Thread(target=self.stuff.forward)
        thread.start()
        # give thread some time to start
        time.sleep(0.01)
        self.assertTrue(self.stuff.is_B())

    def test_parallel_access(self):
        thread = Thread(target=self.stuff.forward)
        thread.start()
        # give thread some time to start
        time.sleep(0.01)
        self.stuff.to_C()
        # if 'forward' has not been locked, it is still running
        # we have to wait to be sure it is done
        time.sleep(1)
        self.assertEqual(self.stuff.state, "C")

    def test_parallel_deep(self):
        self.stuff.machine.add_transition('deep', source='*', dest='C', after='to_D')
        thread = Thread(target=self.stuff.deep)
        thread.start()
        time.sleep(0.01)
        self.stuff.to_C()
        time.sleep(1)
        self.assertEqual(self.stuff.state, "C")

    def test_conditional_access(self):
        self.stuff.heavy_checking = heavy_checking  # checking takes 1s and returns False
        self.stuff.machine.add_transition('advance', 'A', 'B', conditions='heavy_checking')
        self.stuff.machine.add_transition('advance', 'A', 'D')
        t = Thread(target=self.stuff.advance)
        t.start()
        time.sleep(0.1)
        logger.info('Check if state transition done...')
        # Thread will release lock before Transition is finished
        res = self.stuff.is_D()
        self.assertTrue(res)

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
        self.assertTrue(stuff2.is_B())
        # check if machines of stuff and stuff2 are truly separated
        stuff2.to_A()
        self.stuff.to_C()
        self.assertTrue(stuff2.is_A())
        thread = Thread(target=stuff2.forward)
        thread.start()
        # give thread some time to start
        time.sleep(0.01)
        # both objects should be in different states
        # and also not share locks
        begin = time.time()
        # stuff should not be locked and execute fast
        self.assertTrue(self.stuff.is_C())
        fast = time.time()
        # stuff2 should be locked and take about 1 second
        # to be executed
        self.assertTrue(stuff2.is_B())
        blocked = time.time()
        self.assertAlmostEqual(fast - begin, 0, delta=0.1)
        self.assertAlmostEqual(blocked - begin, 1, delta=0.1)

    def test_context_managers(self):

        class CounterContext(object):
            def __init__(self):
                self.counter = 0
                self.level = 0
                self.max = 0
                super(CounterContext, self).__init__()

            def __enter__(self):
                self.counter += 1
                self.level += 1
                self.max = max(self.level, self.max)

            def __exit__(self, *exc):
                self.level -= 1

        M = MachineFactory.get_predefined(locked=True)
        c = CounterContext()
        m = M(states=['A', 'B', 'C', 'D'], transitions=[['reset', '*', 'A']], initial='A', machine_context=c)
        m.get_triggers('A')
        self.assertEqual(c.max, 1)  # was 3 before
        self.assertEqual(c.counter, 4)  # was 72 (!) before

    # This test has been used to quantify the changes made in locking in version 0.5.0.
    # See https://github.com/tyarkoni/transitions/issues/167 for the results.
    # def test_performance(self):
    #     import timeit
    #     states = ['A', 'B', 'C']
    #     transitions = [['go', 'A', 'B'], ['go', 'B', 'C'], ['go', 'C', 'A']]
    #
    #     M1 = MachineFactory.get_predefined()
    #     M2 = MachineFactory.get_predefined(locked=True)
    #
    #     def test_m1():
    #         m1 = M1(states=states, transitions=transitions, initial='A')
    #         m1.get_triggers('A')
    #
    #     def test_m2():
    #         m2 = M2(states=states, transitions=transitions, initial='A')
    #         m2.get_triggers('A')
    #
    #     t1 = timeit.timeit(test_m1, number=20000)
    #     t2 = timeit.timeit(test_m2, number=20000)
    #     self.assertAlmostEqual(t2/t1, 1, delta=0.5)


class TestMultipleContexts(TestCore):

    def setUp(self):
        self.event_list = []

        self.s1 = DummyModel()

        self.c1 = SomeContext(event_list=self.event_list)
        self.c2 = SomeContext(event_list=self.event_list)
        self.c3 = SomeContext(event_list=self.event_list)
        self.c4 = SomeContext(event_list=self.event_list)

        self.machine_cls = MachineFactory.get_predefined(locked=True)
        self.stuff = Stuff(machine_cls=self.machine_cls, extra_kwargs={
            'machine_context': [self.c1, self.c2]
        })
        self.stuff.machine.add_model(self.s1, model_context=[self.c3, self.c4])
        del self.event_list[:]

        self.stuff.machine.add_transition('forward', 'A', 'B')

    def tearDown(self):
        self.stuff.machine.remove_model(self.s1)

    def test_ordering(self):
        self.stuff.forward()
        # There are a lot of internal enter/exits, but the key is that the outermost are in the expected order
        self.assertEqual((self.c1, "enter"), self.event_list[0])
        self.assertEqual((self.c2, "enter"), self.event_list[1])
        self.assertEqual((self.c2, "exit"), self.event_list[-2])
        self.assertEqual((self.c1, "exit"), self.event_list[-1])

    def test_model_context(self):
        self.s1.forward()
        self.assertEqual((self.c1, "enter"), self.event_list[0])
        self.assertEqual((self.c2, "enter"), self.event_list[1])

        # Since there are a lot of internal enter/exits, we don't actually know how deep in the stack
        # to look for these. Should be able to correct when https://github.com/tyarkoni/transitions/issues/167
        self.assertIn((self.c3, "enter"), self.event_list)
        self.assertIn((self.c4, "enter"), self.event_list)
        self.assertIn((self.c4, "exit"), self.event_list)
        self.assertIn((self.c3, "exit"), self.event_list)

        self.assertEqual((self.c2, "exit"), self.event_list[-2])
        self.assertEqual((self.c1, "exit"), self.event_list[-1])


# Same as TestLockedTransition but with LockedHierarchicalMachine
class TestLockedHierarchicalTransitions(TestsNested, TestLockedTransitions):

    def setUp(self):
        states = ['A', 'B', {'name': 'C', 'children': ['1', '2', {'name': '3', 'children': ['a', 'b', 'c']}]},
                  'D', 'E', 'F']
        self.machine_cls = MachineFactory.get_predefined(locked=True, nested=True)
        self.state_cls = self.machine_cls.state_cls
        self.state_cls.separator = '_'
        self.stuff = Stuff(states, machine_cls=self.machine_cls)
        self.stuff.heavy_processing = heavy_processing
        self.stuff.machine.add_transition('forward', '*', 'B', before='heavy_processing')

    def test_parallel_access(self):
        thread = Thread(target=self.stuff.forward)
        thread.start()
        # give thread some time to start
        time.sleep(0.01)
        self.stuff.to_C()
        # if 'forward' has not been locked, it is still running
        # we have to wait to be sure it is done
        time.sleep(1)
        self.assertEqual(self.stuff.state, "C")

    def test_callbacks(self):

        class MachineModel(self.stuff.machine_cls):
            def __init__(self):
                self.mock = MagicMock()
                super(MachineModel, self).__init__(self, states=['A', 'B', 'C'])

            def on_enter_A(self):
                self.mock()

        model = MachineModel()
        model.to_A()
        self.assertTrue(model.mock.called)

    def test_pickle(self):
        import sys
        if sys.version_info < (3, 4):
            import dill as pickle
        else:
            import pickle

        states = ['A', 'B', {'name': 'C', 'children': ['1', '2', {'name': '3', 'children': ['a', 'b', 'c']}]},
                  'D', 'E', 'F']
        transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'B'},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'D'}
        ]
        m = self.stuff.machine_cls(states=states, transitions=transitions, initial='A')
        m.heavy_processing = heavy_processing
        m.add_transition('forward', 'A', 'B', before='heavy_processing')

        # # go to non initial state B
        m.to_B()

        # pickle Stuff model
        dump = pickle.dumps(m)
        self.assertIsNotNone(dump)
        m2 = pickle.loads(dump)
        self.assertTrue(m2.is_B())
        m2.to_C_3_a()
        m2.to_C_3_b()
        # check if machines of stuff and stuff2 are truly separated
        m2.to_A()
        m.to_C()
        self.assertTrue(m2.is_A())
        thread = Thread(target=m2.forward)
        thread.start()
        # give thread some time to start
        time.sleep(0.01)
        # both objects should be in different states
        # and also not share locks
        begin = time.time()
        # stuff should not be locked and execute fast
        self.assertTrue(m.is_C())
        fast = time.time()
        # stuff2 should be locked and take about 1 second
        # to be executed
        self.assertTrue(m2.is_B())
        blocked = time.time()
        self.assertAlmostEqual(fast - begin, 0, delta=0.1)
        self.assertAlmostEqual(blocked - begin, 1, delta=0.1)
