import abc

from ..core import Machine, listify
from ..core import Transition
from .nesting import NestedState
try:
    import pygraphviz as pgv
except:
    pgv = None

import logging
from functools import partial
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class Diagram(object):

    def __init__(self, machine):
        self.machine = machine

    @abc.abstractmethod
    def get_graph(self):
        raise Exception('Abstract base Diagram.get_graph called!')


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
                sub = container.add_subgraph(name="cluster_" + state.name,
                                             label=state.name, rank='same', color='black')
                self._add_nodes(state.children, sub)
            else:
                shape = self.style_attributes['node']['default']['shape']
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
                        src = src.children[0]

                for t in transitions[1]:
                    dst = self.machine.get_state(t.dest)
                    edge_label = self._transition_label(label, t)
                    lhead = ''

                    if hasattr(dst, 'children') and len(dst.children) > 0:
                        lhead = 'cluster_' + dst.name
                        dst = dst.children[0]
                        while len(dst.children) > 0:
                            dst = dst.children[0]

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

        if title is False:
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
        for model in self.models:
            graph = self._get_graph(model, title=self.title)
            self.set_node_style(graph, model.state, 'active')

    def __init__(self, *args, **kwargs):
        # remove graph config from keywords
        self.title = kwargs.pop('title', 'State Machine')
        self.show_conditions = kwargs.pop('show_conditions', False)
        super(GraphMachine, self).__init__(*args, **kwargs)

        # Create graph at beginning
        for model in self.models:
            if hasattr(model, 'get_graph'):
                raise AttributeError('Model already has a get_graph attribute. Graph retrieval cannot be bound.')
            setattr(model, 'get_graph', partial(self._get_graph, model))
            model.get_graph()
            self.set_node_state(model.graph, self.initial, 'active')

        # for backwards compatibility assign get_combined_graph to get_graph
        # if model is not the machine
        if not hasattr(self, 'get_graph'):
            setattr(self, 'get_graph', self.get_combined_graph)

    def _get_graph(self, model, title=None, force_new=False):
        if title is None:
            title = self.title
        if not hasattr(model, 'graph') or force_new:
            model.graph = AGraph(self).get_graph(title)
        return model.graph

    def get_combined_graph(self, title=None, force_new=False):
        logger.info('Returning graph of the first model. In future releases, this ' +
                    'method will return a combined graph of all models.')
        return self._get_graph(next(iter(self.models)), title, force_new)

    def set_edge_state(self, graph, edge_from, edge_to, state='default'):
        """ Mark a node as active by changing the attributes """
        edge = graph.get_edge(edge_from, edge_to)

        # Reset all the edges
        for e in graph.edges_iter():
            self.set_edge_style(graph, e, 'default')
        self.set_edge_style(graph, edge, state)

    def add_states(self, *args, **kwargs):
        super(GraphMachine, self).add_states(*args, **kwargs)
        for model in self.models:
            if hasattr(model, 'graph'):
                model.get_graph(force_new=True)

    def add_transition(self, *args, **kwargs):
        super(GraphMachine, self).add_transition(*args, **kwargs)
        for model in self.models:
            if hasattr(model, 'graph'):
                model.get_graph(force_new=True)

    def set_node_state(self, graph, node_name, state='default', reset=False):
        if reset:
            for n in graph.nodes_iter():
                self.set_node_style(graph, n, 'default')
        if graph.has_node(node_name):
            node = graph.get_node(node_name)
            func = self.set_node_style
        else:
            node = graph
            path = node_name.split(NestedState.separator)
            # A subgraph cannot be retrieved from another nested subgraph.
            # We have to traverse through the whole tree.
            # From cluster_parent to cluster_parent_child1 to cluster_parent_child1_child2 and so on
            current_path = 'cluster_' + path.pop(0)
            node = node.get_subgraph(current_path)
            while len(path) > 0:
                current_path += NestedState.separator + path.pop(0)
                node = node.get_subgraph(current_path)
            func = self.set_graph_style
        func(graph, node, state)

    @staticmethod
    def set_node_style(graph, node_name, style='default'):
        node = graph.get_node(node_name)
        style_attr = graph.style_attributes.get('node', {}).get(style)
        node.attr.update(style_attr)

    @staticmethod
    def set_edge_style(graph, edge, style='default'):
        style_attr = graph.style_attributes.get('edge', {}).get(style)
        edge.attr.update(style_attr)

    @staticmethod
    def set_graph_style(graph, item, style='default'):
        style_attr = graph.style_attributes.get('node', {}).get(style)
        item.graph_attr.update(style_attr)

    @staticmethod
    def _create_transition(*args, **kwargs):
        return TransitionGraphSupport(*args, **kwargs)


class TransitionGraphSupport(Transition):

    def _change_state(self, event_data):
        machine = event_data.machine
        model = event_data.model
        dest = machine.get_state(self.dest)

        # Mark the previous node and path used
        if self.source is not None:
            source = machine.get_state(self.source)
            machine.set_node_state(model.graph, source.name,
                                   state='previous')

            if hasattr(source, 'children'):
                while len(source.children) > 0:
                    source = source.children[0]
                while len(dest.children) > 0:
                    dest = dest.children[0]
            if model.graph.has_edge(source.name, dest.name):
                machine.set_edge_state(model.graph, source.name,
                                       dest.name, state='previous')

        # Mark the active node
        machine.set_node_state(model.graph, dest.name,
                               state='active', reset=True)

        super(TransitionGraphSupport, self)._change_state(event_data)
