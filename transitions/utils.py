import sys

if sys.version_info >= (3,):
    def callable(obj):
        return hasattr(obj, '__call__')
else:
    callable = callable


def get_callable(name):
    """
    Converts path to a callable into callable
    :param name: (string) Path to a callable
    :return: callable
    """
    try:
        mod, name = name.rsplit('.', 1)
    except ValueError:
        raise ImportError('No module named {}'.format(name))
    m = __import__(mod)
    for n in mod.split('.')[1:]:
        m = getattr(m, n)
    try:
        func = getattr(m, name)
    except AttributeError, exc:
        raise ImportError(exc.message)
    if callable(func):
        return func
    else:
        raise ImportError('\'module\' object is not callable')
