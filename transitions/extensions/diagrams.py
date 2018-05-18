"""
    transitions.extensions.diagrams
    -------------------------------

    Graphviz support for (nested) machines. This also includes partial views
    of currently valid transitions.
"""

import logging
from functools import partial
import itertools
from six import string_types, iteritems

from ..core import Machine
from ..core import Transition
from .nesting import HierarchicalMachine
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


def rep(func):
    """ Return a string representation for `func`. """
    if isinstance(func, string_types):
        return func
    try:
        return func.__name__
    except AttributeError:
        pass
    if isinstance(func, partial):
        return "%s(%s)" % (
            func.func.__name__,
            ", ".join(itertools.chain(
                (str(_) for _ in func.args),
                ("%s=%s" % (key, value)
                 for key, value in iteritems(func.keywords if func.keywords else {})))))
    return str(func)


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
        'rankdir': 'LR',
        'ratio': '0.3',
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
            container.add_node(state, shape=shape)

    def _add_edges(self, events, container):
        for event in events.values():
            label = str(event.name)
            if self._omit_auto_transitions(event, label):
                continue

            for transitions in event.transitions.items():
                src = transitions[0]
                edge_attr = {}
                for trans in transitions[1]:
                    if trans.dest is None:
                        dst = src
                        label += " [internal]"
                    else:
                        dst = trans.dest
                    edge_attr['label'] = self._transition_label(label, trans)
                    if container.has_edge(src, dst):
                        edge = container.get_edge(src, dst)
                        edge.attr['label'] = edge.attr['label'] + ' | ' + edge_attr['label']
                    else:
                        container.add_edge(src, dst, **edge_attr)

    def _omit_auto_transitions(self, event, label):
        return self._is_auto_transition(event, label) and not self.machine.show_auto_transitions

    # auto transition events commonly a) start with the 'to_' prefix, followed by b) the state name
    # and c) contain a transition from each state to the target state (including the target)
    def _is_auto_transition(self, event, label):
        if label.startswith('to_') and len(event.transitions) == len(self.machine.states):
            state_name = label[len('to_'):]
            if state_name in self.machine.states:
                return True
        return False

    def _transition_label(self, edge_label, tran):
        if self.machine.show_conditions and tran.conditions:
            return '{edge_label} [{conditions}]'.format(
                edge_label=edge_label,
                conditions=' & '.join(
                    rep(c.func) if c.target else '!' + rep(c.func)
                    for c in tran.conditions
                ),
            )
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
        self._add_nodes(self.machine.states, fsm_graph)
        self._add_edges(self.machine.events.copy(), fsm_graph)

        setattr(fsm_graph, 'style_attributes', self.style_attributes)

        return fsm_graph


class NestedGraph(Graph):
    """ Graph creation support for transitions.extensions.nested.HierarchicalGraphMachine.
    Attributes:
        machine_attributes (dict): Same as Graph but extended with cluster/subgraph information
    """

    machine_attributes = Graph.machine_attributes.copy()
    machine_attributes.update(
        {'clusterrank': 'local', 'rankdir': 'TB', 'ratio': 0.8})

    def __init__(self, *args, **kwargs):
        self.seen_nodes = []
        self.seen_transitions = []
        _super(NestedGraph, self).__init__(*args, **kwargs)
        self.style_attributes['edge']['default']['minlen'] = 2

    def _add_nodes(self, states, container):
        states = [self.machine.get_state(state) for state in states] if isinstance(states, dict) else states
        for state in states:
            if state.name in self.seen_nodes:
                continue
            self.seen_nodes.append(state.name)
            if state.children:
                cluster_name = "cluster_" + state.name
                sub = container.add_subgraph(name=cluster_name, label=state.name, rank='source',
                                             **self.style_attributes['graph']['default'])
                anchor_name = state.name + "_anchor"
                root_container = sub.add_subgraph(name=state.name + '_root')
                child_container = sub.add_subgraph(name=cluster_name + '_child', label='', color=None)
                root_container.add_node(anchor_name, shape='point', fillcolor='black', width='0.1')
                self._add_nodes(state.children, child_container)
            else:
                container.add_node(state.name, shape=self.style_attributes['node']['default']['shape'])

    def _add_edges(self, events, container):

        for sub in container.subgraphs_iter():
            events = self._add_edges(events, sub)

        for event in events.values():
            label = str(event.name)
            if self._omit_auto_transitions(event, label):
                continue

            for transitions in event.transitions.items():
                src = transitions[0]
                if not container.has_node(src) and _get_subgraph(container, "cluster_" + src) is None:
                    continue

                src = self.machine.get_state(src)
                edge_attr = {}
                label_pos = 'label'
                if src.children:
                    edge_attr['ltail'] = "cluster_" + src.name
                    src_name = src.name + "_anchor"
                else:
                    src_name = src.name

                for trans in transitions[1]:
                    if trans in self.seen_transitions:
                        continue
                    if trans.dest is None:
                        dst = src
                        label += " [internal]"
                    elif not container.has_node(trans.dest) and _get_subgraph(container, 'cluster_' + trans.dest) is None:
                        continue
                    else:
                        dst = self.machine.get_state(trans.dest)

                    self.seen_transitions.append(trans)
                    if dst.children:
                        if not src.is_substate_of(dst.name):
                            edge_attr['lhead'] = "cluster_" + dst.name
                        dst_name = dst.name + '_anchor'
                    else:
                        dst_name = dst.name

                    if 'ltail' in edge_attr:
                        if _get_subgraph(container, edge_attr['ltail']).has_node(dst_name):
                            del edge_attr['ltail']

                    edge_attr[label_pos] = self._transition_label(label, trans)
                    if container.has_edge(src_name, dst_name):
                        edge = container.get_edge(src_name, dst_name)
                        edge.attr[label_pos] += ' | ' + edge_attr[label_pos]
                    else:
                        container.add_edge(src_name, dst_name, **edge_attr)

        return events


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


class GraphMachine(Machine):
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
        self.show_auto_transitions = kwargs.pop('show_auto_transitions', False)
        self.model_graphs = {}

        # Update March 2017: This temporal overwrite does not work
        # well with inheritance. Since the tests pass I will disable it
        # for now. If issues arise during initialization we might have to review this again.
        # # temporally disable overwrites since graphing cannot
        # # be initialized before base machine
        # add_states = self.add_states
        # add_transition = self.add_transition
        # self.add_states = super(GraphMachine, self).add_states
        # self.add_transition = super(GraphMachine, self).add_transition

        _super(GraphMachine, self).__init__(*args, **kwargs)
        # # Second part of overwrite
        # self.add_states = add_states
        # self.add_transition = add_transition

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
        if not self.show_auto_transitions and not graph.has_edge(edge_from, edge_to):
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
