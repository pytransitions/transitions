try:
    from builtins import object
except ImportError:
    pass

from .utils import Stuff
from .test_graphviz import TestDiagrams, TestDiagramsNested, NestedState
from transitions.extensions.states import add_state_features, Timeout, Tags
from unittest import skipIf
import tempfile
import os

try:
    # Just to skip tests if graphviz not installed
    import pygraphviz as pgv  # @UnresolvedImport
except ImportError:  # pragma: no cover
    pgv = None


@skipIf(pgv is None, 'Graph diagram requires pygraphviz')
class PygraphvizTest(TestDiagrams):

    use_pygraphviz = True

    def setUp(self):
        super(PygraphvizTest, self).setUp()

    # def test_diagram(self):
    #     m = self.machine_cls(states=self.states, transitions=self.transitions, use_pygraphviz=self.use_pygraphviz,
    #                          initial='A', auto_transitions=False, title='a test')
    #     graph = m.get_graph()
    #     self.assertIsNotNone(graph)
    #     self.assertTrue(graph.directed)
    #
    #     # Test that graph properties match the Machine
    #     self.assertEqual(
    #         set(m.states.keys()), set([n.name for n in graph.nodes()]))
    #     triggers = set([n.attr['label'] for n in graph.edges()])
    #     for t in triggers:
    #         t = edge_label_from_transition_label(t)
    #         self.assertIsNotNone(getattr(m, t))
    #
    #     self.assertEqual(len(graph.edges()), len(self.transitions))
    #
    #     # write diagram to temp file
    #     target = tempfile.NamedTemporaryFile()
    #     graph.draw(target.name, prog='dot')
    #     self.assertTrue(os.path.getsize(target.name) > 0)
    #
    #     # cleanup temp file
    #     target.close()
    #
    #     graph = m.get_graph(force_new=True, title=False)
    #     self.assertEqual("", graph.graph_attr['label'])

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
        m1 = Stuff(machine_cls=None)
        m2 = Stuff(machine_cls=None)
        m = self.machine_cls(model=[m1, m2], states=self.states, transitions=self.transitions, initial='A',
                             use_pygraphviz=self.use_pygraphviz)
        m1.walk()
        self.assertEqual(m1.get_graph().get_node(m1.state).attr['color'],
                         m1.get_graph().style_attributes['node']['active']['color'])
        self.assertEqual(m2.get_graph().get_node(m1.state).attr['color'],
                         m2.get_graph().style_attributes['node']['default']['color'])
        # backwards compatibility test
        self.assertEqual(id(m.get_graph()), id(m1.get_graph()))

    def test_to_method_filtering(self):
        m = self.machine_cls(states=['A', 'B', 'C'], initial='A')
        m.add_transition('to_state_A', 'B', 'A')
        m.add_transition('to_end', '*', 'C')
        e = m.get_graph().get_edge('B', 'A')
        self.assertEqual(e.attr['label'], 'to_state_A')
        e = m.get_graph().get_edge('A', 'C')
        self.assertEqual(e.attr['label'], 'to_end')
        with self.assertRaises(KeyError):
            m.get_graph().get_edge('A', 'B')
        m2 = self.machine_cls(states=['A', 'B'], initial='A', show_auto_transitions=True)
        self.assertEqual(len(m2.get_graph().get_edge('B', 'A')), 2)
        self.assertEqual(m2.get_graph().get_edge('A', 'B').attr['label'], 'to_B')

    def test_roi(self):
        m = self.machine_cls(states=['A', 'B', 'C', 'D', 'E', 'F'], initial='A')
        m.add_transition('to_state_A', 'B', 'A')
        m.add_transition('to_state_C', 'B', 'C')
        m.add_transition('to_state_F', 'B', 'F')
        g1 = m.get_graph(show_roi=True)
        self.assertEqual(len(g1.edges()), 0)
        self.assertEqual(len(g1.nodes()), 1)
        m.to_B()
        g2 = m.get_graph(show_roi=True)
        self.assertEqual(len(g2.edges()), 4)
        self.assertEqual(len(g2.nodes()), 4)

    def test_state_tags(self):

        @add_state_features(Tags, Timeout)
        class CustomMachine(self.machine_cls):
            pass

        self.states[0] = {'name': 'A', 'tags': ['new', 'polling'], 'timeout': 5, 'on_enter': 'say_hello',
                          'on_exit': 'say_goodbye', 'on_timeout': 'do_something'}
        m = CustomMachine(states=self.states, transitions=self.transitions, initial='A', show_state_attributes=True)
        g = m.get_graph(show_roi=True)


@skipIf(pgv is None, 'NestedGraph diagram requires pygraphviz')
class TestPygraphvizNested(TestDiagramsNested, PygraphvizTest):

    use_pygraphviz = True
