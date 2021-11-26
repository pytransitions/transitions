import abc
from transitions.core import StateIdentifier, StateConfig, CallbacksArg, Transition, Machine, State
from transitions.extensions.nesting import NestedTransition
from transitions.extensions.markup import MarkupMachine, HierarchicalMarkupMachine
from logging import Logger
from typing import Any, Type, List, Dict, Union, Optional, Protocol, IO, Tuple, Generator

_LOGGER: Logger


class GraphProtocol(Protocol):

    def draw(self, filename: Optional[str, IO], format:Optional[str] = ...,
             prog: Optional[str] = ..., args:str = ...) -> Optional[str]: ...

class GraphModelProtocol(Protocol):

    def get_graph(self, title=None, force_new=False, show_roi=False) -> GraphProtocol: ...


class TransitionGraphSupport(Transition):
    label: str
    def __init__(self, *args, **kwargs) -> None: ...
    def _change_state(self, event_data) -> None: ...


class GraphMachine(MarkupMachine):
    _pickle_blacklist: List[str]
    transition_cls: Type[TransitionGraphSupport]
    machine_attributes: Dict[str, str]
    hierarchical_machine_attributes:Dict [str, str]
    style_attributes: Dict[str, Union[str, Dict[str, Union[str, Dict[str]]]]]
    model_graphs: Dict[int, BaseGraph]
    title: str
    show_conditions: bool
    show_state_attributes: bool
    graph_cls: Type[BaseGraph]
    models: List[GraphModelProtocol]
    def __getstate__(self) -> Dict[str, Any]: ...
    def __setstate__(self, state: Dict[str, Any]) -> None: ...
    def __init__(self, *args, **kwargs) -> None: ...
    def _init_graphviz_engine(self, use_pygraphviz: bool): ...
    def _get_graph(self, model: GraphModelProtocol, title: Optional[str] = ..., force_new: bool = ...,
                   show_roi: bool = ...) -> GraphProtocol: ...
    def get_combined_graph(self, title: Optional[str] = ..., force_new: bool = ...,
                           show_roi: bool = ...) -> GraphProtocol: ...
    def add_model(self, model: Union[Union[Machine.self_literal, object], List[Union[Machine.self_literal, object]]],
                  initial: StateIdentifier = ...) -> None: ...
    def add_states(self, states: Union[List[StateConfig], StateConfig],
                   on_enter: CallbacksArg = ..., on_exit: CallbacksArg = ...,
                   ignore_invalid_triggers: Optional[bool] = ..., **kwargs) -> None: ...
    def add_transition(self, trigger: str,
                       source: Union[StateIdentifier, List[StateIdentifier]],
                       dest: StateIdentifier, conditions: CallbacksArg = ..., unless: CallbacksArg = ...,
                       before: CallbacksArg = ..., after: CallbacksArg = ..., prepare: CallbacksArg = ...,
                       **kwargs) -> None: ...


class NestedGraphTransition(TransitionGraphSupport, NestedTransition): ...


class HierarchicalGraphMachine(GraphMachine, HierarchicalMarkupMachine):
    transition_cls: Type[NestedGraphTransition]


class BaseGraph(metaclass=abc.ABCMeta):
    machine: Union[GraphMachine, HierarchicalGraphMachine]
    fsm_graph: Optional[GraphProtocol]
    def __init__(self, machine: GraphMachine) -> None: ...
    @abc.abstractmethod
    def generate(self) -> None: ...
    @abc.abstractmethod
    def set_previous_transition(self, src: str, dst: str) -> None: ...
    @abc.abstractmethod
    def reset_styling(self) -> None: ...
    @abc.abstractmethod
    def set_node_style(self, state: str, style: str) -> None: ...
    @abc.abstractmethod
    def get_graph(self, title: Optional[str] = ..., roi_state: Optional[str] = ...) -> GraphProtocol: ...
    def _convert_state_attributes(self, state: Dict[str, str]) -> str: ...
    def _transition_label(self, tran: Dict[str, str]) -> str: ...
    def _get_global_name(self, path: List[str]) -> str: ...
    def _get_elements(self) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]: ...


def _flatten(item: List[Union[list, tuple, set, object]]) -> Generator[object]: ...
