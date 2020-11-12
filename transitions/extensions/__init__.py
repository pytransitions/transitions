"""
transitions.extensions
----------------------

Additional functionality such as hierarchical (nested) machine support, Graphviz-based diagram creation
and threadsafe execution of machine methods. Additionally, combinations of all those features are possible
and made easier to access with a convenience factory.
"""

from .diagrams import GraphMachine
from .nesting import HierarchicalMachine
from .locking import LockedMachine

from .factory import MachineFactory, HierarchicalGraphMachine, LockedHierarchicalGraphMachine
from .factory import LockedHierarchicalMachine, LockedGraphMachine
from .factory import AsyncMachine, AsyncGraphMachine, HierarchicalAsyncMachine, HierarchicalAsyncGraphMachine
