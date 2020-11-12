"""
    transitions.extensions.diagrams
    -------------------------------

    Graphviz support for (nested) machines. This also includes partial views
    of currently valid transitions.
"""

import logging
from functools import partial
from collections import defaultdict
from os.path import splitext
import copy

from .diagrams import BaseGraph
from ..core import listify
try:
    import graphviz as pgv
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

    def __init__(self, machine, title=None):
        self.reset_styling()
        _super(Graph, self).__init__(machine, title)

    def set_previous_transition(self, src, dst, key=None):
        self.custom_styles['edge'][src][dst] = 'previous'
        self.set_node_style(src, 'previous')

    def set_node_style(self, state, style):
        self.custom_styles['node'][state] = style

    def reset_styling(self):
        self.custom_styles = {'edge': defaultdict(lambda: defaultdict(str)),
                              'node': defaultdict(str)}

    def _add_nodes(self, states, container):
        for state in states:
            style = self.custom_styles['node'][state['name']]
            container.node(state['name'], label=self._convert_state_attributes(state),
                           **self.machine.style_attributes['node'][style])

    def _add_edges(self, transitions, container):
        edge_labels = defaultdict(lambda: defaultdict(list))
        for transition in transitions:
            try:
                dst = transition['dest']
            except KeyError:
                dst = transition['source']
            edge_labels[transition['source']][dst].append(self._transition_label(transition))
        for src, dests in edge_labels.items():
            for dst, labels in dests.items():
                style = self.custom_styles['edge'][src][dst]
                container.edge(src, dst, label=' | '.join(labels), **self.machine.style_attributes['edge'][style])

    def generate(self, title=None, roi_state=None):
        """ Generate a DOT graph with graphviz
        Args:
            roi_state (str): Optional, show only custom states and edges from roi_state
        """
        if not pgv:  # pragma: no cover
            raise Exception('AGraph diagram requires graphviz')

        title = self.machine.title if not title else title

        fsm_graph = pgv.Digraph(name=title, node_attr=self.machine.style_attributes['node']['default'],
                                edge_attr=self.machine.style_attributes['edge']['default'],
                                graph_attr=self.machine.style_attributes['graph']['default'])
        fsm_graph.graph_attr.update(**self.machine.machine_attributes)
        fsm_graph.graph_attr['label'] = title
        # For each state, draw a circle
        states, transitions = self._get_elements()
        if roi_state:
            transitions = [t for t in transitions
                           if t['source'] == roi_state or self.custom_styles['edge'][t['source']][t['dest']]]
            state_names = [t for trans in transitions
                           for t in [trans['source'], trans.get('dest', trans['source'])]]
            state_names += [k for k, style in self.custom_styles['node'].items() if style]
            states = _filter_states(states, state_names, self.machine.state_cls)
        self._add_nodes(states, fsm_graph)
        self._add_edges(transitions, fsm_graph)
        setattr(fsm_graph, 'draw', partial(self.draw, fsm_graph))
        return fsm_graph

    def get_graph(self, title=None):
        return self.generate(title, roi_state=self.roi_state)

    @staticmethod
    def draw(graph, filename, format=None, prog='dot', args=''):
        """ Generates and saves an image of the state machine using graphviz.
        Args:
            filename (str): path and name of image output
            format (str): Optional format of the output file
        Returns:

        """
        graph.engine = prog
        try:
            filename, ext = splitext(filename)
            format = format if format is not None else ext[1:]
            graph.render(filename, format=format if format else 'png', cleanup=True)
        except TypeError:
            if format is None:
                raise ValueError("Parameter 'format' must not be None when filename is no valid file path.")
            filename.write(graph.pipe(format))


class NestedGraph(Graph):
    """ Graph creation support for transitions.extensions.nested.HierarchicalGraphMachine. """

    def __init__(self, *args, **kwargs):
        self._cluster_states = []
        _super(NestedGraph, self).__init__(*args, **kwargs)

    def set_previous_transition(self, src, dst, key=None):
        src_name = self._get_global_name(src.split(self.machine.state_cls.separator))
        dst_name = self._get_global_name(dst.split(self.machine.state_cls.separator))
        _super(NestedGraph, self).set_previous_transition(src_name, dst_name, key)

    def _add_nodes(self, states, container, prefix='', default_style='default'):

        for state in states:
            name = prefix + state['name']
            label = self._convert_state_attributes(state)

            if state.get('children', []):
                cluster_name = "cluster_" + name
                style_name = self.custom_styles['node'][name] or default_style
                attr = {'label': label, 'rank': 'source'}
                attr.update(**self.machine.style_attributes['graph'][style_name])
                with container.subgraph(name=cluster_name, graph_attr=attr) as sub:
                    self._cluster_states.append(name)
                    is_parallel = isinstance(state.get('initial', ''), list)
                    width = '0.0' if is_parallel else '0.1'
                    with sub.subgraph(name=cluster_name + '_root',
                                      graph_attr={'label': '', 'color': 'None', 'rank': 'min'}) as root:
                        root.node(name + "_anchor", shape='point', fillcolor='black', width=width)
                    self._add_nodes(state['children'], sub, default_style='parallel' if is_parallel else 'default',
                                    prefix=prefix + state['name'] + self.machine.state_cls.separator)
            else:
                style = self.machine.style_attributes['node'][default_style].copy()
                style.update(self.machine.style_attributes['node'][self.custom_styles['node'][name] or default_style])
                container.node(name, label=label, **style)

    def _add_edges(self, transitions, container, prefix=''):
        edges_attr = defaultdict(lambda: defaultdict(dict))

        for transition in transitions:
            # enable customizable labels
            src = prefix + transition['source']
            try:
                dst = prefix + transition['dest']
            except KeyError:
                dst = src
            if edges_attr[src][dst]:
                attr = edges_attr[src][dst]
                attr[attr['label_pos']] = ' | '.join([edges_attr[src][dst][attr['label_pos']],
                                                      self._transition_label(transition)])
            else:
                edges_attr[src][dst] = self._create_edge_attr(src, dst, transition)

        for custom_src, dests in self.custom_styles['edge'].items():
            for custom_dst, style in dests.items():
                if style and (custom_src not in edges_attr or custom_dst not in edges_attr[custom_src]):
                    edges_attr[custom_src][custom_dst] = self._create_edge_attr(custom_src, custom_dst,
                                                                                {'trigger': '', 'dest': ''})

        for src, dests in edges_attr.items():
            for dst, attr in dests.items():
                del attr['label_pos']
                style = self.custom_styles['edge'][src][dst]
                attr.update(**self.machine.style_attributes['edge'][style])
                container.edge(attr.pop('source'), attr.pop('dest'), **attr)

    def _create_edge_attr(self, src, dst, transition):
        label_pos = 'label'
        attr = {}
        if src in self._cluster_states:
            attr['ltail'] = 'cluster_' + src
            src_name = src + "_anchor"
            label_pos = 'headlabel'
        else:
            src_name = src

        if dst in self._cluster_states:
            if not src.startswith(dst):
                attr['lhead'] = "cluster_" + dst
                label_pos = 'taillabel' if label_pos.startswith('l') else 'label'
            dst_name = dst + '_anchor'
        else:
            dst_name = dst

        # remove ltail when dst (ltail always starts with 'cluster_') is a child of src
        if 'ltail' in attr and dst_name.startswith(attr['ltail'][8:]):
            del attr['ltail']

        attr[label_pos] = self._transition_label(transition)
        attr['label_pos'] = label_pos
        attr['source'] = src_name
        attr['dest'] = dst_name
        return attr


def _filter_states(states, state_names, state_cls, prefix=None):
    prefix = prefix or []
    result = []
    for state in states:
        pref = prefix + [state['name']]
        if 'children' in state:
            state['children'] = _filter_states(state['children'], state_names, state_cls, prefix=pref)
            result.append(state)
        elif getattr(state_cls, 'separator', '_').join(pref) in state_names:
            result.append(state)
    return result
