collect_ignore = []

try:
    import asyncio
    import contextvars
except ImportError:
    collect_ignore.append("tests/test_async.py")
