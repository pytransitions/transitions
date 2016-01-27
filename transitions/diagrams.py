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

    machine_attributes = {
        'directed': True,
        'strict': False,
        'rankdir': 'LR',
        'ratio': '0.3'
    }

    style_attributes = {
        'node': {
            'default': {
                'shape': 'circle',
                'height': '1.2',
                'style': 'filled',
                'fillcolor': 'white',
                'color': 'black',
            },
            'active': {
                'color': 'red',
                'fillcolor': 'darksalmon',
                'shape': 'doublecircle'
            },
            'previous': {
                'color': 'blue',
                'fillcolor': 'azure2',
            }
        },
        'edge': {
            'default': {
                'color': 'black',

            },
            'previous': {
                'color': 'blue',

            }
        }
    }

    def _add_nodes(self, states, container, initial_state=None):
        # For each state, draw a circle
        for state in states.keys():

            shape = self.style_attributes['state']['default']['shape']

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
        fsm_graph.node_attr.update(self.style_attributes['node']['default'])

        # For each state, draw a circle
        self._add_nodes(self.machine.states, fsm_graph)

        self._add_edges(self.machine.events, fsm_graph)

        setattr(fsm_graph, 'style_attributes', self.style_attributes)

        return fsm_graph
