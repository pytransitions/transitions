from typing import Union, Callable, List, Optional, Iterable, Type, ClassVar, Tuple, Dict, Any, DefaultDict, Deque
from transitions.core import StateIdentifier, CallbacksArg, CallbackFunc, Machine, TransitionConfig, MachineConfig
from transitions.extensions.markup import MarkupConfig

_placeholder_body: str

def generate_base_model(config: Union[MachineConfig, MarkupConfig]) -> str: ...
