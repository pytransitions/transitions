# only import TestAsync if asyncio and contextvars are available
# otherwise syntax (Python 2) or import errors (Python before 3.7) occur

try:
    import asyncio
    import contextvars
    from .utils_async import TestAsync
except (ImportError, SyntaxError):
    pass
