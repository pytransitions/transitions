from unittest import TestCase, skipIf

try:
    import enum
except ImportError:
    enum = None

from transitions.extensions import MachineFactory
from .test_pygraphviz import pgv
from .test_graphviz import pgv as gv


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

    def test_enum_zero(self):
        from enum import IntEnum

        class State(IntEnum):
            FOO = 0
            BAR = 1

        transitions = [
            ['foo', State.FOO, State.BAR],
            ['bar', State.BAR, State.FOO]
        ]

        m = self.machine_cls(states=State, initial=State.FOO, transitions=transitions)
        m.foo()
        self.assertTrue(m.is_BAR())
        m.bar()
        self.assertTrue(m.is_FOO())


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

    def test_duplicate_states(self):
        with self.assertRaises(ValueError):
            self.machine_cls(states=['A', 'A'])

    def test_duplicate_states_from_enum_members(self):
        class Foo(enum.Enum):
            A = 1

        with self.assertRaises(ValueError):
            self.machine_cls(states=[Foo.A, Foo.A])

    def test_add_enum_transition(self):

        class Foo(enum.Enum):
            A = 0
            B = 1

        class Bar(enum.Enum):
            FOO = Foo
            C = 2

        m = self.machine_cls(states=Bar, initial=Bar.C, auto_transitions=False)
        m.add_transition('go', Bar.C, Foo.A, conditions=lambda: False)
        trans = m.events['go'].transitions['C']
        self.assertEqual(1, len(trans))
        self.assertEqual('FOO_A', trans[0].dest)
        m.add_transition('go', Bar.C, 'FOO_B')
        self.assertEqual(2, len(trans))
        self.assertEqual('FOO_B', trans[1].dest)
        m.go()
        self.assertTrue(m.is_FOO_B())
        m.add_transition('go', Foo.B, 'C')
        trans = m.events['go'].transitions['FOO_B']
        self.assertEqual(1, len(trans))
        self.assertEqual('C', trans[0].dest)
        m.go()
        self.assertEqual(m.state, Bar.C)

    def test_add_nested_enums_as_nested_state(self):
        class Foo(enum.Enum):
            A = 0
            B = 1

        class Bar(enum.Enum):
            FOO = Foo
            C = 2

        m = self.machine_cls(states=Bar, initial=Bar.C)
        self.assertEqual(sorted(m.states['FOO'].states.keys()), ['A', 'B'])
        m.add_transition('go', 'FOO_A', 'C')
        m.add_transition('go', 'C', 'FOO_B')
        m.add_transition('foo', Bar.C, Bar.FOO)

        m.to_FOO_A()
        self.assertFalse(m.is_C())
        self.assertTrue(m.is_FOO(allow_substates=True))
        self.assertTrue(m.is_FOO_A())
        self.assertTrue(m.is_FOO_A(allow_substates=True))
        m.go()
        self.assertEqual(Bar.C, m.state)
        m.go()
        self.assertEqual(Foo.B, m.state)
        m.to_state(m, Bar.C.name)
        self.assertEqual(Bar.C, m.state)
        m.foo()
        self.assertEqual(Bar.FOO, m.state)

    def test_enum_model_conversion(self):
        class Inner(enum.Enum):
            I1 = 1
            I2 = 2
            I3 = 3
            I4 = 0

        class Middle(enum.Enum):
            M1 = 10
            M2 = 20
            M3 = 30
            M4 = Inner

        class Outer(enum.Enum):
            O1 = 100
            O2 = 200
            O3 = 300
            O4 = Middle

        m = self.machine_cls(states=Outer, initial=Outer.O1)

    def test_enum_initial(self):
        class Foo(enum.Enum):
            A = 0
            B = 1

        class Bar(enum.Enum):
            FOO = dict(children=Foo, initial=Foo.A)
            C = 2

        m = self.machine_cls(states=Bar, initial=Bar.FOO)
        self.assertTrue(m.is_FOO_A())


@skipIf(enum is None or (pgv is None and gv is None), "enum and (py)graphviz are not available")
class TestEnumWithGraph(TestEnumsAsStates):

    def setUp(self):
        super(TestEnumWithGraph, self).setUp()
        self.machine_cls = MachineFactory.get_predefined(graph=True)


@skipIf(enum is None or (pgv is None and gv is None), "enum and (py)graphviz are not available")
class TestNestedStateGraphEnums(TestNestedStateEnums):

    def setUp(self):
        super(TestNestedStateGraphEnums, self).setUp()
        self.machine_cls = MachineFactory.get_predefined(nested=True, graph=True)
