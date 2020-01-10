import os.path

collect_ignore = []
current_dir = os.path.dirname(os.path.abspath(__file__))

try:
    import asyncio
    import contextvars
except ImportError:
    collect_ignore.append(os.path.join(current_dir, "test_async.py"))
