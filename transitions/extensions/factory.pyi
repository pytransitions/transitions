from ..core import Machine, State
from .diagrams import GraphMachine, TransitionGraphSupport
from .locking import LockedMachine
from .markup import MarkupMachine
from .nesting import HierarchicalMachine, NestedEvent, NestedTransition
from transitions.extensions.asyncio import AsyncMachine, AsyncTransition,HierarchicalAsyncMachine ,NestedAsyncTransition
from typing import Any, Type, Dict, Tuple, Callable

class MachineFactory:
    @staticmethod
    def get_predefined(graph: bool = ..., nested: bool = ...,
                       locked: bool = ..., asyncio: bool = ...) -> Type[Machine]: ...

class NestedGraphTransition(TransitionGraphSupport, NestedTransition): ...
class HierarchicalMarkupMachine(MarkupMachine, HierarchicalMachine): ...

class HierarchicalGraphMachine(GraphMachine, HierarchicalMarkupMachine):
    transition_cls: NestedGraphTransition

class LockedHierarchicalMachine(LockedMachine, HierarchicalMachine):
    event_cls: NestedEvent
    def _get_qualified_state_name(self, state: State) -> str: ...

class LockedGraphMachine(GraphMachine, LockedMachine):
    @staticmethod
    def format_references(func): ...

class LockedHierarchicalGraphMachine(GraphMachine, LockedHierarchicalMachine):
    transition_cls: NestedGraphTransition
    event_cls: NestedEvent
    @staticmethod
    def format_references(func: Callable) -> str: ...

class AsyncGraphMachine(GraphMachine, AsyncMachine):
    transition_cls: AsyncTransition

class HierarchicalAsyncGraphMachine(GraphMachine, HierarchicalAsyncMachine):
    transition_cls: NestedAsyncTransition

_CLASS_MAP: Dict[Tuple[bool, bool, bool, bool], Machine]
