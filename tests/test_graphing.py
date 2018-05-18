try:
    from builtins import object
except ImportError:
    pass

from .utils import Stuff
from .test_core import TestTransitions

from transitions.extensions import MachineFactory
from transitions.extensions.diagrams import rep
from transitions.extensions.nesting import NestedState
from unittest import skipIf
from functools import partial
import tempfile
import os

try:
    # Just to skip tests if *pygraphviz8 not installed
    import pygraphviz as pgv  # @UnresolvedImport
except ImportError:  # pragma: no cover
    pgv = None


def edge_label_from_transition_label(label):
    return label.split(' | ')[0].split(' [')[0]  # if no condition, label is returned; returns first event only


class TestRep(TestTransitions):

    def test_rep_string(self):
        self.assertEqual(rep("string"), "string")

    def test_rep_function(self):
        def check():
            return True
        self.assertTrue(check())
        self.assertEqual(rep(check), "check")

    def test_rep_partial_no_args_no_kwargs(self):
        def check():
            return True
        pcheck = partial(check)
        self.assertTrue(pcheck())
        self.assertEqual(rep(pcheck), "check()")

    def test_rep_partial_with_args(self):
        def check(result):
            return result
        pcheck = partial(check, True)
        self.assertTrue(pcheck())
        self.assertEqual(rep(pcheck), "check(True)")

    def test_rep_partial_with_kwargs(self):
        def check(result=True):
            return result
        pcheck = partial(check, result=True)
        self.assertTrue(pcheck())
        self.assertEqual(rep(pcheck), "check(result=True)")

    def test_rep_partial_with_args_and_kwargs(self):
        def check(result, doublecheck=True):
            return result == doublecheck
        pcheck = partial(check, True, doublecheck=True)
        self.assertTrue(pcheck())
        self.assertEqual(rep(pcheck), "check(True, doublecheck=True)")

    def test_rep_callable_class(self):
        class Check(object):
            def __init__(self, result):
                self.result = result

            def __call__(self):
                return self.result

            def __repr__(self):
                return "%s(%r)" % (type(self).__name__, self.result)

        ccheck = Check(True)
        self.assertTrue(ccheck())
        self.assertEqual(rep(ccheck), "Check(True)")


@skipIf(pgv is None, 'Graph diagram requires pygraphviz')
class TestDiagrams(TestTransitions):

    machine_cls = MachineFactory.get_predefined(graph=True)

    def setUp(self):
        self.stuff = Stuff(machine_cls=self.machine_cls)
        self.states = ['A', 'B', 'C', 'D']
        self.transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'B'},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'D', 'conditions': 'is_fast'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'B'}
        ]

    def test_diagram(self):
        m = self.machine_cls(states=self.states, transitions=self.transitions, initial='A', auto_transitions=False, title='a test')
        graph = m.get_graph()
        self.assertIsNotNone(graph)
        self.assertTrue("digraph" in str(graph))

        # Test that graph properties match the Machine
        self.assertEqual(
            set(m.states.keys()), set([n.name for n in graph.nodes()]))
        triggers = set([n.attr['label'] for n in graph.edges()])
        for t in triggers:
            t = edge_label_from_transition_label(t)
            self.assertIsNotNone(getattr(m, t))

        self.assertEqual(len(graph.edges()), len(self.transitions))

        # write diagram to temp file
        target = tempfile.NamedTemporaryFile()
        graph.draw(target.name, prog='dot')
        self.assertTrue(os.path.getsize(target.name) > 0)

        # cleanup temp file
        target.close()

        graph = m.get_graph(force_new=True, title=False)
        self.assertEqual("", graph.graph_attr['label'])

    def test_add_custom_state(self):
        m = self.machine_cls(states=self.states, transitions=self.transitions, initial='A', auto_transitions=False, title='a test')
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
        m = self.machine_cls(model=[m1, m2], states=self.states, transitions=self.transitions, initial='A')
        m1.walk()
        self.assertEqual(m1.get_graph().get_node(m1.state).attr['color'],
                         m1.get_graph().style_attributes['node']['active']['color'])
        self.assertEqual(m2.get_graph().get_node(m1.state).attr['color'],
                         m2.get_graph().style_attributes['node']['default']['color'])
        # backwards compatibility test
        self.assertEqual(id(m.get_graph()), id(m1.get_graph()))

    def test_model_method_collision(self):
        class GraphModel:
            def get_graph(self):
                return "This method already exists"

        model = GraphModel()
        with self.assertRaises(AttributeError):
            m = self.machine_cls(model=model)
        self.assertEqual(model.get_graph(), "This method already exists")

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

    def test_loops(self):
        m = self.machine_cls(states=['A'], initial='A')
        m.add_transition('reflexive', 'A', '=')
        m.add_transition('fixed', 'A', None)
        g1 = m.get_graph()

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


@skipIf(pgv is None, 'Graph diagram requires pygraphviz')
class TestDiagramsLocked(TestDiagrams):

    machine_cls = MachineFactory.get_predefined(graph=True, locked=True)


@skipIf(pgv is None, 'NestedGraph diagram requires pygraphviz')
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
                             title='A test', show_conditions=True)
        graph = m.get_graph()
        self.assertIsNotNone(graph)
        self.assertTrue("digraph" in str(graph))

        # Test that graph properties match the Machine
        node_names = set([n.name for n in graph.nodes()])
        self.assertEqual(set(m.states.keys()) - set(['C', 'C%s1' % NestedState.separator]),
                         node_names - set(['C_anchor', 'C%s1_anchor' % NestedState.separator]))

        triggers = set([n.attr['label'] for n in graph.edges()])
        for t in triggers:
            t = edge_label_from_transition_label(t)
            self.assertIsNotNone(getattr(m, t))

        self.assertEqual(len(graph.edges()), 14)  # see above

        m.walk()
        m.run()

        # write diagram to temp file
        target = tempfile.NamedTemporaryFile()
        sgraph = graph.get_subgraph('cluster_C').get_subgraph('cluster_C_child')
        sgraph = sgraph.get_subgraph('cluster_C%s1' % NestedState.separator)
        self.assertIsNotNone(sgraph)
        # print(graph.string())
        graph.draw(target.name, prog='dot')
        self.assertTrue(os.path.getsize(target.name) > 0)

        # cleanup temp file
        target.close()

    def test_roi(self):
        class Model:
            def is_fast(self, *args, **kwargs):
                return True
        model = Model()
        m = self.machine_cls(model, states=self.states, transitions=self.transitions,
                             initial='A', title='A test', show_conditions=True)
        model.walk()
        model.run()
        g1 = model.get_graph(show_roi=True)
        self.assertEqual(len(g1.edges()), 4)
        self.assertEqual(len(g1.nodes()), 4)
        model.sprint()
        g2 = model.get_graph(show_roi=True)
        self.assertEqual(len(g2.edges()), 2)
        self.assertEqual(len(g2.nodes()), 3)


@skipIf(pgv is None, 'NestedGraph diagram requires pygraphviz')
class TestDiagramsLockedNested(TestDiagramsNested):

    def setUp(self):
        super(TestDiagramsLockedNested, self).setUp()
        self.machine_cls = MachineFactory.get_predefined(graph=True, nested=True, locked=True)
