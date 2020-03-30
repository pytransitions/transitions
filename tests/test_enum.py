from unittest import TestCase, skipIf

try:
    import enum
except ImportError:
    enum = None

from transitions.extensions import MachineFactory


@skipIf(enum is None, "enum is not available")
class TestEnumsAsStates(TestCase):

    def setUp(self):
        class States(enum.Enum):
            RED = 1
            YELLOW = 2
            GREEN = 3
        self.machine_cls = MachineFactory.get_predefined()
        self.States = States

    def test_pass_enums_as_states(self):
        m = self.machine_cls(states=self.States, initial=self.States.YELLOW)

        assert m.state == self.States.YELLOW
        assert m.is_RED() is False
        assert m.is_YELLOW() is True
        assert m.is_RED() is False

        m.to_RED()

        assert m.state == self.States.RED
        assert m.is_RED() is True
        assert m.is_YELLOW() is False
        assert m.is_GREEN() is False

    def test_transitions(self):
        m = self.machine_cls(states=self.States, initial=self.States.RED)
        m.add_transition('switch_to_yellow', self.States.RED, self.States.YELLOW)
        m.add_transition('switch_to_green', 'YELLOW', 'GREEN')

        m.switch_to_yellow()
        assert m.is_YELLOW() is True

        m.switch_to_green()
        assert m.is_YELLOW() is False
        assert m.is_GREEN() is True

    def test_if_enum_has_string_behavior(self):
        class States(str, enum.Enum):
            __metaclass__ = enum.EnumMeta

            RED = 'red'
            YELLOW = 'yellow'

        m = self.machine_cls(states=States, auto_transitions=False, initial=States.RED)
        m.add_transition('switch_to_yellow', States.RED, States.YELLOW)

        m.switch_to_yellow()
        assert m.is_YELLOW() is True

    def test_property_initial(self):
        transitions = [
            {'trigger': 'switch_to_yellow', 'source': self.States.RED, 'dest': self.States.YELLOW},
            {'trigger': 'switch_to_green', 'source': 'YELLOW', 'dest': 'GREEN'},
        ]

        m = self.machine_cls(states=self.States, initial=self.States.RED, transitions=transitions)
        m.switch_to_yellow()
        assert m.is_YELLOW()

        m.switch_to_green()
        assert m.is_GREEN()

    def test_pass_state_instances_instead_of_names(self):
        state_A = self.machine_cls.state_cls(self.States.YELLOW)
        state_B = self.machine_cls.state_cls(self.States.GREEN)

        states = [state_A, state_B]

        m = self.machine_cls(states=states, initial=state_A)
        assert m.state == self.States.YELLOW

        m.add_transition('advance', state_A, state_B)
        m.advance()
        assert m.state == self.States.GREEN

    def test_state_change_listeners(self):
        class States(enum.Enum):
            ONE = 1
            TWO = 2

        class Stuff(object):
            def __init__(self, machine_cls):
                self.state = None
                self.machine = machine_cls(states=States, initial=States.ONE, model=self)

                self.machine.add_transition('advance', States.ONE, States.TWO)
                self.machine.add_transition('reverse', States.TWO, States.ONE)
                self.machine.on_enter_TWO('hello')
                self.machine.on_exit_TWO('goodbye')

            def hello(self):
                self.message = 'Hello'

            def goodbye(self):
                self.message = 'Goodbye'

        s = Stuff(self.machine_cls)
        s.advance()

        assert s.is_TWO()
        assert s.message == 'Hello'

        s.reverse()

        assert s.is_ONE()
        assert s.message == 'Goodbye'


@skipIf(enum is None, "enum is not available")
class TestNestedStateEnums(TestEnumsAsStates):

    def setUp(self):
        super(TestNestedStateEnums, self).setUp()
        self.machine_cls = MachineFactory.get_predefined(nested=True)

    def test_root_enums(self):
        states = [self.States.RED, self.States.YELLOW,
                  {'name': self.States.GREEN, 'children': ['tick', 'tock'], 'initial': 'tick'}]
        m = self.machine_cls(states=states, initial=self.States.GREEN)
        self.assertTrue(m.is_GREEN(allow_substates=True))
        self.assertTrue(m.is_GREEN_tick())
        m.to_RED()
        self.assertTrue(m.state is self.States.RED)

    def test_nested_enums(self):
        states = ['A', self.States.GREEN,
                  {'name': 'C', 'children': self.States, 'initial': self.States.GREEN}]
        m1 = self.machine_cls(states=states, initial='C')
        m2 = self.machine_cls(states=states, initial='A')
        self.assertEqual(m1.state, self.States.GREEN)
        self.assertTrue(m1.is_GREEN())  # even though it is actually C_GREEN
        m2.to_GREEN()
        self.assertTrue(m2.is_C_GREEN())  # even though it is actually just GREEN
        self.assertEqual(m1.state, m2.state)
        m1.to_A()
        self.assertNotEqual(m1.state, m2.state)

    def test_initial_enum(self):
        m1 = self.machine_cls(states=self.States, initial=self.States.GREEN)
        self.assertEqual(self.States.GREEN, m1.state)
        self.assertEqual(m1.state.name, self.States.GREEN.name)

    def test_add_nested_enums_as_nested_state(self):
        from transitions.extensions.nesting_legacy import HierarchicalMachine
        if self.machine_cls is HierarchicalMachine:
            self.skipTest("Converting enums to nested states is not supported on the legacy HierarchicalMachine")

        class Foo(enum.Enum):
            A = 0
            B = 1

        class Bar(enum.Enum):
            FOO = Foo
            C = 2

        m = self.machine_cls(states=Bar, initial=Bar.C)

        self.assertEqual(sorted(m.states['FOO'].states.keys()), ['A', 'B'])

        m.to_FOO_A()
        self.assertFalse(m.is_C())
        self.assertTrue(m.is_FOO_A())


@skipIf(enum is None, "enum is not available")
class TestEnumsAsStatesWithGraph(TestEnumsAsStates):

    def setUp(self):
        super(TestEnumsAsStatesWithGraph, self).setUp()
        self.machine_cls = MachineFactory.get_predefined(graph=True)


@skipIf(enum is None, "enum is not available")
class TestNestedStateGraphEnums(TestNestedStateEnums):

    def setUp(self):
        super(TestNestedStateGraphEnums, self).setUp()
        self.machine_cls = MachineFactory.get_predefined(nested=True, graph=True)
