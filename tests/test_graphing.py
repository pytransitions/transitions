try:
    from builtins import object
except ImportError:
    pass

from transitions.extensions import MachineFactory
from unittest import TestCase
import tempfile
import os


def edge_label_from_transition_label(label):
    return label.split(' | ')[0].split(' [')[0]  # if no condition, label is returned; returns first event only


class TestDiagrams(TestCase):

    def test_agraph_diagram(self):
        states = ['A', 'B', 'C', 'D']
        transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'B'},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'D', 'conditions': 'is_fast'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'B'}
        ]

        machine_cls = MachineFactory.get_predefined(graph=True)
        m = machine_cls(states=states, transitions=transitions, initial='A', auto_transitions=False, title='a test')
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

        self.assertEqual(len(graph.edges()), len(transitions))
        # check for a valid pygraphviz diagram

        # write diagram to temp file
        target = tempfile.NamedTemporaryFile()
        graph.draw(target.name, prog='dot')
        self.assertTrue(os.path.getsize(target.name) > 0)

        # cleanup temp file
        target.close()
        print(graph)

    def test_nested_agraph_diagram(self):
        ''' Same as above, but with nested states. '''
        states = ['A', 'B', {'name': 'C', 'children': ['1', '2', '3']}, 'D']
        transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'B'},   # 1 edge
            {'trigger': 'run', 'source': 'B', 'dest': 'C'},    # + 1 edge
            {'trigger': 'sprint', 'source': 'C', 'dest': 'D',  # + 1 edges
             'conditions': 'is_fast'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'B'}  # + 1 edges = 4 edges
        ]

        hsm_graph_cls = MachineFactory.get_predefined(graph=True, nested=True)
        m = hsm_graph_cls(states=states, transitions=transitions, initial='A', auto_transitions=False,
                          title='A test', show_conditions=True)
        graph = m.get_graph()
        self.assertIsNotNone(graph)
        self.assertTrue("digraph" in str(graph))

        # Test that graph properties match the Machine
        # print((set(m.states.keys()), )
        node_names = set([n.name for n in graph.nodes()])
        self.assertEqual(set(m.states.keys()) - set('C'), node_names)

        triggers = set([n.attr['label'] for n in graph.edges()])
        for t in triggers:
            t = edge_label_from_transition_label(t)
            self.assertIsNotNone(getattr(m, t))

        self.assertEqual(len(graph.edges()), 4)  # see above

        m.walk()
        m.run()

        # write diagram to temp file
        target = tempfile.NamedTemporaryFile()
        graph.draw(target.name, prog='dot')
        self.assertTrue(os.path.getsize(target.name) > 0)

        # cleanup temp file
        target.close()

    def test_store_nested_agraph_diagram(self):
        ''' Same as above, but with nested states. '''
        states = ['standing', 'walking', {'name': 'caffeinated', 'children':['dithering', 'running']}]
        transitions = [
          ['walk', 'standing', 'walking'],                          #   1 edge
          ['go', 'standing', 'walking'],                            # (edge will be merged with previous edge)
          ['stop', 'walking', 'standing'],                          # + 1 edge
          ['drink', '*', 'caffeinated_dithering'],                  # + 4 edges
          ['walk', 'caffeinated_dithering', 'caffeinated_running'], # + 1 edge
          ['relax', 'caffeinated', 'standing']                      # + 1 edge = 8 edges
        ]

        hsm_graph_cls = MachineFactory.get_predefined(graph=True, nested=True)
        m = hsm_graph_cls(states=states, transitions=transitions, initial='standing', auto_transitions=False)
        graph = m.get_graph()
        self.assertIsNotNone(graph)
        self.assertTrue("digraph" in str(graph))

        # Test that graph properties match the Machine
        # print((set(m.states.keys()), )
        node_names = set([n.name for n in graph.nodes()])
        node_names.add('caffeinated')
        self.assertEqual(set(m.states.keys()), node_names)

        triggers = set([n.attr['label'] for n in graph.edges()])
        for t in triggers:
            t = edge_label_from_transition_label(t)
            self.assertIsNotNone(getattr(m, t))

        self.assertEqual(len(graph.edges()), 8)  # see above

        # Force a new
        graph2 = m.get_graph(title="Second Graph", force_new=True)
        self.assertIsNotNone(graph)
        self.assertTrue("digraph" in str(graph))

        self.assertFalse(graph == graph2)

        # write diagram to temp file
        target = tempfile.NamedTemporaryFile()
        graph.draw(target.name, prog='dot')
        self.assertTrue(os.path.getsize(target.name) > 0)

        # cleanup temp file
        target.close()

    def test_add_custom_state(self):
        states = ['A', 'B', 'C', 'D']
        transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'B'},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'D', 'conditions': 'is_fast'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'B'}
        ]

        machine_cls = MachineFactory.get_predefined(graph=True)
        m = machine_cls(states=states, transitions=transitions, initial='A', auto_transitions=False, title='a test')
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

        machine_cls = MachineFactory.get_predefined(graph=True)
        m = machine_cls(
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
