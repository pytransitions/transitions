try:
    from builtins import object
except ImportError:
    pass

from .utils import Stuff, DummyModel
from .test_core import TestTransitions

from transitions.extensions import MachineFactory
from transitions.extensions.nesting import NestedState
from transitions.extensions.states import add_state_features, Timeout, Tags
from unittest import skipIf
import tempfile
import os
import re

try:
    # Just to skip tests if graphviz not installed
    import graphviz as pgv  # @UnresolvedImport
except ImportError:  # pragma: no cover
    pgv = None


@skipIf(pgv is None, 'Graph diagram test requires graphviz.')
class TestDiagrams(TestTransitions):

    machine_cls = MachineFactory.get_predefined(graph=True)
    use_pygraphviz = False

    def parse_dot(self, graph):
        if self.use_pygraphviz:
            dot = graph.string()
        else:
            dot = graph.source
        nodes = []
        edges = []
        for line in dot.split('\n'):
            if '->' in line:
                src, rest = line.split('->')
                dst, attr = rest.split(None, 1)
                nodes.append(src.strip().replace('"', ''))
                nodes.append(dst)
                edges.append(attr)
        return dot, set(nodes), edges

    def tearDown(self):
        pass
        # for m in ['pygraphviz', 'graphviz']:
        #     if 'transitions.extensions.diagrams_' + m in sys.modules:
        #         del sys.modules['transitions.extensions.diagrams_' + m]

    def setUp(self):
        self.stuff = Stuff(machine_cls=self.machine_cls, extra_kwargs={'use_pygraphviz': self.use_pygraphviz})
        self.states = ['A', 'B', 'C', 'D']
        self.transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'B'},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'D', 'conditions': 'is_fast'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'B'}
        ]

    def test_diagram(self):
        m = self.machine_cls(states=self.states, transitions=self.transitions, initial='A', auto_transitions=False,
                             title='a test', use_pygraphviz=self.use_pygraphviz)
        graph = m.get_graph()
        self.assertIsNotNone(graph)
        self.assertTrue(graph.directed)

        _, nodes, edges = self.parse_dot(graph)

        # Test that graph properties match the Machine
        self.assertEqual(set(m.states.keys()), nodes)
        self.assertEqual(len(edges), len(self.transitions))

        for e in edges:
            # label should be equivalent to the event name
            self.assertIsNotNone(getattr(m, re.match(r'\[label=([^\]]+)\]', e).group(1)))

        # write diagram to temp file
        target = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        graph.draw(target.name, format='png', prog='dot')
        self.assertTrue(os.path.getsize(target.name) > 0)
        # backwards compatibility check
        m.get_graph().draw(target.name, format='png', prog='dot')
        self.assertTrue(os.path.getsize(target.name) > 0)

        # cleanup temp file
        target.close()
        os.unlink(target.name)

    def test_transition_custom_model(self):
        m = self.machine_cls(model=None, states=self.states, transitions=self.transitions, initial='A',
                             auto_transitions=False, title='a test', use_pygraphviz=self.use_pygraphviz)
        model = DummyModel()
        m.add_model(model)
        model.walk()

    def test_add_custom_state(self):
        m = self.machine_cls(states=self.states, transitions=self.transitions, initial='A', auto_transitions=False,
                             title='a test', use_pygraphviz=self.use_pygraphviz)
        m.add_state('X')
        m.add_transition('foo', '*', 'X')
        m.foo()

    def test_if_multiple_edges_are_supported(self):
        transitions = [
            ['event_0', 'a', 'b'],
            ['event_1', 'a', 'b'],
            ['event_2', 'a', 'b'],
            ['event_3', 'a', 'b'],
        ]

        m = self.machine_cls(
            states=['a', 'b'],
            transitions=transitions,
            initial='a',
            auto_transitions=False,
            use_pygraphviz=self.use_pygraphviz
        )

        graph = m.get_graph()
        self.assertIsNotNone(graph)
        self.assertTrue("digraph" in str(graph))

        triggers = [transition[0] for transition in transitions]
        for trigger in triggers:
            self.assertTrue(trigger in str(graph))

    def test_multi_model_state(self):
        m1 = Stuff(machine_cls=None, extra_kwargs={'use_pygraphviz': self.use_pygraphviz})
        m2 = Stuff(machine_cls=None, extra_kwargs={'use_pygraphviz': self.use_pygraphviz})
        m = self.machine_cls(model=[m1, m2], states=self.states, transitions=self.transitions, initial='A',
                             use_pygraphviz=self.use_pygraphviz)
        m1.walk()
        self.assertEqual(m.model_graphs[m1].custom_styles['node'][m1.state], 'active')
        self.assertEqual(m.model_graphs[m2].custom_styles['node'][m1.state], '')
        # backwards compatibility test
        dot1, _, _ = self.parse_dot(m1.get_graph())
        dot, _, _ = self.parse_dot(m.get_graph())
        self.assertEqual(dot, dot1)

    def test_model_method_collision(self):
        class GraphModel:
            def get_graph(self):
                return "This method already exists"

        model = GraphModel()
        with self.assertRaises(AttributeError):
            m = self.machine_cls(model=model)
        self.assertEqual(model.get_graph(), "This method already exists")

    def test_to_method_filtering(self):
        m = self.machine_cls(states=['A', 'B', 'C'], initial='A', use_pygraphviz=self.use_pygraphviz)
        m.add_transition('to_state_A', 'B', 'A')
        m.add_transition('to_end', '*', 'C')
        _, _, edges = self.parse_dot(m.get_graph())
        self.assertEqual(len([e for e in edges if e == '[label=to_state_A]']), 1)
        self.assertEqual(len([e for e in edges if e == '[label=to_end]']), 3)
        m2 = self.machine_cls(states=['A', 'B', 'C'], initial='A', show_auto_transitions=True,
                              use_pygraphviz=self.use_pygraphviz)
        _, _, edges = self.parse_dot(m2.get_graph())
        self.assertEqual(len(edges), 9)
        self.assertEqual(len([e for e in edges if e == '[label=to_A]']), 3)
        self.assertEqual(len([e for e in edges if e == '[label=to_C]']), 3)

    def test_loops(self):
        m = self.machine_cls(states=['A'], initial='A', use_pygraphviz=self.use_pygraphviz)
        m.add_transition('reflexive', 'A', '=')
        m.add_transition('fixed', 'A', None)
        g1 = m.get_graph()
        if self.use_pygraphviz:
            dot_string = g1.string()
        else:
            dot_string = g1.source
        try:
            self.assertRegex(dot_string, r'A\s+->\s*A\s+\[label="(fixed|reflexive)')
        except AttributeError:  # Python 2 backwards compatibility

            self.assertRegexpMatches(dot_string, r'A\s+->\s*A\s+\[label="(fixed|reflexive)')

    def test_roi(self):
        m = self.machine_cls(states=['A', 'B', 'C', 'D', 'E', 'F'], initial='A', use_pygraphviz=self.use_pygraphviz)
        m.add_transition('to_state_A', 'B', 'A')
        m.add_transition('to_state_C', 'B', 'C')
        m.add_transition('to_state_F', 'B', 'F')
        g1 = m.get_graph(show_roi=True)
        dot, nodes, edges = self.parse_dot(g1)
        self.assertEqual(len(edges), 0)
        self.assertIn("label=A", dot)
        # make sure that generating a graph without ROI has not influence on the later generated graph
        # this has to be checked since graph.custom_style is a class property and is persistent for multiple
        # calls of graph.generate()
        m.to_C()
        m.to_E()
        _ = m.get_graph()
        g2 = m.get_graph(show_roi=True)
        dot, _, _ = self.parse_dot(g2)
        self.assertNotIn("label=A", dot)
        m.to_B()
        g3 = m.get_graph(show_roi=True)
        _, nodes, edges = self.parse_dot(g3)
        self.assertEqual(len(edges), 3)
        self.assertEqual(len(nodes), 4)

    def test_state_tags(self):

        @add_state_features(Tags, Timeout)
        class CustomMachine(self.machine_cls):
            pass

        self.states[0] = {'name': 'A', 'tags': ['new', 'polling'], 'timeout': 5, 'on_enter': 'say_hello',
                          'on_exit': 'say_goodbye', 'on_timeout': 'do_something'}
        m = CustomMachine(states=self.states, transitions=self.transitions, initial='A', show_state_attributes=True,
                          use_pygraphviz=self.use_pygraphviz)
        g = m.get_graph(show_roi=True)


@skipIf(pgv is None, 'Graph diagram test requires graphviz')
class TestDiagramsLocked(TestDiagrams):

    machine_cls = MachineFactory.get_predefined(graph=True, locked=True)


@skipIf(pgv is None, 'NestedGraph diagram test requires graphviz')
class TestDiagramsNested(TestDiagrams):

    machine_cls = MachineFactory.get_predefined(graph=True, nested=True)

    def setUp(self):
        super(TestDiagramsNested, self).setUp()
        self.states = ['A', 'B',
                       {'name': 'C', 'children': [{'name': '1', 'children': ['a', 'b', 'c']},
                                                  '2', '3']}, 'D']
        self.transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'B'},     # 1 edge
            {'trigger': 'run', 'source': 'B', 'dest': 'C'},      # + 1 edge
            {'trigger': 'sprint', 'source': 'C', 'dest': 'D',    # + 1 edge
             'conditions': 'is_fast'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'B'},   # + 1 edge
            {'trigger': 'reset', 'source': '*', 'dest': 'A'}]    # + 4 edges (from base state) = 8

    def test_diagram(self):
        m = self.machine_cls(states=self.states, transitions=self.transitions, initial='A', auto_transitions=False,
                             title='A test', show_conditions=True, use_pygraphviz=self.use_pygraphviz)
        graph = m.get_graph()
        self.assertIsNotNone(graph)
        self.assertTrue("digraph" in str(graph))

        _, nodes, edges = self.parse_dot(graph)

        self.assertEqual(len(edges), 8)
        # Test that graph properties match the Machine
        self.assertEqual(set(m.states.keys()) - set(['C', 'C%s1' % NestedState.separator]),
                         set(nodes) - set(['C_anchor', 'C%s1_anchor' % NestedState.separator]))
        m.walk()
        m.run()

        # write diagram to temp file
        target = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        m.get_graph().draw(target.name, prog='dot')
        self.assertTrue(os.path.getsize(target.name) > 0)
        # backwards compatibility check
        m.get_graph().draw(target.name, prog='dot')
        self.assertTrue(os.path.getsize(target.name) > 0)

        # cleanup temp file
        target.close()
        os.unlink(target.name)

    def test_roi(self):
        class Model:
            def is_fast(self, *args, **kwargs):
                return True
        model = Model()
        m = self.machine_cls(model, states=self.states, transitions=self.transitions, initial='A', title='A test',
                             use_pygraphviz=self.use_pygraphviz, show_conditions=True)
        model.walk()
        model.run()
        g1 = model.get_graph(show_roi=True)
        _, nodes, edges = self.parse_dot(g1)
        self.assertEqual(len(edges), 4)
        self.assertEqual(len(nodes), 4)
        model.sprint()
        g2 = model.get_graph(show_roi=True)
        dot, nodes, edges = self.parse_dot(g2)
        self.assertEqual(len(edges), 2)
        self.assertEqual(len(nodes), 3)

    def test_internal(self):
        states = ['A', 'B']
        transitions = [['go', 'A', 'B'],
                       dict(trigger='fail', source='A', dest=None, conditions=['failed']),
                       dict(trigger='fail', source='A', dest='B', unless=['failed'])]
        m = self.machine_cls(states=states, transitions=transitions, initial='A', show_conditions=True,
                             use_pygraphviz=self.use_pygraphviz)

        _, nodes, edges = self.parse_dot(m.get_graph())
        self.assertEqual(len(nodes), 2)
        self.assertEqual(len([e for e in edges if '[internal]' in e]), 1)

    def test_internal_wildcards(self):
        internal_only_once = r'^(?:(?!\[internal\]).)*\[internal\](?!.*\[internal\]).*$'
        states = [
            "initial",
            "ready",
            "running"
        ]
        transitions = [
            ["booted", "initial", "ready"],
            {"trigger": "polled", "source": "ready", "dest": "running", "conditions": "door_closed"},
            ["done", "running", "ready"],
            ["polled", "*", None]
        ]
        m = self.machine_cls(states=states, transitions=transitions, show_conditions=True,
                             use_pygraphviz=self.use_pygraphviz, initial='initial')
        _, nodes, edges = self.parse_dot(m.get_graph())
        self.assertEqual(len(nodes), 3)
        self.assertEqual(len([e for e in edges if re.match(internal_only_once, e)]), 3)

    def test_nested_notebook(self):
        states = [{'name': 'caffeinated',
                   'on_enter': 'do_x',
                   'children': ['dithering', 'running'],
                   'transitions': [['walk', 'dithering', 'running'],
                                   ['drink', 'dithering', '=']],
                   },
                  {'name': 'standing', 'on_enter': ['do_x', 'do_y'], 'on_exit': 'do_z'},
                  {'name': 'walking', 'tags': ['accepted', 'pending'], 'timeout': 5, 'on_timeout': 'do_z'}]

        transitions = [
            ['walk', 'standing', 'walking'],
            ['go', 'standing', 'walking'],
            ['stop', 'walking', 'standing'],
            {'trigger': 'drink', 'source': '*',
             'dest': 'caffeinated{0}dithering'.format(self.machine_cls.state_cls.separator),
             'conditions': 'is_hot', 'unless': 'is_too_hot'},
            ['relax', 'caffeinated', 'standing'],
            ['sip', 'standing', 'caffeinated']
        ]

        @add_state_features(Timeout, Tags)
        class CustomStateMachine(self.machine_cls):

            def is_hot(self):
                return True

            def is_too_hot(self):
                return False

            def do_x(self):
                pass

            def do_z(self):
                pass

        extra_args = dict(auto_transitions=False, initial='standing', title='Mood Matrix',
                          show_conditions=True, show_state_attributes=True, use_pygraphviz=self.use_pygraphviz)
        machine = CustomStateMachine(states=states, transitions=transitions, **extra_args)
        g1 = machine.get_graph()
        # dithering should have 4 'drink' edges, a) from walking, b) from initial, c) from running and d) from itself
        if self.use_pygraphviz:
            dot_string = g1.string()
        else:
            dot_string = g1.source
        count = re.findall('-> "?caffeinated{0}dithering"?'.format(machine.state_cls.separator), dot_string)
        self.assertEqual(4, len(count))
        self.assertTrue(True)
        machine.drink()
        machine.drink()
        g1 = machine.get_graph()
        self.assertIsNotNone(g1)


@skipIf(pgv is None, 'NestedGraph diagram test requires graphviz')
class TestDiagramsLockedNested(TestDiagramsNested):

    def setUp(self):
        super(TestDiagramsLockedNested, self).setUp()
        self.machine_cls = MachineFactory.get_predefined(graph=True, nested=True, locked=True)
