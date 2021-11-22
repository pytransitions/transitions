"""
pytest configuration - Tests async functionality only when asyncio and contextvars are available (Python 3.7+)
"""
# imports are required to check whether the modules are available
# pylint: disable=unused-import

from os.path import basename
try:
    import asyncio
    import contextvars
    WITH_ASYNC = True
except ImportError:
    WITH_ASYNC = False

async_files = ['test_async.py', 'asyncio.py']


def pytest_ignore_collect(path):
    """ Text collection function executed by pytest"""
    if not WITH_ASYNC and basename(str(path)) in async_files:
        return True
    return False
