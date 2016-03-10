from ..core import Transition, Machine
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
                    lbl = self._transition_label(label, t)
                    container.add_edge(src, dst, label=lbl)

    def _transition_label(self, edge_label, tran):
        if self.machine.show_conditions and tran.conditions:
            return '{edge_label} [{conditions}]'.format(
                edge_label=edge_label,
                conditions=' & '.join(
                    c.func if c.target else '!' + c.func
                    for c in tran.conditions
                ),
            )
        return edge_label

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


class AAGraph(AGraph):

    def __init__(self, *args, **kwargs):
        self.seen = []
        super(AAGraph, self).__init__(*args, **kwargs)

    def _add_nodes(self, states, container):
        # to be able to process children recursively as well as the state dict of a machine
        states = states.values() if isinstance(states, dict) else states
        for state in states:
            if state.name in self.seen:
                continue
            elif hasattr(state, 'children') and state.children is not None:
                self.seen.append(state.name)
                sub = container.add_subgraph(name="cluster_" + state.name, label=state.name)
                self._add_nodes(state.children, sub)
            else:
                try:
                    shape = self.style_attributes['node']['default']['shape']
                except KeyError:
                    shape = 'circle'

                state = state.name
                self.seen.append(state)
                container.add_node(n=state, shape=shape)

    def _add_edges(self, events, sub):
        for event in events.items():
            event = event[1]
            label = str(event.name)

            for transitions in event.transitions.items():
                src = transitions[0]
                for t in transitions[1]:
                    dst = self.machine.get_state(t.dest)
                    if hasattr(dst, 'children') and dst.children is not None:
                        dst = dst.get_initial().name
                    else:
                        dst = dst.name
                    lbl = self._transition_label(label, t)
                    sub.add_edge(src, dst, label=lbl)


class MachineGraphSupport(Machine):
    _pickle_blacklist = ['graph']

    def __getstate__(self):
        return {k: v for k, v in self.__dict__.items() if k not in self._pickle_blacklist}

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.graph = self.get_graph(title=self.title)
        self.set_node_style(self.graph.get_node(self.current_state.name), 'active')

    def __init__(self, *args, **kwargs):
        # remove graph config from keywords
        title = kwargs.pop('title', 'State Machine')
        show_conditions = kwargs.pop('show_conditions', False)
        super(MachineGraphSupport, self).__init__(*args, **kwargs)

        # Create graph at beginnning
        self.show_conditions = show_conditions
        self.title = title
        self.graph = self.get_graph(title=title)

        # Set initial node as active
        self.set_node_style(self.graph.get_node(self.initial), 'active')

    def get_graph(self, title=None, diagram_class=AAGraph, force_new=False):
        if not hasattr(self, 'graph') or force_new:
            self.graph = diagram_class(self).get_graph(title)

        return self.graph

    def set_edge_state(self, edge_from, edge_to, state='default'):
        """ Mark a node as active by changing the attributes """
        assert hasattr(self, 'graph')

        edge = self.graph.get_edge(edge_from, edge_to)

        # Reset all the edges
        for e in self.graph.edges_iter():
            self.set_edge_style(e, 'default')

        try:
            self.set_edge_style(edge, state)
        except KeyError:
            self.set_edge_style(edge, 'default')

    def set_node_state(self, node_name=None, state='default', reset=False):
        assert hasattr(self, 'graph')

        if node_name is None:
            node_name = self.state

        if reset:
            for n in self.graph.nodes_iter():
                self.set_node_style(n, 'default')

        node = self.graph.get_node(node_name)
        try:
            self.set_node_style(node, state)
        except KeyError:
            self.set_node_style(node, 'default')

    def set_node_style(self, item, style='default'):
        style_attr = self.graph.style_attributes.get('node', {}).get(style)
        item.attr.update(style_attr)

    def set_edge_style(self, item, style='default'):
        style_attr = self.graph.style_attributes.get('edge', {}).get(style)
        item.attr.update(style_attr)

    @staticmethod
    def _create_transition(*args, **kwargs):
        return TransitionGraphSupport(*args, **kwargs)


class TransitionGraphSupport(Transition):

    def _change_state(self, event_data):

        # Mark the active node
        dest = event_data.machine.get_state(self.dest)
        dest = dest.name if not hasattr(dest, 'children') else dest.get_initial().name
        event_data.machine.set_node_state(dest, state='active', reset=True)

        # Mark the previous node and path used
        if self.source is not None:
            event_data.machine.set_node_state(self.source, state='previous')
            event_data.machine.set_edge_state(self.source, dest, state='previous')

        super(TransitionGraphSupport, self)._change_state(event_data)
