import abc

from ..core import Machine
from ..core import Transition
from .nesting import NestedState
try:
    import pygraphviz as pgv
except:
    pgv = None

import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


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

    def __init__(self, *args, **kwargs):
        self.seen = []
        super(AGraph, self).__init__(*args, **kwargs)

    def _add_nodes(self, states, container):
        # to be able to process children recursively as well as the state dict of a machine
        states = states.values() if isinstance(states, dict) else states
        for state in states:
            if state.name in self.seen:
                continue
            elif hasattr(state, 'children') and len(state.children) > 0:
                self.seen.append(state.name)
                sub = container.add_subgraph(name="cluster_" + state._name, label=state.name, rank='same')
                self._add_nodes(state.children, sub)
            else:
                try:
                    shape = self.style_attributes['node']['default']['shape']
                except KeyError:
                    shape = 'circle'

                self.seen.append(state.name)
                container.add_node(n=state.name, shape=shape)

    def _add_edges(self, events, container):
        for event in events.values():
            label = str(event.name)

            for transitions in event.transitions.items():
                src = self.machine.get_state(transitions[0])
                ltail = ''
                if hasattr(src, 'children') and len(src.children) > 0:
                    ltail = 'cluster_' + src.name
                    src = src.children[0]
                    while len(src.children) > 0:
                        src = src.children

                for t in transitions[1]:
                    dst = self.machine.get_state(t.dest)
                    edge_label = self._transition_label(label, t)
                    lhead = ''

                    if hasattr(dst, 'children') and len(dst.children) > 0:
                        lhead = 'cluster_' + dst.name
                        dst = dst.children[0]
                        while len(dst.children) > 0:
                            dst = src.children

                    # special case in which parent to first child edge is resolved to a self reference.
                    # will be omitted for now. I have not found a solution for how to fix this yet since having
                    # cluster to node edges is a bit messy with dot.
                    if dst.name == src.name and transitions[0] != t.dest:
                        continue
                    elif container.has_edge(src.name, dst.name):
                        edge = container.get_edge(src.name, dst.name)
                        edge.attr['label'] = edge.attr['label'] + ' | ' + edge_label
                    else:
                        container.add_edge(src.name, dst.name, label=edge_label, ltail=ltail, lhead=lhead)

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

        fsm_graph = pgv.AGraph(label=title, compound=True, **self.machine_attributes)
        fsm_graph.node_attr.update(self.style_attributes['node']['default'])

        # For each state, draw a circle
        self._add_nodes(self.machine.states, fsm_graph)

        self._add_edges(self.machine.events, fsm_graph)

        setattr(fsm_graph, 'style_attributes', self.style_attributes)

        return fsm_graph


class GraphMachine(Machine):
    _pickle_blacklist = ['graph']

    def __getstate__(self):
        return {k: v for k, v in self.__dict__.items() if k not in self._pickle_blacklist}

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.graph = self.get_graph(title=self.title)
        self.set_node_style(self.graph.get_node(self.current_state.name), 'active')

    def __init__(self, *args, **kwargs):
        # remove graph config from keywords
        self.title = kwargs.pop('title', 'State Machine')
        self.show_conditions = kwargs.pop('show_conditions', False)
        super(GraphMachine, self).__init__(*args, **kwargs)

        # Create graph at beginning
        self.graph = self.get_graph(title=self.title)

        # Set initial node as active
        self.set_node_state(self.initial, 'active')

    def get_graph(self, title=None, force_new=False):
        if title is None:
            title = self.title
        if not hasattr(self, 'graph') or force_new:
            self.graph = AGraph(self).get_graph(title)

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

    def add_states(self, *args, **kwargs):
        super(GraphMachine, self).add_states(*args, **kwargs)
        self.graph = self.get_graph(force_new=True)

    def add_transition(self, *args, **kwargs):
        super(GraphMachine, self).add_transition(*args, **kwargs)
        self.graph = self.get_graph(force_new=True)

    def set_node_state(self, node_name=None, state='default', reset=False):
        assert hasattr(self, 'graph')

        if node_name is None:
            node_name = self.state

        if reset:
            for n in self.graph.nodes_iter():
                self.set_node_style(n, 'default')
        if self.graph.has_node(node_name):
            node = self.graph.get_node(node_name)
            func = self.set_node_style
        else:
            path = node_name.split(NestedState.separator)
            node = self.graph
            while len(path) > 0:
                node = node.get_subgraph('cluster_' + path.pop(0))
            func = self.set_graph_style
        try:
            func(node, state)
        except KeyError:
            func(node, 'default')

    def set_node_style(self, item, style='default'):
        style_attr = self.graph.style_attributes.get('node', {}).get(style)
        item.attr.update(style_attr)

    def set_edge_style(self, item, style='default'):
        style_attr = self.graph.style_attributes.get('edge', {}).get(style)
        item.attr.update(style_attr)

    def set_graph_style(self, item, style='default'):
        style_attr = self.graph.style_attributes.get('node', {}).get(style)
        item.graph_attr.update(style_attr)

    @staticmethod
    def _create_transition(*args, **kwargs):
        return TransitionGraphSupport(*args, **kwargs)


class TransitionGraphSupport(Transition):

    def _change_state(self, event_data):

        # Mark the active node
        dest = event_data.machine.get_state(self.dest)
        event_data.machine.set_node_state(dest.name, state='active', reset=True)

        # Mark the previous node and path used
        if self.source is not None:
            source = event_data.machine.get_state(self.source)

            event_data.machine.set_node_state(source.name, state='previous')

            if hasattr(source, 'children'):
                while len(source.children) > 0:
                    source = source.children[0]
                while len(dest.children) > 0:
                    dest = dest.children[0]
            event_data.machine.set_edge_state(source.name, dest.name, state='previous')
        super(TransitionGraphSupport, self)._change_state(event_data)
