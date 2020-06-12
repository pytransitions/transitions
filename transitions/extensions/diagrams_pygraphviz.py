"""
    transitions.extensions.diagrams
    -------------------------------

    Graphviz support for (nested) machines. This also includes partial views
    of currently valid transitions.
"""

import logging
import copy

from .nesting import NestedState
from .diagrams import BaseGraph

try:
    import pygraphviz as pgv
except ImportError:  # pragma: no cover
    pgv = None

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())

# this is a workaround for dill issues when partials and super is used in conjunction
# without it, Python 3.0 - 3.3 will not support pickling
# https://github.com/pytransitions/transitions/issues/236
_super = super


class Graph(BaseGraph):
    """ Graph creation for transitions.core.Machine.
        Attributes:
            machine (object): Reference to the related machine.
    """

    def _add_nodes(self, states, container):
        for state in states:
            shape = self.machine.style_attributes['node']['default']['shape']
            container.add_node(state['name'], label=self._convert_state_attributes(state), shape=shape)

    def _add_edges(self, transitions, container):
        for transition in transitions:
            src = transition['source']
            edge_attr = {'label': self._transition_label(transition)}
            try:
                dst = transition['dest']
            except KeyError:
                dst = src
            if container.has_edge(src, dst):
                edge = container.get_edge(src, dst)
                edge.attr['label'] = edge.attr['label'] + ' | ' + edge_attr['label']
            else:
                container.add_edge(src, dst, **edge_attr)

    def generate(self, title=None):
        """ Generate a DOT graph with pygraphviz, returns an AGraph object """
        if not pgv:  # pragma: no cover
            raise Exception('AGraph diagram requires pygraphviz')

        title = '' if not title else title

        self.fsm_graph = pgv.AGraph(label=title, **self.machine.machine_attributes)
        self.fsm_graph.node_attr.update(self.machine.style_attributes['node']['default'])
        self.fsm_graph.edge_attr.update(self.machine.style_attributes['edge']['default'])
        states, transitions = self._get_elements()
        self._add_nodes(states, self.fsm_graph)
        self._add_edges(transitions, self.fsm_graph)
        setattr(self.fsm_graph, 'style_attributes', self.machine.style_attributes)

        return self.fsm_graph

    def get_graph(self, title=None):
        if title:
            self.fsm_graph.graph_attr['label'] = title
        if self.roi_state:
            filtered = self.fsm_graph.copy()
            kept_nodes = set()
            active_state = self.roi_state if filtered.has_node(self.roi_state) else self.roi_state + '_anchor'
            kept_nodes.add(active_state)

            # remove all edges that have no connection to the currently active state
            for edge in filtered.edges():
                if active_state not in edge:
                    filtered.delete_edge(edge)

            # find the ingoing edge by color; remove the rest
            for edge in filtered.in_edges(active_state):
                if edge.attr['color'] == self.fsm_graph.style_attributes['edge']['previous']['color']:
                    kept_nodes.add(edge[0])
                else:
                    filtered.delete_edge(edge)

            # remove outgoing edges from children
            for edge in filtered.out_edges_iter(active_state):
                kept_nodes.add(edge[1])

            for node in filtered.nodes():
                if node not in kept_nodes:
                    filtered.delete_node(node)

            return filtered
        else:
            return self.fsm_graph

    def set_node_style(self, state, style):
        node = self.fsm_graph.get_node(state)
        style_attr = self.fsm_graph.style_attributes.get('node', {}).get(style)
        node.attr.update(style_attr)

    def set_previous_transition(self, src, dst, key=None):
        try:
            edge = self.fsm_graph.get_edge(src, dst)
        except KeyError:
            self.fsm_graph.add_edge(src, dst)
            edge = self.fsm_graph.get_edge(src, dst)
        style_attr = self.fsm_graph.style_attributes.get('edge', {}).get('previous')
        edge.attr.update(style_attr)
        self.set_node_style(src, 'previous')
        self.set_node_style(dst, 'active')

    def reset_styling(self):
        for edge in self.fsm_graph.edges_iter():
            style_attr = self.fsm_graph.style_attributes.get('edge', {}).get('default')
            edge.attr.update(style_attr)
        for node in self.fsm_graph.nodes_iter():
            if 'point' not in node.attr['shape']:
                style_attr = self.fsm_graph.style_attributes.get('node', {}).get('default')
                node.attr.update(style_attr)
        for sub_graph in self.fsm_graph.subgraphs_iter():
            style_attr = self.fsm_graph.style_attributes.get('graph', {}).get('default')
            sub_graph.graph_attr.update(style_attr)


class NestedGraph(Graph):
    """ Graph creation support for transitions.extensions.nested.HierarchicalGraphMachine. """

    def __init__(self, *args, **kwargs):
        self.seen_transitions = []
        _super(NestedGraph, self).__init__(*args, **kwargs)
        # self.style_attributes['edge']['default']['minlen'] = 2

    def _add_nodes(self, states, container, prefix='', default_style='default'):
        for state in states:
            name = prefix + state['name']
            label = self._convert_state_attributes(state)

            if 'children' in state:
                cluster_name = "cluster_" + name
                is_parallel = isinstance(state.get('initial', ''), list)
                sub = container.add_subgraph(name=cluster_name, label=label, rank='source',
                                             **self.machine.style_attributes['graph'][default_style])
                root_container = sub.add_subgraph(name=cluster_name + '_root', label='', color=None, rank='min')
                width = '0' if is_parallel else '0.1'
                root_container.add_node(name + "_anchor", shape='point', fillcolor='black', width=width)
                self._add_nodes(state['children'], sub, prefix=prefix + state['name'] + NestedState.separator,
                                default_style='parallel' if is_parallel else 'default')
            else:
                container.add_node(name, label=label, **self.machine.style_attributes['node'][default_style])

    def _add_edges(self, transitions, container):

        for transition in transitions:
            # enable customizable labels
            label_pos = 'label'
            src = transition['source']
            try:
                dst = transition['dest']
            except KeyError:
                dst = src
            edge_attr = {}
            if _get_subgraph(container, 'cluster_' + src) is not None:
                edge_attr['ltail'] = 'cluster_' + src
                src_name = src + "_anchor"
                label_pos = 'headlabel'
            else:
                src_name = src

            dst_graph = _get_subgraph(container, 'cluster_' + dst)
            if dst_graph is not None:
                if not src.startswith(dst):
                    edge_attr['lhead'] = "cluster_" + dst
                    label_pos = 'taillabel' if label_pos.startswith('l') else 'label'
                dst_name = dst + '_anchor'
            else:
                dst_name = dst

            # remove ltail when dst is a child of src
            if 'ltail' in edge_attr:
                if _get_subgraph(container, edge_attr['ltail']).has_node(dst_name):
                    del edge_attr['ltail']

            edge_attr[label_pos] = self._transition_label(transition)
            if container.has_edge(src_name, dst_name):
                edge = container.get_edge(src_name, dst_name)
                edge.attr[label_pos] += ' | ' + edge_attr[label_pos]
            else:
                container.add_edge(src_name, dst_name, **edge_attr)

    def set_node_style(self, state, style):
        try:
            node = self.fsm_graph.get_node(state)
            style_attr = self.fsm_graph.style_attributes.get('node', {}).get(style)
            node.attr.update(style_attr)
        except KeyError:
            subgraph = _get_subgraph(self.fsm_graph, 'cluster_' + state)
            style_attr = self.fsm_graph.style_attributes.get('graph', {}).get(style)
            subgraph.graph_attr.update(style_attr)

    def set_previous_transition(self, src, dst, key=None):
        src = self._get_global_name(src.split(self.machine.state_cls.separator))
        dst = self._get_global_name(dst.split(self.machine.state_cls.separator))
        edge_attr = self.fsm_graph.style_attributes.get('edge', {}).get('previous').copy()
        try:
            edge = self.fsm_graph.get_edge(src, dst)
        except KeyError:
            _src = src
            _dst = dst
            if _get_subgraph(self.fsm_graph, 'cluster_' + src):
                edge_attr['ltail'] = 'cluster_' + src
                _src += '_anchor'
            if _get_subgraph(self.fsm_graph, 'cluster_' + dst):
                edge_attr['lhead'] = "cluster_" + dst
                _dst += '_anchor'
            try:
                edge = self.fsm_graph.get_edge(_src, _dst)
            except KeyError:
                self.fsm_graph.add_edge(_src, _dst)
                edge = self.fsm_graph.get_edge(_src, _dst)

        edge.attr.update(edge_attr)
        self.set_node_style(src, 'previous')


def _get_subgraph(graph, name):
    """ Searches for subgraphs in a graph.
    Args:
        g (AGraph): Container to be searched.
        name (str): Name of the cluster.
    Returns: AGraph if a cluster called 'name' exists else None
    """
    sub_graph = graph.get_subgraph(name)
    if sub_graph:
        return sub_graph
    for sub in graph.subgraphs_iter():
        sub_graph = _get_subgraph(sub, name)
        if sub_graph:
            return sub_graph
    return None
