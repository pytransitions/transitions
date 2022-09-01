from transitions.core import (
    StateIdentifier, StateConfig, CallbacksArg, Transition, EventData, TransitionConfig, ModelParameter
)
from transitions.extensions.nesting import NestedTransition
from transitions.extensions.diagrams_base import BaseGraph, GraphModelProtocol, GraphProtocol
from transitions.extensions.markup import MarkupMachine, HierarchicalMarkupMachine
from logging import Logger
from typing import Any, Literal, Sequence, Type, List, Dict, Union, Optional, Generator

from enum import Enum

_LOGGER: Logger

# mypy does not support cyclic definitions (yet)
# thus we cannot use Dict[str, 'GraphvizParameters'] and have to fall back to Any
GraphvizParameters = Dict[str, Union[str, Dict[str, Any]]]

class TransitionGraphSupport(Transition):
    label: str
    def __init__(self, *args: List, **kwargs: Dict[str, Any]) -> None: ...
    def _change_state(self, event_data: EventData) -> None: ...


class GraphMachine(MarkupMachine):
    _pickle_blacklist: List[str]
    transition_cls: Type[TransitionGraphSupport]
    machine_attributes: Dict[str, str]
    hierarchical_machine_attributes:Dict [str, str]
    style_attributes: Dict[str, Union[str, Dict[str, Union[str, Dict[str, Any]]]]]
    model_graphs: Dict[int, BaseGraph]
    title: str
    show_conditions: bool
    show_state_attributes: bool
    graph_cls: Type[BaseGraph]
    models: List[GraphModelProtocol]
    def __getstate__(self) -> Dict[str, Any]: ...
    def __setstate__(self, state: Dict[str, Any]) -> None: ...
    def __init__(self, model: Optional[ModelParameter]=...,
                 states: Optional[Union[Sequence[StateConfig], Type[Enum]]] = ...,
                 initial: Optional[StateIdentifier] = ...,
                 transitions: Optional[Union[TransitionConfig, List[TransitionConfig]]] = ..., send_event: bool = ...,
                 auto_transitions: bool = ..., ordered_transitions: bool = ...,
                 ignore_invalid_triggers: Optional[bool] = ...,
                 before_state_change: CallbacksArg = ..., after_state_change: CallbacksArg = ...,
                 name: str = ..., queued: bool = ...,
                 prepare_event: CallbacksArg = ..., finalize_event: CallbacksArg = ...,
                 model_attribute: str = ..., on_exception: CallbacksArg = ...,
                 title: str = ..., show_conditions: bool = ..., show_state_attributes: bool = ...,
                 show_auto_transitions: bool = ..., use_pygraphviz: bool = ..., **kwargs: Dict[str, Any]) -> None: ...
    def _init_graphviz_engine(self, use_pygraphviz: bool) -> Type[BaseGraph]: ...
    def _get_graph(self, model: GraphModelProtocol, title: Optional[str] = ..., force_new: bool = ...,
                   show_roi: bool = ...) -> GraphProtocol: ...
    def get_combined_graph(self, title: Optional[str] = ..., force_new: bool = ...,
                           show_roi: bool = ...) -> GraphProtocol: ...
    def add_model(self, model: Union[Union[Literal['self'], object], List[Union[Literal['self'], object]]],
                  initial: Optional[StateIdentifier] = ...) -> None: ...
    def add_states(self, states: Union[Sequence[StateConfig], StateConfig],
                   on_enter: CallbacksArg = ..., on_exit: CallbacksArg = ...,
                   ignore_invalid_triggers: Optional[bool] = ..., **kwargs: Dict[str, Any]) -> None: ...
    def add_transition(self, trigger: str,
                       source: Union[StateIdentifier, List[StateIdentifier]],
                       dest: Optional[StateIdentifier] = ...,
                       conditions: CallbacksArg = ..., unless: CallbacksArg = ...,
                       before: CallbacksArg = ..., after: CallbacksArg = ..., prepare: CallbacksArg = ...,
                       **kwargs: Dict[str, Any]) -> None: ...


class NestedGraphTransition(TransitionGraphSupport, NestedTransition): ...


class HierarchicalGraphMachine(GraphMachine, HierarchicalMarkupMachine):  # type: ignore
    transition_cls: Type[NestedGraphTransition]
