try:
    from builtins import object
except ImportError:
    pass

from transitions.core import Enum
from transitions.extensions.markup import MarkupMachine, rep
from transitions.extensions import MachineFactory
from transitions.extensions.factory import HierarchicalMarkupMachine
from .utils import Stuff
from functools import partial


from unittest import TestCase, skipIf

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

try:
    import enum
except ImportError:
    enum = None


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
        self.num_trans = len(self.transitions)
        self.num_auto = len(self.states) ** 2

    def test_markup_self(self):
        m1 = self.machine_cls(states=self.states, transitions=self.transitions, initial='A')
        m1.walk()
        m2 = self.machine_cls(markup=m1.markup)
        self.assertTrue(m1.state == m2.state or m1.state.name == m2.state)
        self.assertEqual(len(m1.models), len(m2.models))
        self.assertEqual(sorted(m1.states.keys()), sorted(m2.states.keys()))
        self.assertEqual(sorted(m1.events.keys()), sorted(m2.events.keys()))
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
        self.assertTrue(model1.state == model2.state or model1.state.name == model2.state)
        self.assertEqual(sorted(m1.states.keys()), sorted(m2.states.keys()))
        self.assertEqual(sorted(m1.events.keys()), sorted(m2.events.keys()))

    def test_conditions_unless(self):
        s = Stuff(machine_cls=self.machine_cls)
        s.machine.add_transition('go', 'A', 'B', conditions='this_passes',
                                 unless=['this_fails', 'this_fails_by_default'])
        t = s.machine.markup['transitions']
        self.assertEqual(len(t), 1)
        self.assertEqual(t[0]['trigger'], 'go')
        self.assertEqual(len(t[0]['conditions']), 1)
        self.assertEqual(len(t[0]['unless']), 2)

    def test_auto_transitions(self):
        m1 = self.machine_cls(states=self.states, transitions=self.transitions, initial='A')
        m2 = self.machine_cls(states=self.states, transitions=self.transitions, initial='A',
                              auto_transitions_markup=True)

        self.assertEqual(len(m1.markup.get('transitions')), self.num_trans)
        self.assertEqual(len(m2.markup.get('transitions')), self.num_trans + self.num_auto)
        m1.add_transition('go', 'A', 'B')
        m2.add_transition('go', 'A', 'B')
        self.num_trans += 1
        self.assertEqual(len(m1.markup.get('transitions')), self.num_trans)
        self.assertEqual(len(m2.markup.get('transitions')), self.num_trans + self.num_auto)
        m1.auto_transitions_markup = True
        m2.auto_transitions_markup = False
        self.assertEqual(len(m1.markup.get('transitions')), self.num_trans + self.num_auto)
        self.assertEqual(len(m2.markup.get('transitions')), self.num_trans)


class TestMarkupHierarchicalMachine(TestMarkupMachine):

    def setUp(self):
        self.states = ['A', 'B', {'name': 'C',
                                  'children': ['1', '2', {'name': '3', 'children': ['a', 'b', 'c']}]}]

        self.transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'C_1'},
            {'trigger': 'run', 'source': 'C_1', 'dest': 'C_3_a'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'B'}
        ]

        # MarkupMachine cannot be imported via get_predefined as of now
        # We want to be able to run these tests without (py)graphviz
        self.machine_cls = HierarchicalMarkupMachine
        self.num_trans = len(self.transitions)
        self.num_auto = len(self.states) * 9

    def test_nested_definitions(self):
        states = [{'name': 'A'},
                  {'name': 'B'},
                  {'name': 'C',
                   'children': [
                       {'name': '1'},
                       {'name': '2'}],
                   'transitions': [
                       {'trigger': 'go',
                        'source': '1',
                        'dest': '2'}],
                   'initial': '2'}]
        machine = self.machine_cls(states=states, initial='A', auto_transitions=False, name='TestMachine')
        markup = {k: v for k, v in machine.markup.items() if v and k != 'models'}
        self.assertEqual(dict(initial='A', states=states, name='TestMachine'), markup)


@skipIf(enum is None, "enum is not available")
class TestMarkupMachineEnum(TestMarkupMachine):

    class States(Enum):
        A = 1
        B = 2
        C = 3
        D = 4

    def setUp(self):
        self.machine_cls = MarkupMachine
        self.states = TestMarkupMachineEnum.States
        self.transitions = [
            {'trigger': 'walk', 'source': self.states.A, 'dest': self.states.B},
            {'trigger': 'run', 'source': self.states.B, 'dest': self.states.C},
            {'trigger': 'sprint', 'source': self.states.C, 'dest': self.states.D}
        ]
        self.num_trans = len(self.transitions)
        self.num_auto = len(self.states)**2
