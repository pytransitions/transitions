try:
    from builtins import object
except ImportError:
    pass

from transitions import HierarchicalMachine as Machine

from unittest import TestCase
import tempfile
import os


class TestDiagrams(TestCase):

    def test_agraph_diagram(self):
        states = ['A', 'B', {'name': 'C', 'children': ['1', '2', '3']}, 'D']
        transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'B'},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'D'}
        ]

        m = Machine(states=states, transitions=transitions, initial='A')
        graph = m.get_graph()

        # check for a valid pygraphviz diagram
        self.assertIsNotNone(graph)
        self.assertTrue("digraph" in str(graph))

        # write diagram to temp file
        target = tempfile.NamedTemporaryFile()
        graph.draw(target.name, prog='dot')
        self.assertTrue(os.path.getsize(target.name) > 0)

        # cleanup temp file
        target.close()
