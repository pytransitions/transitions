from unittest import TestCase, skipIf

try:
    import enum
except ImportError:
    enum = None

from transitions.extensions import MachineFactory


@skipIf(enum is None, "enum is not available")
class TestEnumsAsStates(TestCase):

    machine_cls = MachineFactory.get_predefined()

    def setUp(self):
        class States(enum.Enum):
            RED = 1
            YELLOW = 2
            GREEN = 3
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

    def test_str_enum(self):
        class States(str, enum.Enum):
            ONE = "one"
            TWO = "two"

        class Stuff(object):
            def __init__(self, machine_cls):
                self.state = None
                self.machine = machine_cls(states=States, initial=States.ONE, model=self)
                self.machine.add_transition("advance", States.ONE, States.TWO)

        s = Stuff(self.machine_cls)
        assert s.is_ONE()
        s.advance()
        assert s.is_TWO()


@skipIf(enum is None, "enum is not available")
class TestNestedStateEnums(TestEnumsAsStates):

    machine_cls = MachineFactory.get_predefined(nested=True)

    def test_root_enums(self):
        states = [self.States.RED, self.States.YELLOW,
                  {'name': self.States.GREEN, 'children': ['tick', 'tock'], 'initial': 'tick'}]
        m = self.machine_cls(states=states, initial=self.States.GREEN)
        self.assertTrue(m.is_GREEN(allow_substates=True))
        self.assertTrue(m.is_GREEN_tick())
        m.to_RED()
        self.assertTrue(m.state is self.States.RED)
        # self.assertEqual(m.state, self.States.GREEN)

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
