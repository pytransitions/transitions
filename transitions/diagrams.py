import abc
try:
    import pygraphviz as pgv
except:
    pgv = None


class Diagram(object):
    def __init__(self, machine):
        self.machine = machine

    @abc.abstractmethod
    def get_graph(self):
        return

class AGraph(Diagram):
    state_attributes = {
        'shape': 'circle',
        'height': '1.2',
    }

    machine_attributes = {
        'directed': True,
        'strict': False,
        'rankdir': 'LR',
        'ratio': '0.3'
    }

    def _add_nodes(self, states, container):
        # For each state, draw a circle
        for state in states:
            shape = self.state_attributes['shape']

            # We want the first state to be a double circle (UML style)
            if state == list(self.machine.states.items())[0]:
                shape = 'doublecircle'
            else:
                shape = self.state_attributes['shape']

            state = state[0]
            container.add_node(n=state, shape=shape)

    def _add_edges(self, events, container):
        for state in events.items():
            shape = self.state_attributes['shape']

            # We want the first state to be a double circle (UML style)
            if state == list(self.machine.states.items())[0]:
                shape = 'doublecircle'
            else:
                shape = self.state_attributes['shape']

            state = state[0]
            container.add_node(n=state, shape=shape)

    def get_graph(self, title=None):
        """ Generate a DOT graph with pygraphviz, returns an AGraph object
        Args:
            title (string): Optional title for the graph.
        """
        if not pgv:
            raise Exception('AGraph diagram requires pygraphviz')

        if title is None:
            title = self.__class__.__name__
        elif title is False:
            title = ''

        fsm_graph = pgv.AGraph(title=title, **self.machine_attributes)
        fsm_graph.node_attr.update(self.state_attributes)

        # For each state, draw a circle
        self._add_nodes(self.machine.states, fsm_graph)
        fsm_graph.add_node('null', shape='plaintext', label='')

        self._add_edges(self.machine.events, fsm_graph)
        fsm_graph.add_edge('null', list(self.machine.states.items())[0][0])

        return fsm_graph
