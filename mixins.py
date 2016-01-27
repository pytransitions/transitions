from .core import Transition
from .diagrams import AGraph


class AAGraph(AGraph):
    seen = []

    def _add_nodes(self, states, container):
        # to be able to process children recursively as well as the state dict of a machine
        states = states.values() if isinstance(states, dict) else states
        for state in states:
            if state.name in self.seen:
                continue
            elif state.children is not None:
                self.seen.append(state.name)
                sub = container.add_subgraph(name="cluster_" + state.name, label=state.name)
                self._add_nodes(state.children, sub)
            else:
                shape = 'doublecircle'

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
                    if dst.children is not None:
                        dst = dst.get_initial().name
                    else:
                        dst = dst.name
                    sub.add_edge(src, dst, label=label)


class MachineGraphSupport(object):

    def __init__(self, *args, **kwargs):
        self.graph = None
        self.default_state_attributes = {
            'shape': 'circle',
            'height': '1.2',
            'style': 'filled',
            'fillcolor': 'white',
            'color': 'black',
        }

        self.active_state_attributes = {
            'color': 'red',
            'fillcolor': 'darksalmon',
            'shape': 'doublecircle'
        }

        self.previous_state_attributes = {
            'color': 'blue',
            'fillcolor': 'azure2',
        }

        self.default_edge_attributes = {
            'color': 'black',
        }

        self.previous_edge_attributes = {
            'color': 'blue',
        }
        super(MachineGraphSupport, self).__init__(*args, **kwargs)

    def get_graph(self, title=None, diagram_class=AGraph, force_new=False):
        if self.graph is None or force_new:
            self.graph = diagram_class(self).get_graph(title)
            self.set_node_state(self.initial, state='active', reset=True)

        return self.graph

    def set_edge_state(self, edge_from, edge_to, state='default'):
        """ Mark a node as active by changing the attributes """
        assert hasattr(self, 'graph')

        edge = self.graph.get_edge(edge_from, edge_to)

        # Reset all the edges
        for e in self.graph.edges_iter():
            e.attr.update(self.default_edge_attributes)

        try:
            edge.attr.update(getattr(self, '{}_edge_attributes'.format(state)))
        except KeyError:
            edge.attr.update(self.default_edge_attributes)

    def set_node_state(self, node_name=None, state='default', reset=False):
        assert hasattr(self, 'graph')

        if node_name is None:
            node_name = self.state

        if reset:
            for n in self.graph.nodes_iter():
                n.attr.update(self.default_state_attributes)

        node = self.graph.get_node(node_name)
        try:
            node.attr.update(getattr(self, '{}_state_attributes'.format(state)))
        except KeyError:
            node.attr.update(self.default_state_attributes)

    @staticmethod
    def _create_transition(*args, **kwargs):
        return TransitionGraphSupport(*args, **kwargs)


class TransitionGraphSupport(Transition):

    def _change_state(self, event_data):

        # Mark the active node
        event_data.machine.set_node_state(self.dest, state='active', reset=True)

        # Mark the previous node and path used
        if self.source is not None:
            event_data.machine.set_node_state(self.source, state='previous')
            event_data.machine.set_edge_state(self.source, self.dest, state='previous')

        super(TransitionGraphSupport, self)._change_state(event_data)
