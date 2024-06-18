from .test_graphviz import TestDiagrams, TestDiagramsNested
from .utils import Stuff, DummyModel
from .test_core import TestTransitions, TYPE_CHECKING

from transitions.extensions import (
    LockedGraphMachine, GraphMachine, HierarchicalGraphMachine, LockedHierarchicalGraphMachine
)
from transitions.extensions.states import add_state_features, Timeout, Tags
from unittest import skipIf
import tempfile
import os
import re
import sys
from unittest import TestCase

try:
    # Just to skip tests if graphviz not installed
    import graphviz as pgv  # @UnresolvedImport
except ImportError:  # pragma: no cover
    pgv = None

if TYPE_CHECKING:
    from typing import Type, List, Collection, Union, Literal


class TestMermaidDiagrams(TestDiagrams):

    graph_engine = "mermaid"
    edge_re = re.compile(r"^\s+(?P<src>\w+)\s*-->\s*(?P<dst>\w+)\s*:\s*(?P<attr>.*)$")
    node_re = re.compile(r"^\s+state \"\S+(\s+(?P<attr>\[.*\]?))?\" as (?P<node>\S+)")

    def test_diagram(self):
        m = self.machine_cls(states=self.states, transitions=self.transitions, initial='A', auto_transitions=False,
                             title='a test', graph_engine=self.graph_engine)
        graph = m.get_graph()
        self.assertIsNotNone(graph)

        _, nodes, edges = self.parse_dot(graph)

        # Test that graph properties match the Machine
        self.assertEqual(set(m.states.keys()), nodes)
        self.assertEqual(len(edges), len(self.transitions))

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

    def test_to_method_filtering(self):
        m = self.machine_cls(states=['A', 'B', 'C'], initial='A', graph_engine=self.graph_engine)
        m.add_transition('to_state_A', 'B', 'A')
        m.add_transition('to_end', '*', 'C')
        _, _, edges = self.parse_dot(m.get_graph())
        self.assertEqual(len([e for e in edges if e == 'to_state_A']), 1)
        self.assertEqual(len([e for e in edges if e == 'to_end']), 3)
        m2 = self.machine_cls(states=['A', 'B', 'C'], initial='A', show_auto_transitions=True,
                              graph_engine=self.graph_engine)
        _, _, edges = self.parse_dot(m2.get_graph())
        self.assertEqual(len(edges), 9)
        self.assertEqual(len([e for e in edges if e == 'to_A']), 3)
        self.assertEqual(len([e for e in edges if e == 'to_C']), 3)

    def test_loops(self):
        m = self.machine_cls(states=['A'], initial='A', graph_engine=self.graph_engine)
        m.add_transition('reflexive', 'A', '=')
        m.add_transition('fixed', 'A', None)
        g1 = m.get_graph()
        dot_string, _, _ = self.parse_dot(g1)
        try:
            self.assertRegex(dot_string, r'A\s+-->\s+A:\s*(fixed|reflexive)')
        except AttributeError:  # Python 2 backwards compatibility

            self.assertRegexpMatches(dot_string, r'A\s+-->\s+A:\s*(fixed|reflexive)')

    def test_roi(self):
        m = self.machine_cls(states=['A', 'B', 'C', 'D', 'E', 'F'], initial='A', graph_engine=self.graph_engine)
        m.add_transition('to_state_A', 'B', 'A')
        m.add_transition('to_state_C', 'B', 'C')
        m.add_transition('to_state_F', 'B', 'F')
        g1 = m.get_graph(show_roi=True)
        dot, nodes, edges = self.parse_dot(g1)
        self.assertEqual(0, len(edges))
        self.assertIn(r'"A"', dot)
        # make sure that generating a graph without ROI has not influence on the later generated graph
        # this has to be checked since graph.custom_style is a class property and is persistent for multiple
        # calls of graph.generate()
        m.to_C()
        m.to_E()
        _ = m.get_graph()
        g2 = m.get_graph(show_roi=True)
        dot, _, _ = self.parse_dot(g2)
        self.assertNotIn(r'label="A\l"', dot)
        m.to_B()
        g3 = m.get_graph(show_roi=True)
        _, nodes, edges = self.parse_dot(g3)
        self.assertEqual(len(edges), 3)  # to_state_{A,C,F}
        self.assertEqual(len(nodes), 5)  # B + A,C,F (edges) + E (previous)

    def test_label_attribute(self):

        class LabelState(self.machine_cls.state_cls):  # type: ignore
            def __init__(self, *args, **kwargs):
                self.label = kwargs.pop('label')
                super(LabelState, self).__init__(*args, **kwargs)

        class CustomMachine(self.machine_cls):  # type: ignore
            state_cls = LabelState

        m = CustomMachine(states=[{'name': 'A', 'label': 'LabelA'},
                                  {'name': 'B', 'label': 'NotLabelA'}],
                          transitions=[{'trigger': 'event', 'source': 'A', 'dest': 'B', 'label': 'LabelEvent'}],
                          initial='A', graph_engine=self.graph_engine)
        dot, _, _ = self.parse_dot(m.get_graph())
        self.assertIn(r'"LabelA"', dot)
        self.assertIn(r'"NotLabelA"', dot)
        self.assertIn("LabelEvent", dot)
        self.assertNotIn(r'"A"', dot)
        self.assertNotIn("event", dot)

    def test_binary_stream(self):
        from io import BytesIO
        m = self.machine_cls(states=['A', 'B', 'C'], initial='A', auto_transitions=True,
                             title='A test', show_conditions=True, graph_engine=self.graph_engine)
        b1 = BytesIO()
        g = m.get_graph()
        g.draw(b1)
        b2 = g.draw(None)
        self.assertEqual(b2, b1.getvalue().decode())
        b1.close()

    def test_update_on_remove_transition(self):
        m = self.machine_cls(states=self.states, transitions=self.transitions, initial='A',
                             graph_engine=self.graph_engine, show_state_attributes=True)
        _, _, edges = self.parse_dot(m.get_graph())
        assert "walk" in edges
        m.remove_transition(trigger="walk", source="A", dest="B")
        _, _, edges = self.parse_dot(m.get_graph())
        assert not any("walk" == t["trigger"] for t in m.markup["transitions"])
        assert "walk" not in edges


class TestMermaidDiagramsNested(TestDiagramsNested, TestMermaidDiagrams):

    machine_cls = HierarchicalGraphMachine \
        # type: Type[Union[HierarchicalGraphMachine, LockedHierarchicalGraphMachine]]

    def test_diagram(self):
        m = self.machine_cls(states=self.states, transitions=self.transitions, initial='A', auto_transitions=False,
                             title='A test', show_conditions=True, graph_engine=self.graph_engine)
        graph = m.get_graph()
        self.assertIsNotNone(graph)

        _, nodes, edges = self.parse_dot(graph)

        self.assertEqual(len(edges), 8)
        # Test that graph properties match the Machine
        self.assertEqual(set(m.get_nested_state_names()), nodes)
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
                             graph_engine=self.graph_engine, show_conditions=True)
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

    def test_roi_parallel(self):
        class Model:
            @staticmethod
            def is_fast(*args, **kwargs):
                return True

        self.states[0] = {"name": "A", "parallel": ["1", "2"]}

        model = Model()
        m = self.machine_cls(model, states=self.states, transitions=self.transitions, initial='A', title='A test',
                             graph_engine=self.graph_engine, show_conditions=True)
        g1 = model.get_graph(show_roi=True)
        _, nodes, edges = self.parse_dot(g1)
        self.assertEqual(2, len(edges))  # reset and walk
        self.assertEqual(4, len(nodes))
        model.walk()
        model.run()
        model.sprint()
        g2 = model.get_graph(show_roi=True)
        _, nodes, edges = self.parse_dot(g2)
        self.assertEqual(len(edges), 2)
        self.assertEqual(len(nodes), 3)

    def test_roi_parallel_deeper(self):
        states = ['A', 'B', 'C', 'D',
                  {'name': 'P',
                   'parallel': [
                       '1',
                       {'name': '2', 'parallel': [
                           {'name': 'a'},
                           {'name': 'b', 'parallel': [
                               {'name': 'x', 'parallel': ['1', '2']}, 'y'
                           ]}
                       ]},
                   ]}]
        transitions = [["go", "A", "P"], ["reset", "*", "A"]]
        m = self.machine_cls(states=states, transitions=transitions, initial='A', title='A test',
                             graph_engine=self.graph_engine, show_conditions=True)
        m.go()
        _, nodes, edges = self.parse_dot(m.get_graph(show_roi=True))
        self.assertEqual(len(edges), 2)
        self.assertEqual(len(nodes), 10)


class TestDiagramsLockedNested(TestDiagramsNested):

    def setUp(self):
        super(TestDiagramsLockedNested, self).setUp()
        self.machine_cls = LockedHierarchicalGraphMachine  # type: Type[LockedHierarchicalGraphMachine]

    @skipIf(sys.version_info < (3, ), "Python 2.7 cannot retrieve __name__ from partials")
    def test_function_callbacks_annotation(self):
        super(TestDiagramsLockedNested, self).test_function_callbacks_annotation()
