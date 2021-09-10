from ..core import Machine as Machine
from .diagrams import GraphMachine as GraphMachine, TransitionGraphSupport as TransitionGraphSupport
from .locking import LockedMachine as LockedMachine
from .markup import MarkupMachine as MarkupMachine
from .nesting import HierarchicalMachine as HierarchicalMachine, NestedEvent as NestedEvent, NestedTransition as NestedTransition
from transitions.extensions.asyncio import AsyncMachine as AsyncMachine, AsyncTransition as AsyncTransition, HierarchicalAsyncMachine as HierarchicalAsyncMachine, NestedAsyncTransition as NestedAsyncTransition
from typing import Any

class AsyncMachine: ...
class AsyncTransition: ...
class HierarchicalAsyncMachine: ...
class NestedAsyncTransition: ...

class MachineFactory:
    @staticmethod
    def get_predefined(graph: bool = ..., nested: bool = ..., locked: bool = ..., asyncio: bool = ...): ...

class NestedGraphTransition(TransitionGraphSupport, NestedTransition): ...
class HierarchicalMarkupMachine(MarkupMachine, HierarchicalMachine): ...

class HierarchicalGraphMachine(GraphMachine, HierarchicalMarkupMachine):
    transition_cls: Any

class LockedHierarchicalMachine(LockedMachine, HierarchicalMachine):
    event_cls: Any
    def _get_qualified_state_name(self, state): ...

class LockedGraphMachine(GraphMachine, LockedMachine):
    @staticmethod
    def format_references(func): ...

class LockedHierarchicalGraphMachine(GraphMachine, LockedHierarchicalMachine):
    transition_cls: Any
    event_cls: Any
    @staticmethod
    def format_references(func): ...

class AsyncGraphMachine(GraphMachine, AsyncMachine):
    transition_cls: Any

class HierarchicalAsyncGraphMachine(GraphMachine, HierarchicalAsyncMachine):
    transition_cls: Any

_CLASS_MAP: Any
