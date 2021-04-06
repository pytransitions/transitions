from .test_nesting import TestNestedTransitions, TestSeparatorsBase, Stuff, default_separator, test_states
from .test_reuse import TestReuse as TestReuse, TestReuseSeparatorBase
from .test_reuse import test_states as reuse_states
from .test_enum import TestNestedStateEnums
from transitions.extensions.nesting_legacy import HierarchicalMachine, NestedState

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock


class TestNestedLegacySeparatorDefault(TestSeparatorsBase):

    def setUp(self):

        class CustomLegacyState(NestedState):
            separator = self.separator

        class CustomLegacyMachine(HierarchicalMachine):
            state_cls = CustomLegacyState

        self.states = test_states
        self.state_cls = CustomLegacyState
        self.machine_cls = CustomLegacyMachine
        self.stuff = Stuff(self.states, self.machine_cls)
        self.state_cls = self.machine_cls.state_cls

    def test_ordered_with_graph(self):
        pass

    def test_example_two(self):
        pass  # not supported by legacy machine


class TestNestedLegacySeparatorDot(TestNestedLegacySeparatorDefault):
    separator = '.'


class TestNestedLegacySeparatorSlash(TestNestedLegacySeparatorDefault):
    separator = '/'


class TestNestedLegacy(TestNestedTransitions):

    def setUp(self):
        super(TestNestedLegacy, self).setUp()
        self.machine_cls = HierarchicalMachine
        self.stuff = Stuff(self.states, self.machine_cls)
        self.state_cls = self.machine_cls.state_cls

    def test_add_custom_state(self):
        s = self.stuff
        s.machine.add_states([{'name': 'E', 'children': ['1', '2']}])
        s.machine.add_state('3', parent='E')
        s.machine.add_transition('go', '*', 'E%s1' % self.state_cls.separator)
        s.machine.add_transition('walk', '*', 'E%s3' % self.state_cls.separator)
        s.machine.add_transition('run', 'E', 'C{0}3{0}a'.format(self.state_cls.separator))
        s.go()
        self.assertEqual('E{0}1'.format(self.state_cls.separator), s.state)
        s.walk()
        self.assertEqual('E{0}3'.format(self.state_cls.separator), s.state)
        s.run()
        self.assertEqual('C{0}3{0}a'.format(self.state_cls.separator), s.state)

    def test_init_machine_with_nested_states(self):
        State = self.state_cls
        a = State('A')
        b = State('B')
        b_1 = State('1', parent=b)
        b_2 = State('2', parent=b)
        m = self.stuff.machine_cls(states=[a, b])
        self.assertEqual(b_1.name, 'B{0}1'.format(State.separator))
        m.to("B{0}1".format(State.separator))

    def test_transitioning(self):
        State = self.state_cls
        s = self.stuff
        s.machine.add_transition('advance', 'A', 'B')
        s.machine.add_transition('advance', 'B', 'C')
        s.machine.add_transition('advance', 'C', 'D')
        s.machine.add_transition('reset', '*', 'A')
        self.assertEqual(len(s.machine.events['reset'].transitions['C%s1' % State.separator]), 1)
        s.advance()
        self.assertEqual(s.state, 'B')
        self.assertFalse(s.is_A())
        self.assertTrue(s.is_B())
        s.advance()
        self.assertEqual(s.state, 'C')

    def test_nested_definitions(self):
        pass  # not supported by legacy machine

    def test_add_nested_state(self):
        pass  # not supported by legacy machine

    def test_child_condition_persistence(self):
        pass  # not supported by legacy machine

    def test_get_nested_transitions(self):
        pass  # not supported by legacy machine

    def test_correct_subclassing(self):
        pass  # not supported by legacy machine


class TestReuseLegacySeparatorDefault(TestReuseSeparatorBase):

    def setUp(self):

        class CustomLegacyState(NestedState):
            separator = self.separator

        class CustomLegacyMachine(HierarchicalMachine):
            state_cls = CustomLegacyState

        self.states = reuse_states
        self.state_cls = CustomLegacyState
        self.machine_cls = CustomLegacyMachine
        self.stuff = Stuff(self.states, self.machine_cls)
        self.state_cls = self.machine_cls.state_cls


class TestReuseLegacySeparatorDefault(TestReuseLegacySeparatorDefault):
    separator = '.'


class TestReuseLegacy(TestReuse):

    def setUp(self):
        super(TestReuseLegacy, self).setUp()
        self.machine_cls = HierarchicalMachine
        self.stuff = Stuff(self.states, self.machine_cls)
        self.state_cls = self.machine_cls.state_cls

    def test_reuse_self_reference(self):
        separator = self.state_cls.separator

        class Nested(self.machine_cls):

            def __init__(self, parent):
                self.parent = parent
                self.mock = MagicMock()
                states = ['1', '2']
                transitions = [{'trigger': 'finish', 'source': '*', 'dest': '2', 'after': self.print_msg}]
                super(Nested, self).__init__(states=states, transitions=transitions, initial='1')

            def print_msg(self):
                self.mock()
                self.parent.print_top()

        class Top(self.machine_cls):

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
        self.assertIsNot(top_machine.nested.get_state('2').on_enter,
                         top_machine.get_state('B{0}2'.format(separator)).on_enter)

    def test_reuse_machine_config(self):
        pass  # not supported


class TestLegacyNestedEnum(TestNestedStateEnums):

    def setUp(self):
        super(TestLegacyNestedEnum, self).setUp()
        self.machine_cls = HierarchicalMachine
        self.machine_cls.state_cls.separator = default_separator

    def test_nested_enums(self):
        # Nested enums are currently not support since model.state does not contain any information about parents
        # and nesting
        states = ['A', 'B',
                  {'name': 'C', 'children': self.States, 'initial': self.States.GREEN}]
        with self.assertRaises(AttributeError):
            # NestedState will raise an error when parent is not None and state name is an enum
            # Initializing this would actually work but `m.to_A()` would raise an error in get_state(m.state)
            # as Machine is not aware of the location of States.GREEN
            m = self.machine_cls(states=states, initial='C')

    def test_add_enum_transition(self):
        pass  # not supported by legacy machine

    def test_add_nested_enums_as_nested_state(self):
        pass  # not supported by legacy machine

    def test_enum_initial(self):
        pass  # not supported by legacy machine

    def test_separator_naming_error(self):
        pass  # not supported by legacy machine

    def test_get_nested_transitions(self):
        pass  # not supported by legacy machine

    def test_multiple_deeper(self):
        pass  # not supported by legacy machine
