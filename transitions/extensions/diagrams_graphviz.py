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

from .nesting import NestedState
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


class Graph(object):
    """ Graph creation for transitions.core.Machine.
        Attributes:
            machine (object): Reference to the related machine.
    """

    def __init__(self, machine, title=None):
        self.machine = machine
        self.roi_state = None
        self.custom_styles = None
        self.reset_styling()
        self.generate(title)

    def set_previous_transition(self, src, dst):
        self.custom_styles['edge'][src][dst] = 'previous'
        self.set_node_style(src, 'previous')
        self.set_node_style(dst, 'active')

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

    def generate(self, title=None, roi_state=None):
        """ Generate a DOT graph with graphviz
        Args:
            roi_state (string): Optional, show only custom states and edges from roi_state
        """
        if not pgv:  # pragma: no cover
            raise Exception('AGraph diagram requires graphviz')

        title = '' if not title else title

        fsm_graph = pgv.Digraph(name=title, node_attr=self.machine.style_attributes['node']['default'],
                                edge_attr=self.machine.style_attributes['edge']['default'],
                                graph_attr=self.machine.style_attributes['graph']['default'])
        fsm_graph.graph_attr.update(**self.machine.machine_attributes)
        # For each state, draw a circle
        try:
            states = self.machine._markup.get('states', [])
            transitions = self.machine._markup.get('transitions', [])
            if roi_state:
                transitions = [t for t in transitions
                               if t['source'] == roi_state or self.custom_styles['edge'][t['source']][t['dest']]]
                state_names = [t for trans in transitions
                               for t in [trans['source'], trans.get('dest', trans['source'])]]
                state_names += [k for k, style in self.custom_styles['node'].items() if style]
                states = _filter_states(states, state_names)
            self._add_nodes(states, fsm_graph)
            self._add_edges(transitions, fsm_graph)
        except KeyError:
            _LOGGER.error("Graph creation incomplete!")
        setattr(fsm_graph, 'draw', partial(self.draw, fsm_graph))
        return fsm_graph

    def get_graph(self, title=None):
        return self.generate(title, roi_state=self.roi_state)

    @staticmethod
    def draw(graph, filename, format=None, prog='dot', args=''):
        """ Generates and saves an image of the state machine using graphviz.
        Args:
            filename (string): path and name of image output
            format (string): Optional format of the output file
        Returns:

        """
        graph.engine = prog
        try:
            filename, ext = splitext(filename)
            format = format if format is not None else ext[1:]
            graph.render(filename, format=format if format else 'png', cleanup=True)
        except TypeError:
            if format is None:
                raise ValueError("Paramter 'format' must not be None when filename is no valid file path.")
            filename.write(graph.pipe(format))

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
    """ Graph creation support for transitions.extensions.nested.HierarchicalGraphMachine. """

    def __init__(self, *args, **kwargs):
        self._cluster_states = []
        _super(NestedGraph, self).__init__(*args, **kwargs)

    def _add_nodes(self, states, container, prefix=''):

        for state in states:
            name = prefix + state['name']
            label = self._convert_state_attributes(state)

            if 'children' in state:
                cluster_name = "cluster_" + name
                with container.subgraph(name=cluster_name,
                                        graph_attr=self.machine.style_attributes['graph']['default']) as sub:
                    style = self.custom_styles['node'][name]
                    sub.graph_attr.update(label=label, rank='source', **self.machine.style_attributes['graph'][style])
                    self._cluster_states.append(name)
                    with sub.subgraph(name=cluster_name + '_root',
                                      graph_attr={'label': '', 'color': 'None', 'rank': 'min'}) as root:
                        root.node(name + "_anchor", shape='point', fillcolor='black', width='0.1')
                    self._add_nodes(state['children'], sub, prefix=prefix + state['name'] + NestedState.separator)
            else:
                style = self.custom_styles['node'][name]
                container.node(name, label=label, **self.machine.style_attributes['node'][style])

    def _add_edges(self, transitions, container):
        edges_attr = defaultdict(lambda: defaultdict(dict))

        for transition in transitions:
            # enable customizable labels
            label_pos = 'label'
            src = transition['source']
            try:
                dst = transition['dest']
            except KeyError:
                dst = src
            if edges_attr[src][dst]:
                attr = edges_attr[src][dst]
                attr[attr['label_pos']] = ' | '.join([edges_attr[src][dst][attr['label_pos']],
                                                      self._transition_label(transition)])
                continue
            else:
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

                # # remove ltail when dst is a child of src
                # if 'ltail' in edge_attr:
                #     if _get_subgraph(container, edge_attr['ltail']).has_node(dst_name):
                #         del edge_attr['ltail']

                attr[label_pos] = self._transition_label(transition)
                attr['label_pos'] = label_pos
                attr['source'] = src_name
                attr['dest'] = dst_name
                edges_attr[src][dst] = attr

        for src, dests in edges_attr.items():
            for dst, attr in dests.items():
                del attr['label_pos']
                style = self.custom_styles['edge'][src][dst]
                attr.update(**self.machine.style_attributes['edge'][style])
                container.edge(attr.pop('source'), attr.pop('dest'), **attr)


def _filter_states(states, state_names, prefix=None):
    prefix = prefix or []
    result = []
    for state in states:
        pref = prefix + [state['name']]
        if 'children' in state:
            state['children'] = _filter_states(state['children'], state_names, prefix=pref)
            result.append(state)
        elif NestedState.separator.join(pref) in state_names:
            result.append(state)
    return result
