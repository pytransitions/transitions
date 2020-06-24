try:
    from builtins import object
except ImportError:
    pass

from collections import OrderedDict

from transitions.extensions.nesting import NestedState as State, _build_state_list
from .test_nesting import TestNestedTransitions as TestNested

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock


class TestParallel(TestNested):

    def setUp(self):
        super(TestParallel, self).setUp()
        self.states = ['A', 'B', {'name': 'C',
                                  'parallel': [{'name': '1', 'children': ['a', 'b'],
                                                'initial': 'a',
                                                'transitions': [['go', 'a', 'b']]},
                                               {'name': '2', 'children': ['a', 'b'],
                                                'initial': 'a',
                                                'transitions': [['go', 'a', 'b']]}]}]
        self.transitions = [['reset', 'C', 'A']]

    def test_init(self):
        m = self.stuff.machine_cls(states=self.states)
        m.to_C()
        self.assertEqual(['C{0}1{0}a'.format(State.separator), 'C{0}2{0}a'.format(State.separator)], m.state)

    def test_enter(self):
        m = self.stuff.machine_cls(states=self.states, transitions=self.transitions, initial='A')
        m.to_C()
        m.go()
        self.assertEqual(['C{0}1{0}b'.format(State.separator), 'C{0}2{0}b'.format(State.separator)], m.state)

    def test_exit(self):

        class Model:

            def __init__(self):
                self.mock = MagicMock()

            def on_exit_C(self):
                self.mock()

            def on_exit_C_1(self):
                self.mock()

            def on_exit_C_2(self):
                self.mock()

        model1 = Model()
        m = self.stuff.machine_cls(model1, states=self.states, transitions=self.transitions, initial='A')
        m.add_transition('reinit', 'C', 'C')
        model1.to_C()
        self.assertEqual(['C{0}1{0}a'.format(State.separator), 'C{0}2{0}a'.format(State.separator)], model1.state)
        model1.reset()
        self.assertTrue(model1.is_A())
        self.assertEqual(3, model1.mock.call_count)

        model2 = Model()
        m.add_model(model2, initial='C')
        model2.reinit()
        self.assertEqual(['C{0}1{0}a'.format(State.separator), 'C{0}2{0}a'.format(State.separator)], model2.state)
        self.assertEqual(3, model2.mock.call_count)
        model2.reset()
        self.assertTrue(model2.is_A())
        self.assertEqual(6, model2.mock.call_count)
        for mod in m.models:
            mod.trigger('to_C')
        for mod in m.models:
            mod.trigger('reset')
        self.assertEqual(6, model1.mock.call_count)
        self.assertEqual(9, model2.mock.call_count)

    def test_parent_transition(self):
        m = self.stuff.machine_cls(states=self.states)
        m.add_transition('switch', 'C{0}2{0}a'.format(State.separator), 'C{0}2{0}b'.format(State.separator))
        m.to_C()
        m.switch()
        self.assertEqual(['C{0}1{0}a'.format(State.separator), 'C{0}2{0}b'.format(State.separator)], m.state)

    def test_shallow_parallel(self):
        sep = self.state_cls.separator
        states = [
            {
                'name': 'P', 'parallel':
                [
                    '1',  # no initial state
                    {'name': '2', 'children': ['a', 'b'], 'initial': 'b'}
                ]
            },
            'X'
        ]
        m = self.machine_cls(states=states, initial='P')
        self.assertEqual(['P{0}1'.format(sep), 'P{0}2{0}b'.format(sep)], m.state)
        m.to_X()
        self.assertEqual('X', m.state)
        m.to_P()
        self.assertEqual(['P{0}1'.format(sep), 'P{0}2{0}b'.format(sep)], m.state)

    def test_multiple(self):
        states = ['A',
                  {'name': 'B',
                   'parallel': [
                       {'name': '1', 'parallel': [
                           {'name': 'a', 'children': ['x', 'y', 'z'], 'initial': 'z'},
                           {'name': 'b', 'children': ['x', 'y', 'z'], 'initial': 'y'}
                       ]},
                       {'name': '2', 'children': ['a', 'b', 'c'], 'initial': 'a'},
                   ]}]

        m = self.stuff.machine_cls(states=states, initial='A')
        self.assertTrue(m.is_A())
        m.to_B()
        self.assertEqual([['B{0}1{0}a{0}z'.format(State.separator),
                           'B{0}1{0}b{0}y'.format(State.separator)],
                          'B{0}2{0}a'.format(State.separator)], m.state)
        m.to_A()
        self.assertEqual('A', m.state)

    def test_multiple_deeper(self):
        sep = self.state_cls.separator
        states = ['A',
                  {'name': 'P',
                   'parallel': [
                       '1',
                       {'name': '2', 'parallel': [
                           {'name': 'a'},
                           {'name': 'b', 'parallel': [
                               {'name': 'x', 'parallel': ['1', '2']}, 'y'
                           ]}
                       ]},
                   ]}]
        ref_state = ['P{0}1'.format(sep),
                     ['P{0}2{0}a'.format(sep),
                     [['P{0}2{0}b{0}x{0}1'.format(sep),
                       'P{0}2{0}b{0}x{0}2'.format(sep)],
                      'P{0}2{0}b{0}y'.format(sep)]]]

        m = self.stuff.machine_cls(states=states, initial='A')
        self.assertTrue(m.is_A())
        m.to_P()
        self.assertEqual(ref_state, m.state)
        m.to_A()

    def test_model_state_conversion(self):
        sep = self.state_cls.separator
        states = ['P{0}1'.format(sep),
                  ['P{0}2{0}a'.format(sep),
                   [['P{0}2{0}b{0}x{0}1'.format(sep),
                     'P{0}2{0}b{0}x{0}2'.format(sep)],
                    'P{0}2{0}b{0}y'.format(sep)]]]
        tree = OrderedDict(
            [('P', OrderedDict(
                [('1', OrderedDict()),
                 ('2', OrderedDict(
                     [('a', OrderedDict()),
                      ('b', OrderedDict(
                          [('x', OrderedDict(
                              [('1', OrderedDict()),
                               ('2', OrderedDict())])),
                           ('y', OrderedDict())]
                      ))]
                 ))]
            ))]
        )
        m = self.machine_cls()
        self.assertEqual(tree, m._build_state_tree(states, sep))
        self.assertEqual(states, _build_state_list(tree, sep))
