try:
    from builtins import object
except ImportError:
    pass

from transitions import MachineError
from transitions.extensions import MachineFactory
from transitions.extensions.nesting import NestedState, HierarchicalMachine

from .utils import Stuff
from .test_core import TYPE_CHECKING

from unittest import TestCase

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock  # type: ignore


if TYPE_CHECKING:
    from typing import List, Union, Dict, Any


test_states = ['A', 'B', {'name': 'C', 'children': ['1', '2', {'name': '3', 'children': ['a', 'b', 'c']}]},
               'D', 'E', 'F']


class TestReuseSeparatorBase(TestCase):
    separator = '_'

    def setUp(self):

        class CustomState(NestedState):
            separator = self.separator

        class CustomMachine(HierarchicalMachine):
            state_cls = CustomState

        self.states = test_states
        self.machine_cls = CustomMachine
        self.state_cls = self.machine_cls.state_cls
        self.stuff = Stuff(self.states, self.machine_cls)

    def test_wrong_nesting(self):
        correct = ['A', {'name': 'B', 'children': self.stuff.machine}]
        wrong_type = ['A', {'name': 'B', 'children': self.stuff}]
        siblings = ['A', {'name': 'B', 'children': ['1', self.stuff.machine]}]
        collision = ['A', {'name': 'B', 'children': ['A', self.stuff.machine]}]

        m = self.machine_cls(states=correct)
        if m.state_cls.separator != '_':
            m.to_B.C.s3.a()
        else:
            m.to_B_C_3_a()

        with self.assertRaises(ValueError):
            m = self.machine_cls(states=wrong_type)

        with self.assertRaises(ValueError):
            m = self.machine_cls(states=collision)

        m = self.machine_cls(states=siblings)
        if m.state_cls.separator != '_':
            m.to_B.s1()
            m.to_B.A()
        else:
            m.to_B_1()
            m.to_B_A()


class TestReuseSeparatorDot(TestReuseSeparatorBase):
    separator = '.'


class TestReuse(TestCase):

    def setUp(self):
        self.states = test_states
        self.machine_cls = HierarchicalMachine
        self.state_cls = self.machine_cls.state_cls
        self.stuff = Stuff(self.states, self.machine_cls)

    def test_blueprint_reuse(self):
        State = self.state_cls
        states = ['1', '2', '3']
        transitions = [
            {'trigger': 'increase', 'source': '1', 'dest': '2'},
            {'trigger': 'increase', 'source': '2', 'dest': '3'},
            {'trigger': 'decrease', 'source': '3', 'dest': '2'},
            {'trigger': 'decrease', 'source': '1', 'dest': '1'},
            {'trigger': 'reset', 'source': '*', 'dest': '1'},
        ]

        counter = self.machine_cls(states=states, transitions=transitions, before_state_change='check',
                                   after_state_change='clear', initial='1')

        new_states = ['A', 'B', {'name': 'C', 'children': counter}]
        new_transitions = [
            {'trigger': 'forward', 'source': 'A', 'dest': 'B'},
            {'trigger': 'forward', 'source': 'B', 'dest': 'C%s1' % State.separator},
            {'trigger': 'backward', 'source': 'C', 'dest': 'B'},
            {'trigger': 'backward', 'source': 'B', 'dest': 'A'},
            {'trigger': 'calc', 'source': '*', 'dest': 'C'},
        ]

        walker = self.machine_cls(states=new_states, transitions=new_transitions, before_state_change='watch',
                                  after_state_change='look_back', initial='A')

        walker.watch = lambda: 'walk'
        walker.look_back = lambda: 'look_back'
        walker.check = lambda: 'check'
        walker.clear = lambda: 'clear'

        with self.assertRaises(MachineError):
            walker.increase()
        self.assertEqual(walker.state, 'A')
        walker.forward()
        walker.forward()
        self.assertEqual(walker.state, 'C%s1' % State.separator)
        walker.increase()
        self.assertEqual(walker.state, 'C%s2' % State.separator)
        walker.reset()
        self.assertEqual(walker.state, 'C%s1' % State.separator)
        walker.to_A()
        self.assertEqual(walker.state, 'A')
        walker.calc()
        self.assertEqual(walker.state, 'C{0}1'.format(State.separator))

    def test_blueprint_initial_false(self):
        child = self.machine_cls(states=['A', 'B'], initial='A')
        parent = self.machine_cls(states=['a', 'b', {'name': 'c', 'children': child, 'initial': False}])
        parent.to_c()
        self.assertEqual(parent.state, 'c')

    def test_blueprint_remap(self):
        State = self.state_cls
        states = ['1', '2', '3', 'finished']
        transitions = [
            {'trigger': 'increase', 'source': '1', 'dest': '2'},
            {'trigger': 'increase', 'source': '2', 'dest': '3'},
            {'trigger': 'decrease', 'source': '3', 'dest': '2'},
            {'trigger': 'decrease', 'source': '1', 'dest': '1'},
            {'trigger': 'reset', 'source': '*', 'dest': '1'},
            {'trigger': 'done', 'source': '3', 'dest': 'finished'}
        ]

        counter = self.machine_cls(states=states, transitions=transitions, initial='1')

        new_states = ['A', 'B', {'name': 'C', 'children':
                      [counter, {'name': 'X', 'children': ['will', 'be', 'filtered', 'out']}],
                      'remap': {'finished': 'A', 'X': 'A'}}] \
            # type: List[Union[str, Dict[str, Union[str, Dict, List]]]]
        new_transitions = [
            {'trigger': 'forward', 'source': 'A', 'dest': 'B'},
            {'trigger': 'forward', 'source': 'B', 'dest': 'C%s1' % State.separator},
            {'trigger': 'backward', 'source': 'C', 'dest': 'B'},
            {'trigger': 'backward', 'source': 'B', 'dest': 'A'},
            {'trigger': 'calc', 'source': '*', 'dest': 'C%s1' % State.separator},
        ]

        walker = self.machine_cls(states=new_states, transitions=new_transitions, before_state_change='watch',
                                  after_state_change='look_back', initial='A')

        walker.watch = lambda: 'walk'
        walker.look_back = lambda: 'look_back'

        counter.increase()
        counter.increase()
        counter.done()
        self.assertEqual(counter.state, 'finished')

        with self.assertRaises(MachineError):
            walker.increase()
        self.assertEqual(walker.state, 'A')
        walker.forward()
        walker.forward()
        self.assertEqual(walker.state, 'C%s1' % State.separator)
        walker.increase()
        self.assertEqual(walker.state, 'C%s2' % State.separator)
        walker.reset()
        self.assertEqual(walker.state, 'C%s1' % State.separator)
        walker.to_A()
        self.assertEqual(walker.state, 'A')
        walker.calc()
        self.assertEqual(walker.state, 'C%s1' % State.separator)
        walker.increase()
        walker.increase()
        walker.done()
        self.assertEqual(walker.state, 'A')
        self.assertFalse('C.finished' in walker.states)

    def test_example_reuse(self):
        State = self.state_cls
        count_states = ['1', '2', '3', 'done']
        count_trans = [
            ['increase', '1', '2'],
            ['increase', '2', '3'],
            ['decrease', '3', '2'],
            ['decrease', '2', '1'],
            {'trigger': 'done', 'source': '3', 'dest': 'done', 'conditions': 'this_passes'},
        ]

        counter = self.machine_cls(states=count_states, transitions=count_trans, initial='1')
        counter.increase()  # love my counter
        states = ['waiting', 'collecting', {'name': 'counting', 'children': counter}]
        states_remap = ['waiting', 'collecting', {'name': 'counting', 'children': counter, 'remap': {'done': 'waiting'}}] \
            # type: List[Union[str, Dict[str, Union[str, HierarchicalMachine, Dict]]]]

        transitions = [
            ['collect', '*', 'collecting'],
            ['wait', '*', 'waiting'],
            ['count', '*', 'counting%s1' % State.separator]
        ]

        collector = self.stuff.machine_cls(states=states, transitions=transitions, initial='waiting')
        collector.this_passes = self.stuff.this_passes
        collector.collect()  # collecting
        collector.count()  # let's see what we got
        collector.increase()  # counting_2
        collector.increase()  # counting_3
        collector.done()  # counting_done
        self.assertEqual(collector.state, 'counting{0}done'.format(State.separator))
        collector.wait()  # go back to waiting
        self.assertEqual(collector.state, 'waiting')

        # reuse counter instance with remap
        collector = self.machine_cls(states=states_remap, transitions=transitions, initial='waiting')
        collector.this_passes = self.stuff.this_passes
        collector.collect()  # collecting
        collector.count()  # let's see what we got
        collector.increase()  # counting_2
        collector.increase()  # counting_3
        collector.done()  # counting_done
        with self.assertRaises(AttributeError):
            collector.is_counting_done()
        self.assertEqual(collector.state, 'waiting')

        # # same as above but with states and therefore stateless embedding
        states_remap[2]['children'] = count_states  # type: ignore
        transitions.append(['increase', 'counting%s1' % State.separator, 'counting%s2' % State.separator])
        transitions.append(['increase', 'counting%s2' % State.separator, 'counting%s3' % State.separator])
        transitions.append(['done', 'counting%s3' % State.separator, 'waiting'])

        collector = self.machine_cls(states=states_remap, transitions=transitions, initial='waiting')
        collector.collect()  # collecting
        collector.count()  # let's see what we got
        collector.increase()  # counting_2
        collector.increase()  # counting_3
        collector.done()  # counting_done
        self.assertEqual(collector.state, 'waiting')

        # check if counting_done was correctly omitted
        collector.add_transition('fail', '*', 'counting%sdone' % State.separator)
        with self.assertRaises(ValueError):
            collector.fail()

    def test_reuse_add_state(self):
        State = self.state_cls
        count_states = ['1', '2', '3', 'done']
        count_trans = [
            ['increase', '1', '2'],
            ['increase', '2', '3'],
            ['decrease', '3', '2'],
            ['decrease', '2', '1'],
            {'trigger': 'done', 'source': '3', 'dest': 'done', 'conditions': 'this_passes'},
        ]

        counter = self.machine_cls(states=count_states, transitions=count_trans, initial='1')
        counter.increase()  # love my counter
        states_remap = ['waiting', 'collecting'] \
            # type: List[Union[str, Dict[str, Union[str, HierarchicalMachine, Dict]]]]
        additional_state = {'name': 'counting', 'children': counter, 'remap': {'done': 'waiting'}}
        transitions = [
            ['collect', '*', 'collecting'],
            ['wait', '*', 'waiting'],
            ['count', '*', 'counting%s1' % State.separator]
        ]

        # reuse counter instance with remap
        collector = self.machine_cls(states=states_remap, transitions=transitions, initial='waiting')
        collector.add_state(additional_state)
        collector.this_passes = self.stuff.this_passes
        collector.collect()  # collecting
        collector.count()  # let's see what we got
        collector.increase()  # counting_2
        collector.increase()  # counting_3
        collector.done()  # counting_done
        self.assertEqual(collector.state, 'waiting')

        # check if counting_done was correctly omitted
        collector.add_transition('fail', '*', 'counting%sdone' % State.separator)
        with self.assertRaises(ValueError):
            collector.fail()

        # same as above but with states and therefore stateless embedding
        additional_state['children'] = count_states
        transitions.append(['increase', 'counting%s1' % State.separator, 'counting%s2' % State.separator])
        transitions.append(['increase', 'counting%s2' % State.separator, 'counting%s3' % State.separator])
        transitions.append(['done', 'counting%s3' % State.separator, 'waiting'])

        collector = self.machine_cls(states=states_remap, transitions=transitions, initial='waiting')
        collector.add_state(additional_state)
        collector.collect()  # collecting
        collector.count()  # let's see what we got
        collector.increase()  # counting_2
        collector.increase()  # counting_3
        collector.done()  # counting_done
        self.assertEqual(collector.state, 'waiting')

        # check if counting_done was correctly omitted
        collector.add_transition('fail', '*', 'counting%sdone' % State.separator)
        with self.assertRaises(ValueError):
            collector.fail()

    def test_reuse_model_decoration(self):
        State = self.state_cls
        count_states = ['1', '2', '3', 'done']
        count_trans = [
            ['increase', '1', '2'],
            ['increase', '2', '3'],
            ['decrease', '3', '2'],
            ['decrease', '2', '1'],
            {'trigger': 'done', 'source': '3', 'dest': 'done', 'conditions': 'this_passes'},
        ]

        counter = self.machine_cls(states=count_states, transitions=count_trans, initial='1')
        states_remap = ['waiting', 'collecting'] \
            # type: List[Union[str, Dict[str, Union[str, HierarchicalMachine, Dict]]]]
        additional_state = {'name': 'counting', 'children': counter, 'remap': {'done': 'waiting'}}
        transitions = [
            ['collect', '*', 'collecting'],
            ['wait', '*', 'waiting'],
            ['count', '*', 'counting%s1' % State.separator]
        ]

        # reuse counter instance with remap
        collector = self.machine_cls(states=states_remap + [additional_state],
                                     transitions=transitions, initial='waiting')

        assert hasattr(collector, "is_waiting")
        assert hasattr(collector, "is_counting")
        assert hasattr(collector, "is_counting_1")
        assert not hasattr(collector, "is_1")
        assert not hasattr(collector, "is_done")
        assert not hasattr(collector, "is_counting_done")

    def test_reuse_model_decoration_add_state(self):
        State = self.state_cls
        count_states = ['1', '2', '3', 'done']
        count_trans = [
            ['increase', '1', '2'],
            ['increase', '2', '3'],
            ['decrease', '3', '2'],
            ['decrease', '2', '1'],
            {'trigger': 'done', 'source': '3', 'dest': 'done', 'conditions': 'this_passes'},
        ]

        counter = self.machine_cls(states=count_states, transitions=count_trans, initial='1')
        states_remap = ['waiting', 'collecting'] \
            # type: List[Union[str, Dict[str, Union[str, HierarchicalMachine, Dict]]]]
        additional_state = {'name': 'counting', 'children': counter, 'remap': {'done': 'waiting'}}
        transitions = [
            ['collect', '*', 'collecting'],
            ['wait', '*', 'waiting'],
            ['count', '*', 'counting%s1' % State.separator]
        ]

        # reuse counter instance with remap
        collector = self.machine_cls(states=states_remap,
                                     transitions=transitions, initial='waiting')
        collector.add_states(additional_state)

        assert hasattr(collector, "is_waiting")
        assert hasattr(collector, "is_counting")
        assert hasattr(collector, "is_counting_1")
        assert not hasattr(collector, "is_1")
        assert not hasattr(collector, "is_done")
        assert not hasattr(collector, "is_counting_done")

    def test_reuse_self_reference(self):
        separator = self.state_cls.separator

        class Nested(self.machine_cls):  # type: ignore

            def __init__(self, parent):
                self.parent = parent
                self.mock = MagicMock()
                states = ['1', '2']
                transitions = [{'trigger': 'finish', 'source': '*', 'dest': '2', 'after': self.print_msg}]
                super(Nested, self).__init__(states=states, transitions=transitions, initial='1')

            def print_msg(self):
                self.mock()
                self.parent.print_top()

        class Top(self.machine_cls):  # type: ignore

            def print_msg(self):
                self.mock()

            def __init__(self):
                self.nested = Nested(self)
                self.mock = MagicMock()

                states = ['A', {'name': 'B', 'children': self.nested}]
                transitions = [dict(trigger='print_top', source='*', dest='=', after=self.print_msg),
                               dict(trigger='to_nested', source='*', dest='B{0}1'.format(separator))]

                super(Top, self).__init__(states=states, transitions=transitions, initial='A')

        top_machine = Top()
        self.assertEqual(top_machine, top_machine.nested.parent)

        top_machine.to_nested()
        top_machine.finish()
        self.assertTrue(top_machine.mock.called)
        self.assertTrue(top_machine.nested.mock.called)
        self.assertIs(top_machine.nested.get_state('2').on_enter,
                      top_machine.get_state('B{0}2'.format(separator)).on_enter)

    def test_reuse_machine_config(self):
        simple_config = {
            "name": "Child",
            "states": ["1", "2"],
            "transitions": [['go', '1', '2']],
            "initial": "1"
        }  # type: Dict[str, Any]
        simple_cls = MachineFactory.get_predefined()
        simple = simple_cls(**simple_config)
        self.assertTrue(simple.is_1())
        self.assertTrue(simple.go())
        self.assertTrue(simple.is_2())
        machine = self.machine_cls(states=['A', simple_config], initial='A')
        machine.to_Child()
        machine.go()
        self.assertTrue(machine.is_Child_2())

    def test_reuse_wrong_class(self):
        m1 = MachineFactory.get_predefined()(states=['A', 'B'], initial='A')
        with self.assertRaises(ValueError):
            m2 = MachineFactory.get_predefined(nested=True)(states=['X', {'name': 'Y', 'states': m1}], initial='Y')

    def test_reuse_remap(self):

        class GenericMachine(self.machine_cls):  # type: ignore

            def __init__(self, states, transitions, model=None):
                generic_states = [
                    {"name": "initial", "on_enter": self.entry_initial},
                    {"name": "done", "on_enter": self.entry_done},
                ]
                states += generic_states

                super(GenericMachine, self).__init__(
                    states=states,
                    transitions=transitions,
                    model=model,
                    send_event=True,
                    queued=True,
                    auto_transitions=False
                )

            def entry_initial(self, event_data):
                raise NotImplementedError

            def entry_done(self, event_data):
                raise NotImplementedError

        class DeeperMachine(GenericMachine):
            def __init__(self):
                states = [
                    {"name": "working", "on_enter": self.entry_working},
                ]
                transitions = [
                    ["go", "initial", "working"],
                    ["go", "working", "done"],
                ]
                super(DeeperMachine, self).__init__(states, transitions, model=self)

            def entry_initial(self, event_data):
                event_data.model.go()

            def entry_working(self, event_data):
                event_data.model.go()

        class NestedMachine(GenericMachine):
            def __init__(self):
                states = [
                    {"name": "deeper", "children": DeeperMachine(), "remap": {"done": "done"}},
                ]
                transitions = [
                    ["go", "initial", "deeper"],
                ]
                super(NestedMachine, self).__init__(states, transitions)

            def entry_initial(self, event_data):
                event_data.model.go()

        class MainMachine(GenericMachine):
            def __init__(self):
                states = [
                    {"name": "nested", "children": NestedMachine(), "remap": {"done": "done"}},
                ]
                transitions = [
                    ["go", "initial", "nested"],
                ]
                super(MainMachine, self).__init__(states, transitions, model=self)

            def entry_done(self, event_data):
                print("job finished")

        machine = MainMachine()
        machine.go()
        assert machine.is_done()

    def test_reuse_callback_copy(self):

        selfs = []

        class Model(object):

            def check_self(self):
                selfs.append(self)
                return True

        m = Model()

        transitions = [
            {"trigger": "go", "source": "A", "dest": "B",
             "conditions": m.check_self, "prepare": m.check_self, "before": m.check_self, "after": m.check_self}
        ]

        child = self.machine_cls(None, states=["A", "B"], transitions=transitions, initial="A")
        parent = self.machine_cls(m, states=[{"name": "P", "states": child, "remap": {}}], initial="P")
        m.go()
        self.assertEqual("P_B", m.state)
        # selfs should only contain references to the same model. If the set is larger than one this means
        # that at some poin the model was falsely copied.
        self.assertEqual(1, len(set(selfs)))
