from ..core import Event, EventData, Machine, State, Transition, CallbacksArg, Callback
from collections import defaultdict as defaultdict
from typing import OrderedDict, Union, List, Dict, Optional, Type, Tuple, Callable, Any
from logging import Logger
from enum import Enum

_LOGGER: Logger

def _build_state_list(state_tree, separator: str, prefix: Optional[List[str]] = ...) -> Union[str, List[str]]: ...
def resolve_order(state_tree: Dict[str, str]) -> List[List[str]]: ...


class FunctionWrapper:
    _func: Optional[Callable]
    def __init__(self, func, path) -> None: ...
    def add(self, func: Callable, path: List[str]) -> None: ...
    def __call__(self, *args, **kwargs): ...


class NestedEvent(Event):
    def trigger_nested(self, event_data: NestedEventData) -> bool: ...
    def _process(self, event_data: NestedEventData) -> bool: ...


class NestedEventData(EventData):
    state: Optional[NestedState]
    event: Optional[NestedEvent]
    machine: Optional[HierarchicalMachine]
    transition: Optional[NestedTransition]
    source_name: Optional[str]
    source_path: Optional[List[str]]


class NestedState(State):
    separator: str
    initial: Optional[str]
    events: Dict[NestedEvent]
    states: OrderedDict[NestedState]
    _scope: List[str]
    def __init__(self, name, on_enter: CallbacksArg = ..., on_exit: CallbacksArg = ...,
                 ignore_invalid_triggers: bool = ..., initial: Optional[str] = ...) -> None: ...
    def add_substate(self, state) -> None: ...
    def add_substates(self, states) -> None: ...
    def scoped_enter(self, event_data, scope=...) -> None: ...
    def scoped_exit(self, event_data, scope=...) -> None: ...
    @property
    def name(self): ...

NestedStateIdentifier = Union[str, Enum, NestedState]
NestedStateConfig =  Union[NestedStateIdentifier, Dict[str, Any], 'HierarchicalMachine']
StateTree = OrderedDict[str, Union['StateTree', NestedState]]

class NestedTransition(Transition):
    def _resolve_transition(self, event_data): ...
    def _change_state(self, event_data) -> None: ...
    def _enter_nested(self, root, dest, prefix_path, event_data): ...
    @staticmethod
    def _update_model(event_data, tree) -> None: ...
    def __deepcopy__(self, memo): ...

ScopeTuple = Tuple[Union[NestedState, 'HierarchicalMachine'], OrderedDict[str, NestedState],
                   Dict[str, NestedEvent], List[str]]

class HierarchicalMachine(Machine):
    state_cls: Type[NestedState]
    transition_cls: Type[NestedTransition]
    event_cls: Type[NestedEvent]
    states: OrderedDict[str, NestedState]
    events: Dict[str, NestedEvent]
    _stack: List[ScopeTuple]
    _initial: Optional[str]
    prefix_path: List[str]
    scoped: Union[NestedState, HierarchicalMachine]
    def __init__(self, *args, **kwargs) -> None: ...
    _next_scope: Optional[ScopeTuple]
    def __call__(self, to_scope: Optional[Union[ScopeTuple, str, Enum]] = ...): ...
    def __enter__(self) -> None: ...
    def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...
    def add_model(self, model, initial: Optional[NestedStateIdentifier] = ...) -> None: ...
    @property
    def initial(self): ...
    @initial.setter
    def initial(self, value: NestedStateIdentifier) -> None: ...
    def add_ordered_transitions(self, states: Optional[List[NestedState]] = ..., trigger: str = ..., loop: bool = ...,
                                loop_includes_initial: bool = ..., conditions: CallbacksArg = ...,
                                unless: CallbacksArg = ..., before: CallbacksArg = ..., after: CallbacksArg = ...,
                                prepare: CallbacksArg = ..., **kwargs) -> None: ...
    def add_states(self, states: Union[List[NestedStateConfig], NestedStateConfig], on_enter: CallbacksArg = ...,
                   on_exit: CallbacksArg = ..., ignore_invalid_triggers: Optional[bool] = ..., **kwargs) -> None: ...
    def add_transition(self, trigger: str, source: Union[NestedStateIdentifier, List[NestedStateIdentifier]],
                       dest: Optional[NestedStateIdentifier], conditions: CallbacksArg = ...,
                       unless: CallbacksArg = ..., before: CallbacksArg = ..., after: CallbacksArg = ...,
                       prepare: CallbacksArg = ..., **kwargs) -> None: ...
    def get_global_name(self, state: NestedStateIdentifier = ..., join: bool = ...) -> Union[str, List[str]]: ...
    def get_nested_state_names(self) -> List[str]: ...
    def get_nested_transitions(self, trigger: str = ..., src_path: Optional[List[str]] = ...,
                               dest_path: Optional[List[str]] = ...) -> List[NestedTransition]: ...
    def get_nested_triggers(self, src_path: Optional[List[str]] = ...) -> List[str]: ...
    def get_state(self, state: Union[str, Enum, List[str]], hint: Optional[List[str]] = ...) -> NestedState: ...
    def get_states(self, states: Union[str, Enum, List[Union[str, Enum]]]) -> List[NestedState]: ...
    def get_transitions(self, trigger: str = ..., source: NestedStateIdentifier = ...,
                        dest: NestedStateIdentifier = ..., delegate: bool = ...) -> List[NestedTransition]: ...
    def get_triggers(self, *args) -> List[str]: ...
    def has_trigger(self, trigger: str, state: Optional[NestedState] = ...) -> bool: ...
    def is_state(self, state_name: str, model: object, allow_substates: bool = ...): ...
    def on_enter(self, state_name: str, callback: Callback) -> None: ...
    def on_exit(self, state_name: str, callback: Callback) -> None: ...
    def set_state(self, state: Union[NestedStateIdentifier, List[NestedStateIdentifier]],
                  model: Optional[object] = ...) -> None: ...
    def to_state(self, model: object, state_name: str, *args, **kwargs) -> None: ...
    def trigger_event(self, model: object, trigger: str, *args, **kwargs) -> bool: ...
    def _add_model_to_state(self, state: NestedState, model: object) -> None: ...
    def _add_dict_state(self, state: Dict[str, Any], ignore_invalid_triggers: bool, remap: Optional[str, str],
                        **kwargs): ...
    def _add_enum_state(self, state: Enum, on_enter: CallbacksArg, on_exit: CallbacksArg, ignore_invalid_triggers: bool,
                        remap: Optional[Dict[str, str]], **kwargs): ...
    def _add_machine_states(self, state: HierarchicalMachine, remap: Optional[Dict[str, str]]): ...
    def _add_string_state(self, state: str, on_enter: CallbacksArg, on_exit: CallbacksArg,
                          ignore_invalid_triggers: bool, remap: Optional[Dict[str, str]], **kwargs): ...
    def _add_trigger_to_model(self, trigger: str, model: object) -> None: ...
    def build_state_tree(self, model_states: Union[str, Enum, List[Union[str, Enum]]],
                         separator: str, tree: Optional[StateTree] = ...): ...
    @classmethod
    def _create_transition(cls, *args, **kwargs) -> NestedTransition: ...
    @classmethod
    def _create_event(cls, *args, **kwargs) -> NestedEvent: ...
    @classmethod
    def _create_state(cls, *args, **kwargs) -> NestedState: ...
    def _get_enum_path(self, enum_state: Enum, prefix: Optional[List[str]] =...) -> List[str]: ...
    def _get_state_path(self, state: NestedState, prefix: Optional[List[str]] = ...) -> List[str]: ...
    def _check_event_result(self, res: bool, model: object, trigger: str) -> bool: ...
    def _get_trigger(self, model: object, trigger_name: str, *args, **kwargs) -> bool: ...
    def _has_state(self, state: NestedState, raise_error: bool = ...) -> bool: ...
    def _init_state(self, state: NestedState) -> None: ...
    def _recursive_initial(self, value: NestedStateIdentifier) -> Union[str, List[str]]: ...
    def _remap_state(self, state: NestedState, remap: Dict[str, str]) -> List[NestedTransition]: ...
    def _resolve_initial(self, models: List[object], state_name_path: List[str],
                         prefix: Optional[List[str]] = ...) -> str: ...
    def _set_state(self, state_name: Union[str, List[str]]) -> Union[str, Enum, List[Union[str, Enum]]]: ...
    def _trigger_event(self, event_data: NestedEventData, trigger: str) -> Optional[bool]: ...