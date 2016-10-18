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
        'ratio': '0.3',
        'clusterrank': 'local'
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
        },
        'graph': {
            'default': {
                'color': 'black',
                'fillcolor': 'white'
            },
            'previous': {
                'color': 'blue',
                'fillcolor': 'azure2',
                'style': 'filled'
            },
            'active': {
                'color': 'red',
                'fillcolor': 'darksalmon',
                'style': 'filled'
            },
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
                sub = container.add_subgraph(name="cluster_" + state._name, label=state.name,
                                             **AGraph.style_attributes['graph']['default'])
                anchor_name = "cluster_" + state._name + "_anchor"
                sub.add_node(anchor_name, shape='point', fillcolor='black', width='0.1')
                self._add_nodes(state.children, sub)
            else:
                shape = self.style_attributes['node']['default']['shape']
                self.seen.append(state.name)
                container.add_node(n=state.name, shape=shape)

    def _add_edges(self, events, container):
        for event in events.values():
            label = str(event.name)
            if not self.machine.show_auto_transitions and label.startswith('to_')\
                    and len(event.transitions) == len(self.machine.states):
                continue

            for transitions in event.transitions.items():
                src = self.machine.get_state(transitions[0])
                edge_attr = {}
                if hasattr(src, 'children') and len(src.children) > 0:
                    #edge_attr['ltail'] = 'cluster_' + src._name
                    src = 'cluster_' + src._name + "_anchor"
                else:
                    src = src.name
                for t in transitions[1]:
                    dst = self.machine.get_state(t.dest)
                    edge_attr['label'] = self._transition_label(label, t)
                    if hasattr(dst, 'children') and len(dst.children) > 0:
                        #edge_attr['lhead'] = 'cluster_' + dst.name
                        dst = 'cluster_' + dst.name + "_anchor"
                    else:
                        dst = dst.name

                    if container.has_edge(src, dst):
                        edge = container.get_edge(src, dst)
                        edge.attr['label'] = edge.attr['label'] + ' | ' + edge_attr['label']
                    else:
                        container.add_edge(src, dst, **edge_attr)

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
            show_roi (boolean): Show only the active region in a graph
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
        self.show_auto_transitions = kwargs.pop('show_auto_transitions', False)

        # temporally disable overwrites since graphing cannot
        # be initialized before base machine
        add_states = self.add_states
        add_transition = self.add_transition
        self.add_states = super(GraphMachine, self).add_states
        self.add_transition = super(GraphMachine, self).add_transition

        super(GraphMachine, self).__init__(*args, **kwargs)
        self.add_states = add_states
        self.add_transition = add_transition

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

    def _get_graph(self, model, title=None, force_new=False, show_roi=False):
        if title is None:
            title = self.title
        if not hasattr(model, 'graph') or force_new:
            model.graph = AGraph(self).get_graph(title)
            self.set_node_state(model.graph, model.state, state='active')

        return model.graph if not show_roi else self._graph_roi(model)

    def get_combined_graph(self, title=None, force_new=False, show_roi=False):
        logger.info('Returning graph of the first model. In future releases, this ' +
                    'method will return a combined graph of all models.')
        return self._get_graph(self.models[0], title, force_new, show_roi)

    def set_edge_state(self, graph, edge_from, edge_to, state='default', label=None):
        """ Mark a node as active by changing the attributes """
        if not self.show_auto_transitions and not graph.has_edge(edge_from, edge_to):
            graph.add_edge(edge_from, edge_to, label)
        edge = graph.get_edge(edge_from, edge_to)
        self.set_edge_style(graph, edge, state)

    def add_states(self, *args, **kwargs):
        super(GraphMachine, self).add_states(*args, **kwargs)
        for model in self.models:
            model.get_graph(force_new=True)

    def add_transition(self, *args, **kwargs):
        super(GraphMachine, self).add_transition(*args, **kwargs)
        for model in self.models:
            model.get_graph(force_new=True)

    def reset_graph(self, graph):
        # Reset all the edges
        for e in graph.edges_iter():
            self.set_edge_style(graph, e, 'default')
        for n in graph.nodes_iter():
            if 'point' not in n.attr['shape']:
                self.set_node_style(graph, n, 'default')
        for g in graph.subgraphs_iter():
            self.set_graph_style(graph, g, 'default')

    def set_node_state(self, graph, node_name, state='default'):
        if graph.has_node(node_name):
            node = graph.get_node(node_name)
            func = self.set_node_style
        else:
            node = graph
            path = node_name.split(NestedState.separator)
            while len(path) > 0:
                node = node.get_subgraph('cluster_' + path.pop(0))
            func = self.set_graph_style
        func(graph, node, state)

    @staticmethod
    def _graph_roi(model):
        g = model.graph
        filtered = g.copy()

        kept_nodes = set()
        active_state = model.state if g.has_node(model.state) else 'cluster_' + model.state + '_anchor'
        kept_nodes.add(active_state)

        # remove all edges that have no connection to the currently active state
        for e in filtered.edges():
            if active_state not in e:
                filtered.delete_edge(e)

        # find the ingoing edge by color; remove the rest
        for e in filtered.in_edges(active_state):
            if e.attr['color'] == AGraph.style_attributes['edge']['previous']['color']:
                kept_nodes.add(e[0])
            else:
                filtered.delete_edge(e)

        # remove outgoing edges from children
        for e in filtered.out_edges_iter(active_state):
            kept_nodes.add(e[1])

        for n in filtered.nodes():
            if n not in kept_nodes:
                filtered.delete_node(n)

        return filtered

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
        style_attr = graph.style_attributes.get('graph', {}).get(style)
        item.graph_attr.update(style_attr)

    @staticmethod
    def _create_transition(*args, **kwargs):
        return TransitionGraphSupport(*args, **kwargs)


class TransitionGraphSupport(Transition):

    def _change_state(self, event_data):
        machine = event_data.machine
        model = event_data.model
        dest = machine.get_state(self.dest)

        # Mark the active node
        machine.reset_graph(model.graph)

        # Mark the previous node and path used
        if self.source is not None:
            source = machine.get_state(self.source)
            machine.set_node_state(model.graph, source.name,
                                   state='previous')
            machine.set_node_state(model.graph, dest.name, state='active')

            if hasattr(source, 'children') and len(source.children) > 0:
                source = 'cluster_' + source.name + '_anchor'
            else:
                source = source.name
            if hasattr(dest, 'children') and len(dest.children) > 0:
                dest = 'cluster_' + dest.name + '_anchor'
            else:
                dest = dest.name
            machine.set_edge_state(model.graph, source, dest,
                                   state='previous', label=event_data.event.name)

        super(TransitionGraphSupport, self)._change_state(event_data)
