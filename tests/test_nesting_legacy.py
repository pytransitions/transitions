from .test_nesting import TestTransitions, Stuff
from transitions.extensions.nesting_legacy import HierarchicalMachine, NestedState


class TestNestedLegacy(TestTransitions):

    def setUp(self):
        super(TestNestedLegacy, self).setUp()
        self.machine_cls = HierarchicalMachine
        self.stuff = Stuff(self.states, self.machine_cls)
        self.state_cls = NestedState

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
        pass
