# -*- coding: utf-8 -*-

try:
    from builtins import object
except ImportError:
    pass

import sys
import tempfile
from os.path import getsize
from os import unlink
from functools import partial

from transitions.extensions.nesting import NestedState, HierarchicalMachine
from transitions.extensions import HierarchicalGraphMachine

from unittest import skipIf
from .test_core import TestTransitions, TestCase, TYPE_CHECKING
from .utils import Stuff, DummyModel

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock  # type: ignore

try:
    # Just to skip tests if graphviz not installed
    import graphviz as pgv  # @UnresolvedImport
except ImportError:  # pragma: no cover
    pgv = None


if TYPE_CHECKING:
    from typing import List, Dict, Union, Type


default_separator = NestedState.separator


class Dummy(object):
    pass


test_states = ['A', 'B',
               {'name': 'C', 'children': ['1', '2', {'name': '3', 'children': ['a', 'b', 'c']}]}, 'D', 'E', 'F']


class TestNestedTransitions(TestTransitions):

    def setUp(self):
        self.states = test_states
        self.machine_cls = HierarchicalMachine  # type: Type[HierarchicalMachine]
        self.state_cls = NestedState
        self.stuff = Stuff(self.states, self.machine_cls)

    def test_add_model(self):
        model = Dummy()
        self.stuff.machine.add_model(model, initial='E')

    def test_init_machine_with_hella_arguments(self):
        states = [
            self.state_cls('State1'),
            'State2',
            {
                'name': 'State3',
                'on_enter': 'hello_world'
            }
        ]
        transitions = [
            {'trigger': 'advance',
                'source': 'State2',
                'dest': 'State3'
             }
        ]
        s = Stuff()
        self.stuff.machine_cls(
            model=s, states=states, transitions=transitions, initial='State2')
        s.advance()
        self.assertEqual(s.message, 'Hello World!')

    def test_init_machine_with_nested_states(self):
        State = self.state_cls
        a = State('A')
        b = State('B')
        b_1 = State('1')
        b_2 = State('2')
        b.add_substate(b_1)
        b.add_substates([b_2])
        m = self.stuff.machine_cls(states=[a, b])
        self.assertEqual(m.states['B'].states['1'], b_1)
        m.to("B{0}1".format(State.separator))
        self.assertEqual(m.state, "B{0}1".format(State.separator))

    def test_property_initial(self):
        # Define with list of dictionaries
        states = ['A', 'B', {'name': 'C', 'children': ['1', '2', '3']}, 'D']
        # Define with list of dictionaries
        transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'B'},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'D'}
        ]
        m = self.stuff.machine_cls(states=states, transitions=transitions, initial='A')
        self.assertEqual(m.initial, 'A')
        m = self.stuff.machine_cls(states=states, transitions=transitions, initial='C')
        self.assertEqual(m.initial, 'C')
        m = self.stuff.machine_cls(states=states, transitions=transitions)
        self.assertEqual(m.initial, 'initial')

    def test_transition_definitions(self):
        State = self.state_cls
        states = ['A', 'B', {'name': 'C', 'children': ['1', '2', '3']}, 'D']
        # Define with list of dictionaries
        transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'B'},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'D'},
            {'trigger': 'run', 'source': 'C', 'dest': 'C%s1' % State.separator}
        ]  # type: List[Union[List[str], Dict[str, str]]]
        m = self.stuff.machine_cls(states=states, transitions=transitions, initial='A')
        m.walk()
        self.assertEqual(m.state, 'B')
        m.run()
        self.assertEqual(m.state, 'C')
        m.run()
        self.assertEqual(m.state, 'C%s1' % State.separator)
        # Define with list of lists
        transitions = [
            ['walk', 'A', 'B'],
            ['run', 'B', 'C'],
            ['sprint', 'C', 'D']
        ]
        m = self.stuff.machine_cls(states=states, transitions=transitions, initial='A')
        m.to_C()
        m.sprint()
        self.assertEqual(m.state, 'D')

    def test_nested_definitions(self):
        separator = self.state_cls.separator
        state = {
            'name': 'B',
            'children': ['1', '2'],
            'transitions': [['jo', '1', '2']],
            'initial': '2'
        }
        m = self.stuff.machine_cls(initial='A', states=['A', state],
                                   transitions=[['go', 'A', 'B'], ['go', 'B{0}2'.format(separator),
                                                                   'B{0}1'.format(separator)]])
        self.assertTrue(m.is_A())
        m.go()
        self.assertEqual(m.state, 'B{0}2'.format(separator))
        m.go()
        self.assertEqual(m.state, 'B{0}1'.format(separator))
        m.jo()

    def test_transitioning(self):
        s = self.stuff
        s.machine.add_transition('advance', 'A', 'B')
        s.machine.add_transition('advance', 'B', 'C')
        s.machine.add_transition('advance', 'C', 'D')
        s.machine.add_transition('reset', '*', 'A')
        self.assertEqual(len(s.machine.events['reset'].transitions), 6)
        self.assertEqual(len(s.machine.events['reset'].transitions['C']), 1)
        s.advance()
        self.assertEqual(s.state, 'B')
        self.assertFalse(s.is_A())
        self.assertTrue(s.is_B())
        s.advance()
        self.assertEqual(s.state, 'C')

    def test_conditions(self):
        s = self.stuff
        s.machine.add_transition('advance', 'A', 'B', conditions='this_passes')
        s.machine.add_transition('advance', 'B', 'C', unless=['this_fails'])
        s.machine.add_transition('advance', 'C', 'D', unless=['this_fails',
                                                              'this_passes'])
        s.advance()
        self.assertEqual(s.state, 'B')
        s.advance()
        self.assertEqual(s.state, 'C')
        s.advance()
        self.assertEqual(s.state, 'C')

    def test_multiple_add_transitions_from_state(self):
        State = self.state_cls
        s = self.stuff
        s.machine.add_transition(
            'advance', 'A', 'B', conditions=['this_fails'])
        s.machine.add_transition('advance', 'A', 'C')
        s.machine.add_transition('advance', 'C', 'C%s2' % State.separator)
        s.advance()
        self.assertEqual(s.state, 'C')
        s.advance()
        self.assertEqual(s.state, 'C%s2' % State.separator)
        self.assertFalse(s.is_C())
        self.assertTrue(s.is_C(allow_substates=True))

    def test_use_machine_as_model(self):
        states = ['A', 'B', 'C', 'D']
        m = self.stuff.machine_cls(states=states, initial='A')
        m.add_transition('move', 'A', 'B')
        m.add_transition('move_to_C', 'B', 'C')
        m.move()
        self.assertEqual(m.state, 'B')

    def test_add_custom_state(self):
        State = self.state_cls
        s = self.stuff
        s.machine.add_states([{'name': 'E', 'children': ['1', '2']}])
        s.machine.add_state('E%s3' % State.separator)
        s.machine.add_transition('go', '*', 'E%s1' % State.separator)
        s.machine.add_transition('walk', '*', 'E%s3' % State.separator)
        s.machine.add_transition('run', 'E', 'C{0}3{0}a'.format(State.separator))
        s.go()
        self.assertEqual('E{0}1'.format(State.separator), s.state)
        s.walk()
        self.assertEqual('E{0}3'.format(State.separator), s.state)
        s.run()
        self.assertEqual('C{0}3{0}a'.format(State.separator), s.state)

    def test_add_nested_state(self):
        m = self.machine_cls(states=['A'], initial='A')
        m.add_state('B{0}1{0}a'.format(self.state_cls.separator))
        self.assertIn('B', m.states)
        self.assertIn('1', m.states['B'].states)
        self.assertIn('a', m.states['B'].states['1'].states)

        with self.assertRaises(ValueError):
            m.add_state(m.states['A'])

    def test_enter_exit_nested_state(self):
        State = self.state_cls
        mock = MagicMock()

        def callback():
            mock()
        states = ['A', 'B', {'name': 'C', 'on_enter': callback, 'on_exit': callback,
                             'children': [{'name': '1', 'on_enter': callback, 'on_exit': callback}, '2', '3']},
                            {'name': 'D', 'on_enter': callback, 'on_exit': callback}]
        transitions = [['go', 'A', 'C{0}1'.format(State.separator)],
                       ['go', 'C', 'D']]
        m = self.stuff.machine_cls(states=states, transitions=transitions, initial='A')
        m.go()
        self.assertTrue(mock.called)
        self.assertEqual(2, mock.call_count)
        m.go()
        self.assertTrue(m.is_D())
        self.assertEqual(5, mock.call_count)
        m.to_C()
        self.assertEqual(7, mock.call_count)
        m.to('C{0}1'.format(State.separator))
        self.assertEqual(8, mock.call_count)
        m.to('C{0}2'.format(State.separator))
        self.assertEqual(9, mock.call_count)

    def test_ordered_transitions(self):
        State = self.state_cls
        states = [{'name': 'first', 'children': ['second', 'third', {'name': 'fourth', 'children': ['fifth', 'sixth']},
                                                 'seventh']}, 'eighth', 'ninth']
        m = self.stuff.machine_cls(states=states)
        m.add_ordered_transitions()
        self.assertEqual('initial', m.state)
        m.next_state()
        self.assertEqual('first', m.state)
        m.next_state()
        m.next_state()
        self.assertEqual('first{0}third'.format(State.separator), m.state)
        m.next_state()
        m.next_state()
        self.assertEqual('first{0}fourth{0}fifth'.format(State.separator), m.state)
        m.next_state()
        m.next_state()
        self.assertEqual('first{0}seventh'.format(State.separator), m.state)
        m.next_state()
        m.next_state()
        self.assertEqual('ninth', m.state)

        # Include initial state in loop
        m = self.stuff.machine_cls(states=states)
        m.add_ordered_transitions(loop_includes_initial=False)
        m.to_ninth()
        m.next_state()
        self.assertEqual(m.state, 'first')

        # Test user-determined sequence and trigger name
        m = self.stuff.machine_cls(states=states, initial='first')
        m.add_ordered_transitions(['first', 'ninth'], trigger='advance')
        m.advance()
        self.assertEqual(m.state, 'ninth')
        m.advance()
        self.assertEqual(m.state, 'first')

        # Via init argument
        m = self.stuff.machine_cls(states=states, initial='first', ordered_transitions=True)
        m.next_state()
        self.assertEqual(m.state, 'first{0}second'.format(State.separator))

    def test_pickle(self):
        print("separator", self.state_cls.separator)
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
        m.walk()
        dump = pickle.dumps(m)
        self.assertIsNotNone(dump)
        m2 = pickle.loads(dump)
        self.assertEqual(m.state, m2.state)
        m2.run()
        m2.to_C_3_a()
        m2.to_C_3_b()

    def test_callbacks_duplicate(self):

        transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'C', 'before': 'before_change',
             'after': 'after_change'},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'}
        ]

        m = self.stuff.machine_cls(states=['A', 'B', 'C'], transitions=transitions,
                                   before_state_change='before_change',
                                   after_state_change='after_change', send_event=True,
                                   initial='A', auto_transitions=True)

        m.before_change = MagicMock()
        m.after_change = MagicMock()

        m.walk()
        self.assertEqual(m.before_change.call_count, 2)
        self.assertEqual(m.after_change.call_count, 2)

    def test_example_one(self):
        State = self.state_cls
        State.separator = '_'
        states = ['standing', 'walking', {'name': 'caffeinated', 'children': ['dithering', 'running']}]
        transitions = [['walk', 'standing', 'walking'],
                       ['stop', 'walking', 'standing'],
                       ['drink', 'caffeinated_dithering', '='],
                       ['drink', 'caffeinated', 'caffeinated_dithering'],
                       ['drink', '*', 'caffeinated'],
                       ['walk', 'caffeinated', 'caffeinated_running'],
                       ['relax', 'caffeinated', 'standing']]
        machine = self.stuff.machine_cls(states=states, transitions=transitions, initial='standing',
                                         ignore_invalid_triggers=True, name='Machine 1')

        machine.walk()   # Walking now
        machine.stop()   # let's stop for a moment
        machine.drink()  # coffee time
        machine.state
        self.assertEqual(machine.state, 'caffeinated')
        machine.drink()  # again!
        self.assertEqual(machine.state, 'caffeinated_dithering')
        machine.drink()  # and again!
        self.assertEqual(machine.state, 'caffeinated_dithering')
        machine.walk()   # we have to go faster
        self.assertEqual(machine.state, 'caffeinated_running')
        machine.stop()   # can't stop moving!
        machine.state
        self.assertEqual(machine.state, 'caffeinated_running')
        machine.relax()  # leave nested state
        machine.state    # phew, what a ride
        self.assertEqual(machine.state, 'standing')
        machine.to_caffeinated_running()  # auto transition fast track
        machine.on_enter_caffeinated_running('callback_method')

    def test_multiple_models(self):
        class Model(object):
            pass
        s1, s2 = Model(), Model()
        m = self.stuff.machine_cls(model=[s1, s2], states=['A', 'B', 'C'], initial='A')
        self.assertEqual(len(m.models), 2)
        m.add_transition('advance', 'A', 'B')
        self.assertNotEqual(s1.advance, s2.advance)
        s1.advance()
        self.assertEqual(s1.state, 'B')
        self.assertEqual(s2.state, 'A')

    def test_excessive_nesting(self):
        states = [{'name': 'A', 'children': []}]  # type: List[Dict[str, Union[str, List[Dict]]]]
        curr = states[0]  # type: Dict
        for i in range(10):
            curr['children'].append({'name': str(i), 'children': []})
            curr = curr['children'][0]
        m = self.stuff.machine_cls(states=states, initial='A')

    def test_intial_state(self):
        separator = self.state_cls.separator
        states = [{'name': 'A', 'children': ['1', '2'], 'initial': '2'},
                  {'name': 'B', 'initial': '2',
                   'children': ['1', {'name': '2', 'initial': 'a',
                                      'children': ['a', 'b']}]}]
        transitions = [['do', 'A', 'B'],
                       ['do', 'B{0}2'.format(separator),
                        'B{0}1'.format(separator)]]
        m = self.stuff.machine_cls(states=states, transitions=transitions, initial='A')
        self.assertEqual(m.state, 'A{0}2'.format(separator))
        m.do()
        self.assertEqual(m.state, 'B{0}2{0}a'.format(separator))
        self.assertTrue(m.is_B(allow_substates=True))
        m.do()
        self.assertEqual(m.state, 'B{0}1'.format(separator))
        m = self.stuff.machine_cls(states=states, transitions=transitions, initial='B{0}2{0}b'.format(separator))
        self.assertTrue('B{0}2{0}b'.format(separator), m.state)

    def test_get_triggers(self):
        seperator = self.state_cls.separator
        states = ['standing', 'walking', {'name': 'caffeinated', 'children': ['dithering', 'running']}]
        transitions = [
            ['walk', 'standing', 'walking'],
            ['go', 'standing', 'walking'],
            ['stop', 'walking', 'standing'],
            {'trigger': 'drink', 'source': '*', 'dest': 'caffeinated{0}dithering'.format(seperator),
             'conditions': 'is_hot', 'unless': 'is_too_hot'},
            ['walk', 'caffeinated{0}dithering'.format(seperator), 'caffeinated{0}running'.format(seperator)],
            ['relax', 'caffeinated', 'standing']
        ]

        machine = self.stuff.machine_cls(states=states, transitions=transitions, auto_transitions=False)
        trans = machine.get_triggers('caffeinated{0}dithering'.format(seperator))
        self.assertEqual(len(trans), 3)
        self.assertTrue('relax' in trans)

    def test_get_nested_transitions(self):
        seperator = self.state_cls.separator
        states = ['A', {'name': 'B', 'children': ['1', '2', {'name': '3', 'children': ['a', 'b'],
                                                             'transitions': [['inner', 'a', 'b'],
                                                                             ['inner', 'b', 'a']]}],
                        'transitions': [['mid', '1', '1'],
                                        ['mid', '2', '3'],
                                        ['mid', '3', '1'],
                                        ['mid2', '2', '3'],
                                        ['mid_loop', '1', '1']]}]
        transitions = [['outer', 'A', 'B'],
                       ['outer', ['A', 'B'], 'C']]
        machine = self.stuff.machine_cls(states=states, transitions=transitions, initial='A', auto_transitions=False)
        self.assertEqual(10, len(machine.get_transitions()))
        self.assertEqual(2, len(machine.get_transitions(source='A')))
        self.assertEqual(2, len(machine.get_transitions('inner')))
        self.assertEqual(3, len(machine.get_transitions('mid')))
        self.assertEqual(3, len(machine.get_transitions(dest='B{0}1'.format(seperator))))
        self.assertEqual(2, len(machine.get_transitions(source='B{0}2'.format(seperator),
                                                        dest='B{0}3'.format(seperator))))
        self.assertEqual(1, len(machine.get_transitions(source='B{0}3{0}a'.format(seperator),
                                                        dest='B{0}3{0}b'.format(seperator))))
        self.assertEqual(1, len(machine.get_transitions(source=machine.states['B'].states['3'].states['b'])))
        # should be B_3_b -> B_3_a, B_3 -> B_1 and B -> C
        self.assertEqual(3, len(machine.get_transitions(source=machine.states['B'].states['3'].states['b'],
                                                        delegate=True)))

    def test_internal_transitions(self):
        s = self.stuff
        s.machine.add_transition('internal', 'A', None, prepare='increase_level')
        s.internal()
        self.assertEqual(s.state, 'A')
        self.assertEqual(s.level, 2)

    def test_transition_with_unknown_state(self):
        s = self.stuff
        with self.assertRaises(ValueError):
            s.machine.add_transition('next', 'A', s.machine.state_cls('X'))

    def test_skip_to_override(self):
        mock = MagicMock()

        class Model:

            def to(self):
                mock()

        model1 = Model()
        model2 = DummyModel()
        machine = self.machine_cls([model1, model2], states=['A', 'B'], initial='A')
        model1.to()
        model2.to('B')
        self.assertTrue(mock.called)
        self.assertTrue(model2.is_B())

    def test_trigger_parent(self):
        parent_mock = MagicMock()
        exit_mock = MagicMock()
        enter_mock = MagicMock()

        class Model:

            def on_exit_A(self):
                parent_mock()

            def on_exit_A_1(self):
                exit_mock()

            def on_enter_A_2(self):
                enter_mock()

        model = Model()
        machine = self.machine_cls(model, states=[{'name': 'A', 'children': ['1', '2']}],
                                   transitions=[['go', 'A', 'A_2'], ['enter', 'A', 'A_1']], initial='A')

        model.enter()
        self.assertFalse(parent_mock.called)
        model.go()
        self.assertTrue(exit_mock.called)
        self.assertTrue(enter_mock.called)
        self.assertFalse(parent_mock.called)

    def test_trigger_parent_model_self(self):
        exit_mock = MagicMock()
        enter_mock = MagicMock()

        class CustomMachine(self.machine_cls):  # type: ignore
            def on_enter_A(self):
                raise AssertionError("on_enter_A must not be called!")

            def on_exit_A(self):
                raise AssertionError("on_exit_A must not be called!")

            def on_exit_A_1(self):
                exit_mock()

            def on_enter_A_2(self):
                enter_mock()

        machine = CustomMachine(states=[{'name': 'A', 'children': ['1', '2']}],
                                transitions=[['go', 'A', 'A_2'], ['enter', 'A', 'A_1']], initial='A')
        machine.enter()
        self.assertFalse(exit_mock.called)
        self.assertFalse(enter_mock.called)
        machine.go()
        self.assertTrue(exit_mock.called)
        self.assertTrue(enter_mock.called)
        machine.go()
        self.assertEqual(2, enter_mock.call_count)

    def test_child_condition_persistence(self):
        # even though the transition is invalid for the parent it is valid for the nested child state
        # no invalid transition exception should be thrown
        machine = self.machine_cls(states=[{'name': 'A', 'children': ['1', '2'], 'initial': '1',
                                            'transitions': [{'trigger': 'go', 'source': '1', 'dest': '2',
                                                             'conditions': self.stuff.this_fails}]}, 'B'],
                                   transitions=[['go', 'B', 'A']], initial='A')
        self.assertFalse(False, machine.go())

    def test_exception_in_state_enter_exit(self):
        # https://github.com/pytransitions/transitions/issues/486
        # NestedState._scope needs to be reset when an error is raised in a state callback
        class Model:
            def on_enter_B_1(self):
                raise RuntimeError("Oh no!")

            def on_exit_C_1(self):
                raise RuntimeError("Oh no!")

        states = ['A',
                  {'name': 'B', 'initial': '1', 'children': ['1', '2']},
                  {'name': 'C', 'initial': '1', 'children': ['1', '2']}]
        model = Model()
        machine = self.machine_cls(model, states=states, initial='A')
        with self.assertRaises(RuntimeError):
            model.to_B()
        self.assertTrue(model.is_B_1())
        machine.set_state('A', model)
        with self.assertRaises(RuntimeError):
            model.to_B()
        with self.assertRaises(RuntimeError):
            model.to_C()
            model.to_A()
        self.assertTrue(model.is_C_1())
        machine.set_state('A', model)
        model.to_C()
        self.assertTrue(model.is_C_1())

    def test_correct_subclassing(self):
        from transitions.core import State

        class WrongStateClass(self.machine_cls):  # type: ignore
            state_cls = State

        class MyNestedState(NestedState):
            pass

        class CorrectStateClass(self.machine_cls):  # type: ignore
            state_cls = MyNestedState

        with self.assertRaises(AssertionError):
            m = WrongStateClass()
        m = CorrectStateClass()

    def test_queued_callbacks(self):
        states = [
            "initial",
            {'name': 'A', 'children': [{'name': '1', 'on_enter': 'go'}, '2'],
             'transitions': [['go', '1', '2']], 'initial': '1'}
        ]
        machine = self.machine_cls(states=states, initial='initial', queued=True)
        machine.to_A()
        self.assertEqual("A{0}2".format(self.state_cls.separator), machine.state)

    def test_nested_transitions(self):
        states = [{
            'name': 'A',
            'states': [
                {'name': 'B',
                 'states': [
                     {'name': 'C',
                      'states': ['1', '2'],
                      'initial': '1'}],
                 'transitions': [['go', 'C_1', 'C_2']],
                 'initial': 'C',
                 }],
            'initial': 'B'
        }]
        machine = self.machine_cls(states=states, initial='A')
        machine.go()

    def test_auto_transitions_from_nested_callback(self):

        def fail():
            self.fail("C should not be exited!")

        states = [
            {'name': 'b', 'children': [
                {'name': 'c', 'on_exit': fail, 'on_enter': 'to_b_c_ca', 'children': ['ca', 'cb']},
                'd'
            ]},
        ]
        machine = self.machine_cls(states=states, queued=True, initial='b')
        machine.to_b_c()

    def test_machine_may_transitions_for_generated_triggers(self):
        states = ['A', 'B', {'name': 'C', 'children': ['1', '2', '3']}, 'D']
        m = self.stuff.machine_cls(states=states, initial='A')
        assert m.may_to_A()
        m.to_A()
        assert m.may_to_B()
        m.to_B()
        assert m.may_to_C()
        m.to_C()
        assert m.may_to_C_1()
        m.to_C_1()
        assert m.may_to_D()
        m.to_D()

    def test_get_nested_triggers(self):
        transitions = [
            ['goB', 'A', 'B'],
            ['goC', 'B', 'C'],
            ['goA', '*', 'A'],
            ['goF1', ['C{0}1'.format(self.machine_cls.separator), 'C{0}2'.format(self.machine_cls.separator)], 'F'],
            ['goF2', 'C', 'F']
        ]
        m = self.machine_cls(states=test_states, transitions=transitions, auto_transitions=False, initial='A')
        self.assertEqual(1, len(m.get_nested_triggers(['C', '1'])))
        with m('C'):
            m.add_transition('goC1', '1', '2')
        self.assertEqual(len(transitions) + 1, len(m.get_nested_triggers()))
        self.assertEqual(2, len(m.get_nested_triggers(['C', '1'])))
        self.assertEqual(2, len(m.get_nested_triggers(['C'])))

    def test_stop_transition_evaluation(self):
        states = ['A', {'name': 'B', 'states': ['C', 'D']}]
        transitions = [['next', 'A', 'B_C'], ['next', 'B_C', 'B_D'], ['next', 'B', 'A']]
        mock = MagicMock()

        def process_error(event_data):
            assert isinstance(event_data.error, ValueError)
            mock()

        m = self.machine_cls(states=states, transitions=transitions, initial='A', send_event=True)
        m.on_enter_B_D(partial(self.stuff.this_raises, ValueError()))
        m.next()
        with self.assertRaises(ValueError):
            m.next()
        assert m.is_B_D()
        assert m.to_B_C()
        m.on_exception = [process_error]
        m.next()
        assert mock.called
        assert m.is_B_D()

    def test_nested_queued_remap(self):
        states = ['A', 'done',
                  {'name': 'B', 'remap': {'done': 'done'},
                   'initial': 'initial',
                   'transitions': [['go', 'initial', 'a']],
                   'states': ['done', 'initial', {'name': 'a', 'remap': {'done': 'done'},
                                                  'initial': 'initial',
                                                  'transitions': [['go', 'initial', 'x']],
                                                  'states': ['done', 'initial',
                                                             {'name': 'x',
                                                              'remap': {'done': 'done'},
                                                              'initial': 'initial',
                                                              'states': ['initial', 'done'],
                                                              'transitions': [['done', 'initial', 'done']]}]}]}]
        m = self.machine_cls(states=states, initial='A', queued=True)
        m.on_enter_B('go')
        m.on_enter_B_a('go')
        m.on_enter_B_a_x_initial('done')
        m.to_B()
        assert m.is_done()

    # https://github.com/pytransitions/transitions/issues/568
    def test_wildcard_src_reflexive_dest(self):
        states = ['A', 'B', {'name': 'C', 'children': ['1', '2', '3']}, 'D']
        machine = self.machine_cls(states=states, transitions=[["reflexive", "*", "="]], initial="A")
        self.assertTrue(machine.is_A())
        machine.reflexive()
        self.assertTrue(machine.is_A())
        state_name = 'C{0}2'.format(self.state_cls.separator)
        machine.set_state(state_name)
        self.assertEqual(state_name, machine.state)
        machine.reflexive()
        self.assertEqual(state_name, machine.state)


class TestSeparatorsBase(TestCase):

    separator = default_separator

    def setUp(self):

        class CustomNestedState(NestedState):
            separator = self.separator

        class CustomHierarchicalMachine(HierarchicalMachine):
            state_cls = CustomNestedState

        self.states = test_states
        self.machine_cls = CustomHierarchicalMachine
        self.state_cls = CustomNestedState
        self.stuff = Stuff(self.states, self.machine_cls)

    def test_enter_exit_nested(self):
        separator = self.state_cls.separator
        s = self.stuff
        s.machine.add_transition('advance', 'A', 'C{0}3'.format(separator))
        s.machine.add_transition('reverse', 'C', 'A')
        s.machine.add_transition('lower', ['C{0}1'.format(separator),
                                           'C{0}3'.format(separator)], 'C{0}3{0}a'.format(separator))
        s.machine.add_transition('rise', 'C{0}3'.format(separator), 'C{0}1'.format(separator))
        s.machine.add_transition('fast', 'A', 'C{0}3{0}a'.format(separator))

        for state_name in s.machine.get_nested_state_names():
            state = s.machine.get_state(state_name)
            state.on_enter.append('increase_level')
            state.on_exit.append('decrease_level')

        s.advance()
        self.assertEqual('C{0}3'.format(separator), s.state)
        self.assertEqual(2, s.level)
        self.assertEqual(3, s.transitions)  # exit A; enter C,3
        s.lower()
        self.assertEqual(s.state, 'C{0}3{0}a'.format(separator))
        self.assertEqual(3, s.level)
        self.assertEqual(4, s.transitions)  # enter a
        s.rise()
        self.assertEqual('C%s1' % separator, s.state)
        self.assertEqual(2, s.level)
        self.assertEqual(7, s.transitions)  # exit a, 3; enter 1
        s.reverse()
        self.assertEqual('A', s.state)
        self.assertEqual(1, s.level)
        self.assertEqual(10, s.transitions)  # exit 1, C; enter A
        s.fast()
        self.assertEqual(s.state, 'C{0}3{0}a'.format(separator))
        self.assertEqual(s.level, 3)
        self.assertEqual(s.transitions, 14)  # exit A; enter C, 3, a
        s.to_A()
        self.assertEqual(s.state, 'A')
        self.assertEqual(s.level, 1)
        self.assertEqual(s.transitions, 18)  # exit a, 3, C; enter A
        s.to_A()
        self.assertEqual(s.state, 'A')
        self.assertEqual(s.level, 1)
        self.assertEqual(s.transitions, 20)  # exit A; enter A
        if separator == '_':
            s.to_C_3_a()
        else:
            print("separator", separator)
            s.to_C.s3.a()
        self.assertEqual(s.state, 'C{0}3{0}a'.format(separator))
        self.assertEqual(s.level, 3)
        self.assertEqual(s.transitions, 24)  # exit A; enter C, 3, a

    def test_state_change_listeners(self):
        State = self.state_cls
        s = self.stuff
        s.machine.add_transition('advance', 'A', 'C%s1' % State.separator)
        s.machine.add_transition('reverse', 'C', 'A')
        s.machine.add_transition('lower', 'C%s1' % State.separator, 'C{0}3{0}a'.format(State.separator))
        s.machine.add_transition('rise', 'C%s3' % State.separator, 'C%s1' % State.separator)
        s.machine.add_transition('fast', 'A', 'C{0}3{0}a'.format(State.separator))
        s.machine.on_enter_C('hello_world')
        s.machine.on_exit_C('goodbye')
        s.machine.on_enter('C{0}3{0}a'.format(State.separator), 'greet')
        s.machine.on_exit('C%s3' % State.separator, 'meet')
        s.advance()
        self.assertEqual(s.state, 'C%s1' % State.separator)
        self.assertEqual(s.message, 'Hello World!')
        s.lower()
        self.assertEqual(s.state, 'C{0}3{0}a'.format(State.separator))
        self.assertEqual(s.message, 'Hi')
        s.rise()
        self.assertEqual(s.state, 'C%s1' % State.separator)
        self.assertTrue(s.message is not None and s.message.startswith('Nice to'))
        s.reverse()
        self.assertEqual(s.state, 'A')
        self.assertTrue(s.message is not None and s.message.startswith('So long'))
        s.fast()
        self.assertEqual(s.state, 'C{0}3{0}a'.format(State.separator))
        self.assertEqual(s.message, 'Hi')
        s.to_A()
        self.assertEqual(s.state, 'A')
        self.assertTrue(s.message is not None and s.message.startswith('So long'))

    def test_nested_auto_transitions(self):
        State = self.state_cls
        s = self.stuff
        s.to_C()
        self.assertEqual(s.state, 'C')
        state = 'C{0}3{0}a'.format(State.separator)
        s.to(state)
        self.assertEqual(s.state, state)
        # backwards compatibility check (can be removed in 0.7)
        self.assertEqual(s.state, state)
        for state_name in s.machine.get_nested_state_names():
            event_name = 'to_{0}'.format(state_name)
            num_base_states = len(s.machine.states)
            self.assertTrue(event_name in s.machine.events)
            self.assertEqual(len(s.machine.events[event_name].transitions), num_base_states)

    @skipIf(pgv is None, 'NestedGraph diagram test requires graphviz')
    def test_ordered_with_graph(self):
        class CustomHierarchicalGraphMachine(HierarchicalGraphMachine):
            state_cls = self.state_cls

        states = ['A', 'B', {'name': 'C', 'children': ['1', '2',
                                                       {'name': '3', 'children': ['a', 'b', 'c']}]}, 'D', 'E', 'F']
        machine = CustomHierarchicalGraphMachine(states=states, initial='A', auto_transitions=False,
                                                 ignore_invalid_triggers=True, use_pygraphviz=False)
        machine.add_ordered_transitions(trigger='next_state')
        machine.next_state()
        self.assertEqual(machine.state, 'B')
        target = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        machine.get_graph().draw(target.name, prog='dot')
        self.assertTrue(getsize(target.name) > 0)
        target.close()
        unlink(target.name)

    def test_example_two(self):
        separator = self.state_cls.separator
        states = ['A', 'B',
                  {'name': 'C', 'children': ['1', '2',
                                             {'name': '3', 'children': ['a', 'b', 'c']}]
                   }]

        transitions = [
            ['reset', 'C', 'A'],
            ['reset', 'C%s2' % separator, 'C']  # overwriting parent reset
        ]

        # we rely on auto transitions
        machine = self.stuff.machine_cls(states=states, transitions=transitions, initial='A')

        machine.to_B()  # exit state A, enter state B
        machine.to_C()  # exit B, enter C
        if separator == '_':
            machine.to_C_3_a()
            self.assertTrue(machine.is_C(allow_substates=True))
            self.assertFalse(machine.is_C())
            self.assertTrue(machine.is_C_3(allow_substates=True))
            self.assertFalse(machine.is_C_3())
            self.assertTrue(machine.is_C_3_a())
        else:
            machine.to_C.s3.a()  # enter C↦a; enter C↦3↦a;
            self.assertTrue(machine.is_C(allow_substates=True))
            self.assertFalse(machine.is_C())
            self.assertTrue(machine.is_C.s3(allow_substates=True))
            self.assertFalse(machine.is_C.s3())
            self.assertTrue(machine.is_C.s3.a())
        self.assertEqual(machine.state, 'C{0}3{0}a'.format(separator))
        machine.to('C{0}2'.format(separator))  # exit C↦3↦a, exit C↦3, enter C↦2
        self.assertEqual(machine.state, 'C{0}2'.format(separator))
        machine.reset()  # exit C↦2; reset C has been overwritten by C↦3
        self.assertEqual('C', machine.state)
        machine.reset()  # exit C, enter A
        self.assertEqual('A', machine.state)

    def test_machine_may_transitions(self):
        states = ['A', 'B', {'name': 'C', 'children': ['1', '2', '3']}, 'D']
        transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'B'},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'},
            {'trigger': 'run_fast', 'source': 'C', 'dest': 'C{0}1'.format(self.separator)},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'D'}
        ]
        m = self.stuff.machine_cls(
            states=states, transitions=transitions, initial='A', auto_transitions=False
        )
        assert m.may_walk()
        assert not m.may_run()
        assert not m.may_run_fast()
        assert not m.may_sprint()

        m.walk()
        assert not m.may_walk()
        assert m.may_run()
        assert not m.may_run_fast()

        m.run()
        assert m.may_run_fast()
        assert m.may_sprint()
        m.run_fast()


class TestSeparatorsSlash(TestSeparatorsBase):
    separator = '/'


class TestSeparatorsDot(TestSeparatorsBase):
    separator = '.'


@skipIf(sys.version_info[0] < 3, "Unicode separators are only supported for Python 3")
class TestSeparatorUnicode(TestSeparatorsBase):
    separator = u'↦'
