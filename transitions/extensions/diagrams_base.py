"""
    transitions.extensions.diagrams_base
    ------------------------------------

    The class BaseGraph implements the common ground for Graphviz backends.
"""

import copy
import abc
import logging

import six

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())


@six.add_metaclass(abc.ABCMeta)
class BaseGraph(object):
    """ Provides the common foundation for graphs generated either with pygraphviz or graphviz. This abstract class
    should not be instantiated directly. Use .(py)graphviz.(Nested)Graph instead.
    Attributes:
        machine (GraphMachine): The associated GraphMachine
        fsm_graph (object): The AGraph-like object that holds the graphviz information
    """

    def __init__(self, machine):
        self.machine = machine
        self.fsm_graph = None
        self.generate()

    @abc.abstractmethod
    def generate(self):
        """ Triggers the generation of a graph. """

    @abc.abstractmethod
    def set_previous_transition(self, src, dst):
        """ Sets the styling of an edge to 'previous'
        Args:
            src (str): Name of the source state
            dst (str): Name of the destination
        """

    @abc.abstractmethod
    def reset_styling(self):
        """ Resets the styling of the currently generated graph. """

    @abc.abstractmethod
    def set_node_style(self, state, style):
        """ Sets the style of nodes associated with a model state
        Args:
            state (str, Enum or list): Name of the state(s) or Enum(s)
            style (str): Name of the style
        """

    @abc.abstractmethod
    def get_graph(self, title=None, roi_state=None):
        """ Returns a graph object.
        Args:
            title (str): Title of the generated graph
            roi_state (State): If not None, the returned graph will only contain edges and states connected to it.
        Returns:
             A graph instance with a `draw` that allows to render the graph.
        """

    def _convert_state_attributes(self, state):
        label = state.get("label", state["name"])
        if self.machine.show_state_attributes:
            if "tags" in state:
                label += " [" + ", ".join(state["tags"]) + "]"
            if "on_enter" in state:
                label += r"\l- enter:\l  + " + r"\l  + ".join(state["on_enter"])
            if "on_exit" in state:
                label += r"\l- exit:\l  + " + r"\l  + ".join(state["on_exit"])
            if "timeout" in state:
                label += r'\l- timeout(' + state['timeout'] + 's) -> (' + ', '.join(state['on_timeout']) + ')'
        # end each label with a left-aligned newline
        return label + r"\l"

    def _get_state_names(self, state):
        if isinstance(state, (list, tuple, set)):
            for res in state:
                for inner in self._get_state_names(res):
                    yield inner
        else:
            yield self.machine.state_cls.separator.join(self.machine._get_enum_path(state))\
                if hasattr(state, "name") else state

    def _transition_label(self, tran):
        edge_label = tran.get("label", tran["trigger"])
        if "dest" not in tran:
            edge_label += " [internal]"
        if self.machine.show_conditions and any(prop in tran for prop in ["conditions", "unless"]):
            edge_label = "{edge_label} [{conditions}]".format(
                edge_label=edge_label,
                conditions=" & ".join(
                    tran.get("conditions", []) + ["!" + u for u in tran.get("unless", [])]
                ),
            )
        return edge_label

    def _get_global_name(self, path):
        if path:
            state = path.pop(0)
            with self.machine(state):
                return self._get_global_name(path)
        else:
            return self.machine.get_global_name()

    def _get_elements(self):
        states = []
        transitions = []
        try:
            markup = self.machine.get_markup_config()
            queue = [([], markup)]

            while queue:
                prefix, scope = queue.pop(0)
                for transition in scope.get("transitions", []):
                    if prefix:
                        tran = copy.copy(transition)
                        tran["source"] = self.machine.state_cls.separator.join(
                            prefix + [tran["source"]]
                        )
                        if "dest" in tran:  # don't do this for internal transitions
                            tran["dest"] = self.machine.state_cls.separator.join(
                                prefix + [tran["dest"]]
                            )
                    else:
                        tran = transition
                    transitions.append(tran)
                for state in scope.get("children", []) + scope.get("states", []):
                    if not prefix:
                        sta = state
                        states.append(sta)

                    ini = state.get("initial", [])
                    if not isinstance(ini, list):
                        ini = ini.name if hasattr(ini, "name") else ini
                        tran = dict(
                            trigger="",
                            source=self.machine.state_cls.separator.join(prefix + [state["name"]]) + "_anchor",
                            dest=self.machine.state_cls.separator.join(
                                prefix + [state["name"], ini]
                            ),
                        )
                        transitions.append(tran)
                    if state.get("children", []):
                        queue.append((prefix + [state["name"]], state))
        except KeyError:
            _LOGGER.error("Graph creation incomplete!")
        return states, transitions
