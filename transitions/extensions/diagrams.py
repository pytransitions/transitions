from transitions import Transition
from transitions.extensions.markup import MarkupMachine

import warnings
import logging
from enum import Enum
from functools import partial

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())

# make deprecation warnings of transition visible for module users
warnings.filterwarnings(action='default', message=r".*transitions version.*")

# this is a workaround for dill issues when partials and super is used in conjunction
# without it, Python 3.0 - 3.3 will not support pickling
# https://github.com/pytransitions/transitions/issues/236
_super = super


class TransitionGraphSupport(Transition):
    """ Transition used in conjunction with (Nested)Graphs to update graphs whenever a transition is
        conducted.
    """

    def _change_state(self, event_data):
        graph = event_data.machine.model_graphs[event_data.model]
        graph.reset_styling()
        graph.set_previous_transition(self.source, self.dest)
        _super(TransitionGraphSupport, self)._change_state(event_data)  # pylint: disable=protected-access


class GraphMachine(MarkupMachine):
    """ Extends transitions.core.Machine with graph support.
        Is also used as a mixin for HierarchicalMachine.
        Attributes:
            _pickle_blacklist (list): Objects that should not/do not need to be pickled.
            transition_cls (cls): TransitionGraphSupport
    """

    _pickle_blacklist = ['model_graphs']
    transition_cls = TransitionGraphSupport

    machine_attributes = {
        'directed': 'true',
        'strict': 'false',
        'rankdir': 'LR',
    }

    hierarchical_machine_attributes = {
        'rankdir': 'TB',
        'rank': 'source',
        'nodesep': '1.5',
        'compound': 'true'
    }

    style_attributes = {
        'node': {
            '': {},
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
            '': {},
            'default': {
                'color': 'black'
            },
            'previous': {
                'color': 'blue'
            }
        },
        'graph': {
            '': {},
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

    # model_graphs cannot be pickled. Omit them.
    def __getstate__(self):
        # self.pkl_graphs = [(g.markup, g.custom_styles) for g in self.model_graphs]
        return {k: v for k, v in self.__dict__.items() if k not in self._pickle_blacklist}

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.model_graphs = {}  # reinitialize new model_graphs
        for model in self.models:
            try:
                _ = self._get_graph(model, title=self.title)
            except AttributeError as e:
                _LOGGER.warning("Graph for model could not be initialized after pickling: %s", e)

    def __init__(self, *args, **kwargs):
        # remove graph config from keywords
        self.title = kwargs.pop('title', 'State Machine')
        self.show_conditions = kwargs.pop('show_conditions', False)
        self.show_state_attributes = kwargs.pop('show_state_attributes', False)
        # in MarkupMachine this switch is called 'with_auto_transitions'
        # keep 'auto_transitions_markup' for backwards compatibility
        kwargs['auto_transitions_markup'] = kwargs.pop('show_auto_transitions', False)
        self.model_graphs = {}
        self.graph_cls = self._init_graphviz_engine(kwargs.pop('use_pygraphviz', True))

        _LOGGER.debug("Using graph engine %s", self.graph_cls)
        _super(GraphMachine, self).__init__(*args, **kwargs)

        # Create graph at beginning
        for model in self.models:
            if hasattr(model, 'get_graph'):
                raise AttributeError('Model already has a get_graph attribute. Graph retrieval cannot be bound.')
            setattr(model, 'get_graph', partial(self._get_graph, model))
            _ = model.get_graph(title=self.title, force_new=True)  # initialises graph
        # for backwards compatibility assign get_combined_graph to get_graph
        # if model is not the machine
        if not hasattr(self, 'get_graph'):
            setattr(self, 'get_graph', self.get_combined_graph)

    def _init_graphviz_engine(self, use_pygraphviz):
        if use_pygraphviz:
            try:
                if hasattr(self.state_cls, 'separator'):
                    from .diagrams_pygraphviz import NestedGraph as Graph
                    self.machine_attributes.update(self.hierarchical_machine_attributes)
                else:
                    from .diagrams_pygraphviz import Graph
                return Graph
            except ImportError:
                pass
        if hasattr(self.state_cls, 'separator'):
            from .diagrams_graphviz import NestedGraph as Graph
            self.machine_attributes.update(self.hierarchical_machine_attributes)
        else:
            from .diagrams_graphviz import Graph
        return Graph

    def _get_graph(self, model, title=None, force_new=False, show_roi=False):
        if force_new:
            grph = self.graph_cls(self, title=title if title is not None else self.title)
            self.model_graphs[model] = grph
            try:
                if isinstance(model.state, Enum):
                    self.model_graphs[model].set_node_style(model.state.name, 'active')
                else:
                    self.model_graphs[model].set_node_style(model.state, 'active')
            except AttributeError:
                _LOGGER.info("Could not set active state of diagram")
        try:
            m = self.model_graphs[model]
        except KeyError:
            _ = self._get_graph(model, title, force_new=True)
            m = self.model_graphs[model]
        m.roi_state = model.state if show_roi else None
        return m.get_graph(title=title)

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
