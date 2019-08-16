"""
    transitions.extensions.diagrams
    -------------------------------

    Graphviz support for (nested) machines. This also includes partial views
    of currently valid transitions.
"""

import logging
from functools import partial

from ..core import Transition
from .markup import MarkupMachine, rep
from .nesting import NestedState
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


class Graph(object):
    """ Graph creation for transitions.core.Machine.
        Attributes:
            machine_attributes (dict): Parameters for the general layout of the graph (flow direction, strict etc.)
            style_attributes (dict): Contains style parameters for nodes, edges and the graph
            machine (object): Reference to the related machine.
    """

    machine_attributes = {
        'directed': True,
        'strict': False,
        'rankdir': 'LR'
    }

    style_attributes = {
        'node': {
            'default': {
                'shape': 'rectangle',
                'style': 'rounded, filled',
                'fillcolor': 'white',
                'color': 'black',
                'peripheries': '1'

            },
            'active': {
                'color': 'red',
                'fillcolor': 'darksalmon',
                'peripheries': '2'
            },
            'previous': {
                'color': 'blue',
                'fillcolor': 'azure2',
                'peripheries': '1'
            }
        },
        'edge': {
            'default': {
                'color': 'black'
            },
            'previous': {
                'color': 'blue'
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

    def __init__(self, machine):
        self.machine = machine

    def _add_nodes(self, states, container):
        for state in states:
            shape = self.style_attributes['node']['default']['shape']
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

    def _transition_label(self, tran):
        edge_label = tran.get('label', tran['trigger'])
        if 'dest' not in tran:
            edge_label += " [internal]"
        if self.machine.show_conditions and any(prop in tran for prop in ['conditions', 'unless']):
            x = '{edge_label} [{conditions}]'.format(
                edge_label=edge_label,
                conditions=' & '.join(tran.get('conditions', []) + ['!' + u for u in tran.get('unless', [])]),
            )
            return x
        return edge_label

    def get_graph(self, title=None):
        """ Generate a DOT graph with pygraphviz, returns an AGraph object
        Args:
            title (string): Optional title for the graph.
        """
        if not pgv:  # pragma: no cover
            raise Exception('AGraph diagram requires pygraphviz')

        if title is False:
            title = ''

        fsm_graph = pgv.AGraph(label=title, compound=True, **self.machine_attributes)
        fsm_graph.node_attr.update(self.style_attributes['node']['default'])
        fsm_graph.edge_attr.update(self.style_attributes['edge']['default'])

        # For each state, draw a circle
        self._add_nodes(self.machine.markup.get('states', []), fsm_graph)
        self._add_edges(self.machine.markup.get('transitions', []), fsm_graph)

        setattr(fsm_graph, 'style_attributes', self.style_attributes)

        return fsm_graph

    def _convert_state_attributes(self, state):
        label = state.get('label', state['name'])
        if self.machine.show_state_attributes:
            if 'tags' in state:
                label += ' [' + ', '.join(state['tags']) + ']'
            if 'on_enter' in state:
                label += '\l- enter:\l  + ' + '\l  + '.join(state['on_enter'])
            if 'on_exit' in state:
                label += '\l- exit:\l  + ' + '\l  + '.join(state['on_exit'])
            if 'timeout' in state:
                label += '\l- timeout(' + state['timeout'] + 's)  -> (' + ', '.join(state['on_timeout']) + ')'
        return label


class NestedGraph(Graph):
    """ Graph creation support for transitions.extensions.nested.HierarchicalGraphMachine.
    Attributes:
        machine_attributes (dict): Same as Graph but extended with cluster/subgraph information
    """

    machine_attributes = Graph.machine_attributes.copy()
    machine_attributes.update(
        {'rank': 'source', 'rankdir': 'TB', 'nodesep': '1.5'})

    def __init__(self, *args, **kwargs):
        self.seen_transitions = []
        _super(NestedGraph, self).__init__(*args, **kwargs)
        # self.style_attributes['edge']['default']['minlen'] = 2

    def _add_nodes(self, states, container, prefix=''):
        for state in states:
            name = prefix + state['name']
            label = self._convert_state_attributes(state)

            if 'children' in state:
                cluster_name = "cluster_" + name
                sub = container.add_subgraph(name=cluster_name, label=label, rank='source',
                                             **self.style_attributes['graph']['default'])
                root_container = sub.add_subgraph(name=cluster_name + '_root', label='', color=None, rank='min')
                # child_container = sub.add_subgraph(name=cluster_name + '_child', label='', color=None)
                root_container.add_node(name + "_anchor", shape='point', fillcolor='black', width='0.1')
                self._add_nodes(state['children'], sub, prefix=prefix + state['name'] + NestedState.separator)
            else:
                container.add_node(name, label=label, shape=self.style_attributes['node']['default']['shape'])

    def _add_edges(self, transitions, container):

        # for sub in container.subgraphs_iter():
        #     events = self._add_edges(transitions, sub)

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


class TransitionGraphSupport(Transition):
    """ Transition used in conjunction with (Nested)Graphs to update graphs whenever a transition is
        conducted.
    """

    def _change_state(self, event_data):
        machine = event_data.machine
        model = event_data.model
        dest = machine.get_state(self.dest)
        graph = model.get_graph()

        # Mark the active node
        machine.reset_graph_style(graph)

        # Mark the previous node and path used
        if self.source is not None:
            source = machine.get_state(self.source)
            machine.set_node_state(graph, source.name, state='previous')
            machine.set_node_state(graph, dest.name, state='active')

            if getattr(source, 'children', []):
                source = source.name + '_anchor'
            else:
                source = source.name
            if getattr(dest, 'children', []):
                dest = dest.name + '_anchor'
            else:
                dest = dest.name
            machine.set_edge_state(graph, source, dest, state='previous', label=event_data.event.name)

        _super(TransitionGraphSupport, self)._change_state(event_data)  # pylint: disable=protected-access


class GraphMachine(MarkupMachine):
    """ Extends transitions.core.Machine with graph support.
        Is also used as a mixin for HierarchicalMachine.
        Attributes:
            _pickle_blacklist (list): Objects that should not/do not need to be pickled.
            transition_cls (cls): TransitionGraphSupport
    """

    _pickle_blacklist = ['model_graphs']
    graph_cls = Graph
    transition_cls = TransitionGraphSupport

    # model_graphs cannot be pickled. Omit them.
    def __getstate__(self):
        return {k: v for k, v in self.__dict__.items() if k not in self._pickle_blacklist}

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.model_graphs = {}  # reinitialize new model_graphs
        for model in self.models:
            try:
                graph = self._get_graph(model, title=self.title)
                self.set_node_style(graph, model.state, 'active')
            except AttributeError:
                _LOGGER.warning("Graph for model could not be initialized after pickling.")

    def __init__(self, *args, **kwargs):
        # remove graph config from keywords
        self.title = kwargs.pop('title', 'State Machine')
        self.show_conditions = kwargs.pop('show_conditions', False)
        self.show_state_attributes = kwargs.pop('show_state_attributes', False)
        # in MarkupMachine this switch is called 'with_auto_transitions'
        # keep 'show_auto_transitions' for backwards compatibility
        kwargs['with_auto_transitions'] = kwargs.pop('show_auto_transitions', False)
        self.model_graphs = {}
        _super(GraphMachine, self).__init__(*args, **kwargs)

        # Create graph at beginning
        for model in self.models:
            if hasattr(model, 'get_graph'):
                raise AttributeError('Model already has a get_graph attribute. Graph retrieval cannot be bound.')
            setattr(model, 'get_graph', partial(self._get_graph, model))
            model.get_graph()
            self.set_node_state(self.model_graphs[model], self.initial, 'active')

        # for backwards compatibility assign get_combined_graph to get_graph
        # if model is not the machine
        if not hasattr(self, 'get_graph'):
            setattr(self, 'get_graph', self.get_combined_graph)

    def _get_graph(self, model, title=None, force_new=False, show_roi=False):
        if force_new:
            self.model_graphs[model] = self.graph_cls(self).get_graph(title if title is not None else self.title)
            self.set_node_state(self.model_graphs[model], model.state, state='active')
        try:
            return self.model_graphs[model] if not show_roi else self._graph_roi(model)
        except KeyError:
            return self._get_graph(model, title, force_new=True, show_roi=show_roi)

    def get_combined_graph(self, title=None, force_new=False, show_roi=False):
        """ This method is currently equivalent to 'get_graph' of the first machine's model.
        In future releases of transitions, this function will return a combined graph with active states
        of all models.
        Args:
            title (str): Title of the resulting graph.
            force_new (bool): If set to True, (re-)generate the model's graph.
            show_roi (bool): If set to True, only render states that are active and/or can be reached from
                the current state.
        Returns: AGraph of the first machine's model.
        """
        _LOGGER.info('Returning graph of the first model. In future releases, this '
                     'method will return a combined graph of all models.')
        return self._get_graph(self.models[0], title, force_new, show_roi)

    def set_edge_state(self, graph, edge_from, edge_to, state='default', label=None):
        """ Retrieves/creates an edge between two states and changes the style/label.
        Args:
            graph (AGraph): The graph to be changed.
            edge_from (str): Source state of the edge.
            edge_to (str): Destination state of the edge.
            state (str): Style name (Should be part of the node style_attributes in Graph)
            label (str): Label of the edge.
        """
        # If show_auto_transitions is True, there will be an edge from 'edge_from' to 'edge_to'.
        # This test is considered faster than always calling 'has_edge'.
        if not self.with_auto_transitions and not graph.has_edge(edge_from, edge_to):
            graph.add_edge(edge_from, edge_to, label)
        edge = graph.get_edge(edge_from, edge_to)
        self.set_edge_style(graph, edge, state)

    def add_states(self, states, on_enter=None, on_exit=None,
                   ignore_invalid_triggers=None, **kwargs):
        """ Calls the base method and regenerates all models's graphs. """
        _super(GraphMachine, self).add_states(states, on_enter=on_enter, on_exit=on_exit,
                                              ignore_invalid_triggers=ignore_invalid_triggers, **kwargs)
        for model in self.models:
            model.get_graph(force_new=True)

    def add_transition(self, trigger, source, dest, conditions=None,
                       unless=None, before=None, after=None, prepare=None, **kwargs):
        """ Calls the base method and regenerates all models's graphs. """
        _super(GraphMachine, self).add_transition(trigger, source, dest, conditions=conditions, unless=unless,
                                                  before=before, after=after, prepare=prepare, **kwargs)
        for model in self.models:
            model.get_graph(force_new=True)

    def reset_graph_style(self, graph):
        """ This method resets the style of edges, nodes, and subgraphs to the 'default' parameters.
        Args:
            graph (AGraph): The graph to be reset.
        """
        # Reset all the edges
        for edge in graph.edges_iter():
            self.set_edge_style(graph, edge, 'default')
        for node in graph.nodes_iter():
            if 'point' not in node.attr['shape']:
                self.set_node_style(graph, node, 'default')
        for sub_graph in graph.subgraphs_iter():
            self.set_graph_style(graph, sub_graph, 'default')

    def set_node_state(self, graph, node_name, state='default'):
        """ Sets the style of a node or subgraph/cluster.
        Args:
            graph (AGraph): The graph to be altered.
            node_name (str): Name of a node or cluster (without cluster_-prefix).
            state (str): Style name (Should be part of the node style_attributes in Graph).
        """
        if graph.has_node(node_name):
            node = graph.get_node(node_name)
            func = self.set_node_style
        else:
            node = _get_subgraph(graph, 'cluster_' + node_name)
            func = self.set_graph_style
        func(graph, node, state)

    def _graph_roi(self, model):
        graph = model.get_graph()
        filtered = graph.copy()

        kept_nodes = set()
        active_state = model.state if graph.has_node(model.state) else model.state + '_anchor'
        kept_nodes.add(active_state)

        # remove all edges that have no connection to the currently active state
        for edge in filtered.edges():
            if active_state not in edge:
                filtered.delete_edge(edge)

        # find the ingoing edge by color; remove the rest
        for edge in filtered.in_edges(active_state):
            if edge.attr['color'] == graph.style_attributes['edge']['previous']['color']:
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

    @staticmethod
    def set_node_style(graph, node_name, style='default'):
        """ Sets the style of a node.
        Args:
            graph (AGraph): Graph containing the relevant styling attributes.
            node_name (str): Name of a node.
            style (str): Style name (Should be part of the node style_attributes in Graph).
        """
        node = graph.get_node(node_name)
        style_attr = graph.style_attributes.get('node', {}).get(style)
        node.attr.update(style_attr)

    @staticmethod
    def set_edge_style(graph, edge, style='default'):
        """ Sets the style of an edge.
        Args:
            graph (AGraph): Graph containing the relevant styling attributes.
            edge (Edge): Edge to be altered.
            style (str): Style name (Should be part of the edge style_attributes in Graph).
        """
        style_attr = graph.style_attributes.get('edge', {}).get(style)
        edge.attr.update(style_attr)

    @staticmethod
    def set_graph_style(graph, item, style='default'):
        """ Sets the style of a (sub)graph/cluster.
        Args:
            graph (AGraph): Graph containing the relevant styling attributes.
            item (AGraph): Item to be altered.
            style (str): Style name (Should be part of the graph style_attributes in Graph).
        """
        style_attr = graph.style_attributes.get('graph', {}).get(style)
        item.graph_attr.update(style_attr)


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
