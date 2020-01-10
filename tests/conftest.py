collect_ignore = []

try:
    import asyncio
    import contextvars
except ImportError:
    collect_ignore.append("test_async.py")
