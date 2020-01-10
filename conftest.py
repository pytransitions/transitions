from os.path import basename
try:
    import asyncio
    import contextvars
    with_async = True
except ImportError:
    with_async = False

async_files = ['test_async.py', 'asyncio.py']


def pytest_ignore_collect(path):
    if not with_async and basename(str(path)) in async_files:
        return True
    return False
