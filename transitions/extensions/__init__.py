"""
transitions.extensions
----------------------

Additional functionality such as hierarchical (nested) machine support, Graphviz-based diagram creation
and threadsafe execution of machine methods. Additionally, combinations of all those features are possible
and made easier to access with a convenience factory.
"""

from .diagrams import GraphMachine, HierarchicalGraphMachine
from .nesting import HierarchicalMachine
from .locking import LockedMachine

from .factory import MachineFactory, LockedHierarchicalGraphMachine
from .factory import LockedHierarchicalMachine, LockedGraphMachine

try:
    # only available for Python 3
    from .asyncio import AsyncMachine, HierarchicalAsyncMachine
    from .factory import AsyncGraphMachine, HierarchicalAsyncGraphMachine
except (ImportError, SyntaxError):
    pass
