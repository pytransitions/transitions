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
    default_state_attributes = {
        'shape': 'circle',
        'height': '1.2',
        'style': 'filled',
        'fillcolor': 'white',
        'color': 'black',
    }

    machine_attributes = {
        'directed': True,
        'strict': False,
        'rankdir': 'LR',
        'ratio': '0.3'
    }

    def _add_nodes(self, states, container, initial_state=None):
        # For each state, draw a circle
        for state in states.keys():

            shape = self.default_state_attributes['shape']

            container.add_node(n=state, shape=shape)

    def _add_edges(self, events, container):
        # For each event, add an edge
        for event in events.items():
            event = event[1]
            label = str(event.name)

            for transitions in event.transitions.items():
                src = transitions[0]
                for t in transitions[1]:
                    dst = t.dest
                    container.add_edge(src, dst, label=label)

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

        fsm_graph = pgv.AGraph(label=title, **self.machine_attributes)
        fsm_graph.node_attr.update(self.default_state_attributes)

        # For each state, draw a circle
        self._add_nodes(self.machine.states, fsm_graph)

        self._add_edges(self.machine.events, fsm_graph)

        return fsm_graph
