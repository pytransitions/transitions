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
                    sub.add_edge(src, dst, label=label)


class MachineGraphSupport(object):

    def __init__(self, title='State Machine', *args, **kwargs):
        super(MachineGraphSupport, self).__init__(*args, **kwargs)

        # Create graph at beginnning
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
        event_data.machine.set_node_state(self.dest, state='active', reset=True)

        # Mark the previous node and path used
        if self.source is not None:
            event_data.machine.set_node_state(self.source, state='previous')
            event_data.machine.set_edge_state(self.source, self.dest, state='previous')

        super(TransitionGraphSupport, self)._change_state(event_data)
