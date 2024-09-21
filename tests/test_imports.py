def test_imports() -> None:
    from transitions import Machine
    from transitions.extensions import GraphMachine, HierarchicalGraphMachine, HierarchicalMachine, LockedMachine
    from transitions.extensions import MachineFactory, LockedHierarchicalGraphMachine, LockedHierarchicalMachine
    from transitions.extensions import LockedGraphMachine
    try:
        # only available for Python 3
        from transitions.extensions import AsyncMachine, HierarchicalAsyncMachine
        from transitions.extensions import AsyncGraphMachine, HierarchicalAsyncGraphMachine
    except (ImportError, SyntaxError):  # pragma: no cover
        pass
