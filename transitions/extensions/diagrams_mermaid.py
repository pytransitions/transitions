"""
    transitions.extensions.diagrams
    -------------------------------

    Mermaid support for (nested) machines. This also includes partial views
    of currently valid transitions.
"""
import copy
import logging
from collections import defaultdict

from .diagrams_graphviz import filter_states
from .diagrams_base import BaseGraph

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())


class Graph(BaseGraph):
    """Graph creation for transitions.core.Machine.
        Attributes:
            custom_styles (dict): A dictionary of styles for the current graph
    """

    def __init__(self, machine):
        self.custom_styles = {}
        self.reset_styling()
        super(Graph, self).__init__(machine)

    def set_previous_transition(self, src, dst):
        self.custom_styles["edge"][src][dst] = "previous"
        self.set_node_style(src, "previous")

    def set_node_style(self, state, style):
        self.custom_styles["node"][state.name if hasattr(state, "name") else state] = style

    def reset_styling(self):
        self.custom_styles = {
            "edge": defaultdict(lambda: defaultdict(str)),
            "node": defaultdict(str),
        }

    def _add_nodes(self, states, container):
        for state in states:
            container.append("state \"{}\" as {}".format(self._convert_state_attributes(state), state["name"]))
            container.append("Class {} s_{}".format(state["name"],
                                                    self.custom_styles["node"][state["name"]] or "default"))

    def _add_edges(self, transitions, container):
        edge_labels = defaultdict(lambda: defaultdict(list))
        for transition in transitions:
            try:
                dst = transition["dest"]
            except KeyError:
                dst = transition["source"]
            edge_labels[transition["source"]][dst].append(self._transition_label(transition))
        for src, dests in edge_labels.items():
            for dst, labels in dests.items():
                container.append("{} --> {}: {}".format(src, dst, " | ".join(labels)))

    def generate(self):
        """Triggers the generation of a graph. With graphviz backend, this does nothing since graph trees need to be
        built from scratch with the configured styles.
        """
        # we cannot really generate a graph in advance with graphviz

    def get_graph(self, title=None, roi_state=None):
        title = title if title else self.machine.title

        fsm_graph = ['---', title, '---', 'stateDiagram-v2']
        fsm_graph.extend(_to_mermaid(self.machine.machine_attributes, " "))

        for style_name, style_attrs in self.machine.style_attributes["node"].items():
            if style_name:
                fsm_graph.append("classDef s_{} {}".format(
                    style_name, ','.join(_to_mermaid(style_attrs, ":"))))
        fsm_graph.append("")
        states, transitions = self._get_elements()
        if roi_state:
            active_states = set()
            sep = getattr(self.machine.state_cls, "separator", None)
            for state in self._flatten(roi_state):
                active_states.add(state)
                if sep:
                    state = sep.join(state.split(sep)[:-1])
                    while state:
                        active_states.add(state)
                        state = sep.join(state.split(sep)[:-1])
            transitions = [
                t
                for t in transitions
                if t["source"] in active_states or self.custom_styles["edge"][t["source"]][t["dest"]]
            ]
            active_states = active_states.union({
                t
                for trans in transitions
                for t in [trans["source"], trans.get("dest", trans["source"])]
            })
            active_states = active_states.union({k for k, style in self.custom_styles["node"].items() if style})
            states = filter_states(copy.deepcopy(states), active_states, self.machine.state_cls)
        self._add_nodes(states, fsm_graph)
        fsm_graph.append("")
        self._add_edges(transitions, fsm_graph)
        if self.machine.initial and (roi_state is None or roi_state == self.machine.initial):
            fsm_graph.append("[*] --> {}".format(self.machine.initial))

        indent = 0
        for i in range(len(fsm_graph)):
            next_indent = indent
            if fsm_graph[i].startswith("stateDiagram") or fsm_graph[i].endswith("{"):
                next_indent += 2
            elif fsm_graph[i].startswith("}"):
                indent -= 2
                next_indent -= 2
            fsm_graph[i] = " " * indent + fsm_graph[i]
            indent = next_indent

        return DigraphMock("\n".join(fsm_graph))

    def _convert_state_attributes(self, state):
        label = state.get("label", state["name"])
        if self.machine.show_state_attributes:
            if "tags" in state:
                label += " [" + ", ".join(state["tags"]) + "]"
            if "on_enter" in state:
                label += r"\n- enter:\n  + " + r"\n  + ".join(state["on_enter"])
            if "on_exit" in state:
                label += r"\n- exit:\n  + " + r"\n  + ".join(state["on_exit"])
            if "timeout" in state:
                label += r'\n- timeout(' + state['timeout'] + 's) -> (' + ', '.join(state['on_timeout']) + ')'
        # end each label with a left-aligned newline
        return label


class NestedGraph(Graph):
    """Graph creation support for transitions.extensions.nested.HierarchicalGraphMachine."""

    def __init__(self, *args, **kwargs):
        self._cluster_states = []
        super(NestedGraph, self).__init__(*args, **kwargs)

    def set_node_style(self, state, style):
        for state_name in self._get_state_names(state):
            super(NestedGraph, self).set_node_style(state_name, style)

    def set_previous_transition(self, src, dst):
        self.custom_styles["edge"][src][dst] = "previous"
        self.set_node_style(src, "previous")

    def _add_nodes(self, states, container):
        self._add_nested_nodes(states, container, prefix="", default_style="default")

    def _add_nested_nodes(self, states, container, prefix, default_style):
        for state in states:
            name = prefix + state["name"]
            container.append("state \"{}\" as {}".format(self._convert_state_attributes(state), name))
            if state.get("final", False):
                container.append("{} --> [*]".format(name))
            if not prefix:
                container.append("Class {} s_{}".format(name.replace(" ", ""),
                                                        self.custom_styles["node"][name] or default_style))
            if state.get("children", None) is not None:
                container.append("state {} {{".format(name))
                self._cluster_states.append(name)
                # with container.subgraph(name=cluster_name, graph_attr=attr) as sub:
                initial = state.get("initial", "")
                is_parallel = isinstance(initial, list)
                if is_parallel:
                    for child in state["children"]:
                        self._add_nested_nodes(
                            [child],
                            container,
                            default_style="parallel",
                            prefix=prefix + state["name"] + self.machine.state_cls.separator,
                        )
                        container.append("--")
                    if state["children"]:
                        container.pop()
                else:
                    if initial:
                        container.append("[*] --> {}".format(
                            prefix + state["name"] + self.machine.state_cls.separator + initial))
                    self._add_nested_nodes(
                        state["children"],
                        container,
                        default_style="default",
                        prefix=prefix + state["name"] + self.machine.state_cls.separator,
                    )
                container.append("}")

    def _add_edges(self, transitions, container):
        edges_attr = defaultdict(lambda: defaultdict(dict))

        for transition in transitions:
            # enable customizable labels
            src = transition["source"]
            dst = transition.get("dest", src)
            if edges_attr[src][dst]:
                attr = edges_attr[src][dst]
                attr["label"] = " | ".join(
                    [edges_attr[src][dst]["label"], self._transition_label(transition)]
                )
            else:
                edges_attr[src][dst] = self._create_edge_attr(src, dst, transition)

        for custom_src, dests in self.custom_styles["edge"].items():
            for custom_dst, style in dests.items():
                if style and (
                    custom_src not in edges_attr or custom_dst not in edges_attr[custom_src]
                ):
                    edges_attr[custom_src][custom_dst] = self._create_edge_attr(
                        custom_src, custom_dst, {"trigger": "", "dest": ""}
                    )

        for src, dests in edges_attr.items():
            for dst, attr in dests.items():
                if not attr["label"]:
                    continue
                container.append("{source} --> {dest}: {label}".format(**attr))

    def _create_edge_attr(self, src, dst, transition):
        return {"source": src, "dest": dst, "label": self._transition_label(transition)}


class DigraphMock:

    def __init__(self, source):
        self.source = source

    # pylint: disable=redefined-builtin,unused-argument
    def draw(self, filename, format=None, prog="dot", args=""):
        """
        Generates and saves an image of the state machine using graphviz. Note that `prog` and `args` are only part
        of the signature to mimic `Agraph.draw` and thus allow to easily switch between graph backends.
        Args:
            filename (str or file descriptor or stream or None): path and name of image output, file descriptor,
            stream object or None
            format (str): ignored
            prog (str): ignored
            args (str): ignored
        Returns:
            None or str: Returns a binary string of the graph when the first parameter (`filename`) is set to None.
        """

        if filename is None:
            return self.source
        if isinstance(filename, str):
            with open(filename, "w") as f:
                f.write(self.source)
        else:
            filename.write(self.source.encode())
        return None


invalid = {"style", "shape", "peripheries", "strict", "directed"}
convertible = {"fillcolor": "fill", "rankdir": "direction"}


def _to_mermaid(style_attrs, sep):
    params = []
    for k, v in style_attrs.items():
        if k in invalid:
            continue
        if k in convertible:
            k = convertible[k]
        params.append("{}{}{}".format(k, sep, v))
    return params
