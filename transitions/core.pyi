from logging import Logger
from functools import partial
from typing import Any, Optional, Callable, Union, Iterable, List, Dict, DefaultDict, Type, Deque, OrderedDict, Tuple

try:
    # Enums are supported for Python 3.4+ and Python 2.7 with enum34 package installed
    from enum import Enum, EnumMeta
except ImportError:
    # If enum is not available, create dummy classes for type checks
    class Enum:
        name: str
        value: Any

    class EnumMeta:
        pass

_LOGGER: Logger

Callback = Union[str, Callable]
CallbackList = Iterable[Callback]
CallbacksArg = Optional[Union[Callback, CallbackList]]
ModelState = Union[str, Enum, List]

def listify(obj: Union[None, list, tuple, EnumMeta, Any]) -> Union[list, tuple, EnumMeta]: ...

def _prep_ordered_arg(desired_length: int, arguments: CallbacksArg) -> CallbackList: ...

class State:
    dynamic_methods: List[str]
    _name: Union[str, Enum]
    ignore_invalid_triggers: bool
    on_enter: CallbackList
    on_exit: CallbackList
    def __init__(self, name, on_enter: CallbacksArg, on_exit: CallbacksArg,
                 ignore_invalid_triggers: bool = ...) -> None: ...
    @property
    def name(self) -> str: ...
    @property
    def value(self) -> Union[str, Enum]: ...
    def enter(self, event_data: EventData) -> None: ...
    def exit(self, event_data: EventData) -> None: ...
    def add_callback(self, trigger: str, func: Callback) -> None: ...
    def __repr__(self) -> str: ...

StateIdentifier = Union[str, Enum, State]
StateConfig =  Union[StateIdentifier, Dict[str, Any]]

class Condition:
    func: Callback
    target: bool
    def __init__(self, func: Callback, target: bool = ...) -> None: ...
    def check(self, event_data: EventData) -> bool: ...
    def __repr__(self) -> str: ...

class Transition:
    dynamic_methods: List[str]
    condition_cls: Type[Condition]
    source: str
    dest: str
    prepare: CallbackList
    before: CallbackList
    after: CallbackList
    conditions: List[Condition]
    def __init__(self, source: str, dest: str, conditions: Optional[Condition] = ...,
                 unless: CallbacksArg = ..., before: CallbacksArg = ..., after: CallbacksArg = ...,
                 prepare: CallbacksArg = ...) -> None: ...
    def _eval_conditions(self, event_data: EventData) -> bool: ...
    def execute(self, event_data: EventData) -> bool: ...
    def _change_state(self, event_data: EventData) -> None: ...
    def add_callback(self, trigger: str, func: Callback) -> None: ...
    def __repr__(self) -> str: ...

TransitionConfig = Union[List[str], Dict[str, Any], Transition]

class EventData:
    state: Optional[State]
    event: Optional[Event]
    machine: Optional[Machine]
    model: object
    args: Tuple[Any]
    kwargs: Dict[str, Any]
    transition: Optional[Transition]
    error: Optional[Exception]
    result: Optional[bool]
    def __init__(self, state: Optional[State], event: Optional[Event], machine: Machine, model: object,
                 args: Tuple[Any], kwargs: Dict[str, Any]) -> None: ...
    def update(self, state: Union[State, str, Enum]) -> None: ...
    def __repr__(self) -> str: ...

class Event:
    name: str
    machine: Machine
    transitions: DefaultDict[str, List[Transition]]
    def __init__(self, name: str, machine: Machine) -> None: ...
    def add_transition(self, transition: Transition) -> None: ...
    def trigger(self, model: object, *args, **kwargs) -> bool: ...
    def _trigger(self, event_data: EventData) -> bool: ...
    def _process(self, event_data: EventData) -> bool: ...
    def _is_valid_source(self, state: State) -> bool: ...
    def __repr__(self) -> str: ...
    def add_callback(self, trigger: str, func: Callback) -> None: ...

class Machine:
    separator: str
    wildcard_all: str
    wildcard_same: str
    state_cls: Type[State]
    transition_cls: Type[Transition]
    event_cls: Type[Event]
    self_literal: str
    _queued: bool
    _transition_queue: Deque[partial]
    _before_state_change: CallbackList
    _after_state_change: CallbackList
    _prepare_event: CallbackList
    _finalize_event: CallbackList
    _on_exception: CallbackList
    _initial: Optional[str]
    states: OrderedDict[str, State]
    events: Dict[str, Event]
    send_event: bool
    auto_transitions: bool
    ignore_invalid_triggers: Optional[bool]
    name: str
    model_attribute: str
    models: List[object]
    def __init__(self, model: Optional[Union[Machine.self_literal, object]]=...,
                 states: Optional[List[StateConfig]] = ...,
                 initial: Optional[StateIdentifier] = ...,
                 transitions: Optional[Union[TransitionConfig, List[TransitionConfig]]] = ..., send_event: bool = ...,
                 auto_transitions: bool = ..., ordered_transitions: bool = ...,
                 ignore_invalid_triggers: Optional[bool] = ...,
                 before_state_change: CallbacksArg = ..., after_state_change: CallbacksArg = ...,
                 name: str = ..., queued: bool = ...,
                 prepare_event: CallbacksArg = ..., finalize_event: CallbacksArg = ...,
                 model_attribute: str = ..., on_exception: CallbacksArg = ..., **kwargs) -> None: ...
    def add_model(self, model: Union[Union[Machine.self_literal, object], List[Union[Machine.self_literal, object]]],
                  initial: Optional[StateIdentifier] = ...) -> None: ...
    def remove_model(self, model: Union[Union[Machine.self_literal, object],
                                        List[Union[Machine.self_literal, object]]]) -> None: ...
    @classmethod
    def _create_transition(cls, *args, **kwargs) -> Transition: ...
    @classmethod
    def _create_event(cls, *args, **kwargs) -> Event: ...
    @classmethod
    def _create_state(cls, *args, **kwargs) -> State: ...
    @property
    def initial(self) -> str: ...
    @initial.setter
    def initial(self, value: StateIdentifier) -> None: ...
    @property
    def has_queue(self) -> bool: ...
    @property
    def model(self) -> Union[object, List[object]]: ...
    @property
    def before_state_change(self) -> CallbackList: ...
    @before_state_change.setter
    def before_state_change(self, value: CallbacksArg) -> None: ...
    @property
    def after_state_change(self) -> CallbackList: ...
    @after_state_change.setter
    def after_state_change(self, value: CallbacksArg) -> None: ...
    @property
    def prepare_event(self) -> CallbackList: ...
    @prepare_event.setter
    def prepare_event(self, value: CallbacksArg) -> None: ...
    @property
    def finalize_event(self) -> CallbackList: ...
    @finalize_event.setter
    def finalize_event(self, value: CallbacksArg) -> None: ...
    @property
    def on_exception(self) -> CallbackList: ...
    @on_exception.setter
    def on_exception(self, value: CallbacksArg) -> None: ...
    def get_state(self, state: Union[str, Enum]) -> State: ...
    def is_state(self, state: Union[str, Enum], model: object) -> bool: ...
    def get_model_state(self, model: object) -> State: ...
    def set_state(self, state: StateIdentifier, model: Optional[object] = ...) -> None: ...
    def add_state(self, *args, **kwargs) -> None: ...
    def add_states(self, states: Union[List[StateConfig], StateConfig],
                   on_enter: CallbacksArg = ..., on_exit: CallbacksArg = ...,
                   ignore_invalid_triggers: Optional[bool] = ..., **kwargs) -> None: ...
    def _add_model_to_state(self, state: State, model: object) -> None: ...
    def _checked_assignment(self, model: object, name: str, func: Callable) -> None: ...
    def _add_trigger_to_model(self, trigger: str, model: object) -> None: ...
    def _get_trigger(self, model: object, trigger_name: str, *args, **kwargs) -> bool: ...
    def get_triggers(self, *args) -> List[str]: ...
    def add_transition(self, trigger: str,
                       source: Union[StateIdentifier, List[StateIdentifier]],
                       dest: StateIdentifier, conditions: CallbacksArg = ..., unless: CallbacksArg = ...,
                       before: CallbacksArg = ..., after: CallbacksArg = ..., prepare: CallbacksArg = ...,
                       **kwargs) -> None: ...
    def add_transitions(self, transitions: Union[TransitionConfig, List[TransitionConfig]]) -> None: ...
    def add_ordered_transitions(self, states: Optional[List[State]] = ...,
                                trigger: str = ..., loop: bool = ...,
                                loop_includes_initial: bool = ...,
                                conditions: CallbacksArg = ..., unless: CallbacksArg = ..., before: CallbacksArg = ...,
                                after: CallbacksArg = ..., prepare: CallbacksArg = ..., **kwargs) -> None: ...
    def get_transitions(self, trigger: str = ...,
                        source: StateIdentifier = ..., dest: StateIdentifier = ...) -> List[Transition]: ...
    def remove_transition(self, trigger: str, source: str = ..., dest: str = ...) -> None: ...
    def dispatch(self, trigger: str, *args, **kwargs) -> bool: ...
    def callbacks(self, funcs: Iterable[Union[str, Callable]], event_data: EventData) -> None: ...
    def callback(self, func: Union[str, Callable], event_data: EventData) -> None: ...
    @staticmethod
    def resolve_callable(func: Union[str, Callable], event_data: EventData): ...
    def _has_state(self, state: StateIdentifier, raise_error: bool = ...) -> bool: ...
    def _process(self, trigger: partial) -> bool: ...
    @classmethod
    def _identify_callback(cls, name: str) -> Tuple[Optional[str], Optional[str]]: ...
    def __getattr__(self, name: str) -> Any: ...

class MachineError(Exception):
    value: str
    def __init__(self, value: str) -> None: ...
    def __str__(self) -> str: ...