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
        for state in self.machine.states.items():
            shape = self.state_attributes['shape']

            # We want the first state to be a double circle (UML style)
            if state == list(self.machine.states.items())[0]:
                shape = 'doublecircle'
            else:
                shape = self.state_attributes['shape']

            state = state[0]
            fsm_graph.add_node(n=state, shape=shape)

        fsm_graph.add_node('null', shape='plaintext', label='')
        fsm_graph.add_edge('null', 'new')

        # For each event, add the transitions
        for event in self.machine.events.items():
            event = event[1]
            label = str(event.name)

            for transition in event.transitions.items():
                src = transition[0]
                dst = transition[1][0].dest

                fsm_graph.add_edge(src, dst, label=label)

        return fsm_graph
