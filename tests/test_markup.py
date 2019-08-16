try:
    from builtins import object
except ImportError:
    pass

from transitions.extensions.markup import MarkupMachine, rep
from transitions.extensions.factory import HierarchicalMarkupMachine
from .utils import Stuff
from functools import partial


from unittest import TestCase

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock


class SimpleModel(object):

    def after_func(self):
        pass


class TestRep(TestCase):

    def test_rep_string(self):
        self.assertEqual(rep("string"), "string")

    def test_rep_function(self):
        def check():
            return True
        self.assertTrue(check())
        self.assertEqual(rep(check), "check")

    def test_rep_partial_no_args_no_kwargs(self):
        def check():
            return True
        pcheck = partial(check)
        self.assertTrue(pcheck())
        self.assertEqual(rep(pcheck), "check()")

    def test_rep_partial_with_args(self):
        def check(result):
            return result
        pcheck = partial(check, True)
        self.assertTrue(pcheck())
        self.assertEqual(rep(pcheck), "check(True)")

    def test_rep_partial_with_kwargs(self):
        def check(result=True):
            return result
        pcheck = partial(check, result=True)
        self.assertTrue(pcheck())
        self.assertEqual(rep(pcheck), "check(result=True)")

    def test_rep_partial_with_args_and_kwargs(self):
        def check(result, doublecheck=True):
            return result == doublecheck
        pcheck = partial(check, True, doublecheck=True)
        self.assertTrue(pcheck())
        self.assertEqual(rep(pcheck), "check(True, doublecheck=True)")

    def test_rep_callable_class(self):
        class Check(object):
            def __init__(self, result):
                self.result = result

            def __call__(self):
                return self.result

            def __repr__(self):
                return "%s(%r)" % (type(self).__name__, self.result)

        ccheck = Check(True)
        self.assertTrue(ccheck())
        self.assertEqual(rep(ccheck), "Check(True)")


class TestMarkupMachine(TestCase):

    def setUp(self):
        self.machine_cls = MarkupMachine
        self.states = ['A', 'B', 'C', 'D']
        self.transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'B'},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'D'}
        ]

    def test_markup_self(self):

        m1 = self.machine_cls(states=self.states, transitions=self.transitions, initial='A')
        m1.walk()
        # print(m1.markup)
        m2 = self.machine_cls(markup=m1.markup)
        self.assertEqual(m1.state, m2.state)
        self.assertEqual(len(m1.models), len(m2.models))
        self.assertEqual(m1.states.keys(), m2.states.keys())
        self.assertEqual(m1.events.keys(), m2.events.keys())
        m2.run()
        m2.sprint()
        self.assertNotEqual(m1.state, m2.state)

    def test_markup_model(self):

        model1 = SimpleModel()
        m1 = self.machine_cls(model1, states=self.states, transitions=self.transitions, initial='A')
        model1.walk()
        m2 = self.machine_cls(markup=m1.markup)
        model2 = m2.models[0]
        self.assertIsInstance(model2, SimpleModel)
        self.assertEqual(len(m1.models), len(m2.models))
        self.assertEqual(model1.state, model2.state)
        self.assertEqual(m1.states.keys(), m2.states.keys())
        self.assertEqual(m1.events.keys(), m2.events.keys())

    def test_conditions_unless(self):
        s = Stuff(machine_cls=self.machine_cls)
        s.machine.add_transition('go', 'A', 'B', conditions='this_passes',
                                 unless=['this_fails', 'this_fails_by_default'])
        t = s.machine.markup['transitions']
        self.assertEqual(len(t), 1)
        self.assertEqual(t[0]['trigger'], 'go')
        self.assertEqual(len(t[0]['conditions']), 1)
        self.assertEqual(len(t[0]['unless']), 2)


class TestMarkupHierarchicalMachine(TestMarkupMachine):

    def setUp(self):
        self.states = ['A', 'B', {'name': 'C',
                                  'children': ['1', '2', {'name': '3', 'children': ['a', 'b', 'c']}]}]

        self.transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'C_1'},
            {'trigger': 'run', 'source': 'C_1', 'dest': 'C_3_a'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'B'}
        ]

        self.machine_cls = HierarchicalMarkupMachine
