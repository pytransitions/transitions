try:
    from builtins import object
except ImportError:
    pass

import transitions

from .utils import Stuff
from .test_core import TestTransitions

from transitions.extensions import MachineFactory
from transitions.extensions.nesting import NestedState
from transitions.extensions.states import add_state_features, Timeout, Tags
from unittest import skipIf
import tempfile
import os
import sys

try:
    # Just to skip tests if graphviz not installed
    import graphviz as pgv  # @UnresolvedImport
except ImportError:  # pragma: no cover
    pgv = None


def edge_label_from_transition_label(label):
    return label.split(' | ')[0].split(' [')[0]  # if no condition, label is returned; returns first event only


def parse_dot(dot):
    nodes = []
    edges = []
    for line in dot.split('\n'):
        if '->' in line:
            src, rest = line.split('->')
            dst, attr = rest.split(None, 1)
            nodes.append(src.strip().replace('"', ''))
            nodes.append(dst)
            edges.append(attr)
    return set(nodes), edges


@skipIf(pgv is None, 'Graph diagram test requires graphviz.')
class TestDiagrams(TestTransitions):

    machine_cls = MachineFactory.get_predefined(graph=True)
    use_pygraphviz = False

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

        nodes, edges = parse_dot(graph.source)

        # Test that graph properties match the Machine
        self.assertEqual(set(m.states.keys()), nodes)
        self.assertEqual(len(edges), len(self.transitions))

        # triggers = set([n.attr['label'] for n in graph.edges()])
        # for t in triggers:
        #     t = edge_label_from_transition_label(t)
        #     self.assertIsNotNone(getattr(m, t))

        # write diagram to temp file
        target = tempfile.NamedTemporaryFile(suffix='.png')
        graph.draw(target.name, format='png')
        self.assertTrue(os.path.getsize(target.name) > 0)
        # backwards compatibility check
        m.get_graph().draw(target.name, format='png', prog='dot')
        self.assertTrue(os.path.getsize(target.name) > 0)

        # cleanup temp file
        target.close()

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
        # self.assertEqual(id(m.get_graph()), id(m1.get_graph()))

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
        e = m.get_graph()
        nodes, edges = parse_dot(e.source)
        # self.assertEqual(e.attr['label'], 'to_state_A')
        # e = m.get_graph().get_edge('A', 'C')
        # self.assertEqual(e.attr['label'], 'to_end')
        # with self.assertRaises(KeyError):
        #     m.get_graph().get_edge('A', 'B')
        m2 = self.machine_cls(states=['A', 'B'], initial='A', show_auto_transitions=True,
                              use_pygraphviz=self.use_pygraphviz)
        nodes, edges = parse_dot(m2.get_graph().source)
        # self.assertEqual(len(m2.get_graph().get_edge('B', 'A')), 2)
        # self.assertEqual(m2.get_graph().get_edge('A', 'B').attr['label'], 'to_B')

    def test_loops(self):
        m = self.machine_cls(states=['A'], initial='A', use_pygraphviz=self.use_pygraphviz)
        m.add_transition('reflexive', 'A', '=')
        m.add_transition('fixed', 'A', None)
        g1 = m.get_graph()

    def test_roi(self):
        m = self.machine_cls(states=['A', 'B', 'C', 'D', 'E', 'F'], initial='A', use_pygraphviz=self.use_pygraphviz)
        m.add_transition('to_state_A', 'B', 'A')
        m.add_transition('to_state_C', 'B', 'C')
        m.add_transition('to_state_F', 'B', 'F')
        g1 = m.get_graph(show_roi=True)
        nodes, edges = parse_dot(g1.source)
        self.assertEqual(len(edges), 0)
        self.assertIn("label=A", g1.source)
        # make sure that generating a graph without ROI has not influence on the later generated graph
        # this has to be checked since graph.custom_style is a class property and is persistent for multiple
        # calls of graph.generate()
        m.to_C()
        m.to_E()
        _ = m.get_graph()
        g2 = m.get_graph(show_roi=True)
        self.assertNotIn("label=A", g2.source)
        m.to_B()
        g3 = m.get_graph(show_roi=True)
        nodes, edges = parse_dot(g3.source)
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
            {'trigger': 'reset', 'source': '*', 'dest': 'A'}]    # + 10 (8 nodes; 2 cluster) edges = 14

    def test_diagram(self):
        m = self.machine_cls(states=self.states, transitions=self.transitions, initial='A', auto_transitions=False,
                             title='A test', show_conditions=True, use_pygraphviz=self.use_pygraphviz)
        graph = m.get_graph()
        self.assertIsNotNone(graph)
        self.assertTrue("digraph" in str(graph))

        nodes, edges = parse_dot(graph.source)

        self.assertEqual(len(edges), 14)
        # Test that graph properties match the Machine
        self.assertEqual(set(m.states.keys()) - set(['C', 'C%s1' % NestedState.separator]),
                         set(nodes) - set(['C_anchor', 'C%s1_anchor' % NestedState.separator]))
        m.walk()
        m.run()

        # write diagram to temp file
        target = tempfile.NamedTemporaryFile(suffix='.png')
        graph.render(target.name)
        self.assertTrue(os.path.getsize(target.name) > 0)
        # backwards compatibility check
        m.get_graph().draw(target.name, prog='dot')
        self.assertTrue(os.path.getsize(target.name) > 0)

        # cleanup temp file
        target.close()

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
        nodes, edges = parse_dot(g1.source)
        self.assertEqual(len(edges), 4)
        self.assertEqual(len(nodes), 4)
        model.sprint()
        g2 = model.get_graph(show_roi=True)
        nodes, edges = parse_dot(g2.source)
        self.assertEqual(len(edges), 2)
        self.assertEqual(len(nodes), 3)


@skipIf(pgv is None, 'NestedGraph diagram test requires graphviz')
class TestDiagramsLockedNested(TestDiagramsNested):

    def setUp(self):
        super(TestDiagramsLockedNested, self).setUp()
        self.machine_cls = MachineFactory.get_predefined(graph=True, nested=True, locked=True)
