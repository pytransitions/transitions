from typing import Any, List, Dict, Union, Optional
from logging import Logger

from .diagrams_base import BaseGraph
from ..core import ModelState

try:
    from pygraphviz import AGraph
except ImportError:
    class AGraph:  # type: ignore

        style_attributes: Dict[str, Union[str, Dict[str, Union[str, Dict[str, str]]]]]

_LOGGER: Logger


class Graph(BaseGraph):
    fsm_graph: AGraph  # type: ignore[no-any-unimported]
    def _add_nodes(self, states: List[Dict[str, str]],  # type: ignore[no-any-unimported]
                   container: AGraph) -> None: ...
    def _add_edges(self, transitions: List[Dict[str, str]],  # type: ignore[no-any-unimported]
                   container: AGraph) -> None: ...
    def generate(self) -> None: ...
    def get_graph(self, title: Optional[str] = ...,  # type: ignore[no-any-unimported]
                  roi_state: Optional[str] = ...) -> AGraph: ...
    def set_node_style(self, state: ModelState, style: str) -> None: ...
    def set_previous_transition(self, src: str, dst: str) -> None: ...
    def reset_styling(self) -> None: ...


class NestedGraph(Graph):
    seen_transitions: Any
    def __init__(self, *args: List, **kwargs: Dict[str, Any]) -> None: ...
    def _add_nodes(self,  # type: ignore[override, no-any-unimported]
                   states: List[Dict[str, Union[str, List[Dict[str, str]]]]],
                   container: AGraph, prefix: str = ..., default_style: str = ...) -> None: ...
    def _add_edges(self, transitions: List[Dict[str, str]],  # type: ignore[no-any-unimported]
                   container: AGraph) -> None: ...
    def set_node_style(self, state: ModelState, style: str) -> None: ...
    def set_previous_transition(self, src: str, dst: str) -> None: ...

def _get_subgraph(graph: AGraph, name: str) -> Optional[AGraph]: ...  # type: ignore[no-any-unimported]
def _copy_agraph(graph: AGraph) -> AGraph: ...  # type: ignore[no-any-unimported]
