import functools
import inspect
import sys
import pprint

from . import opts

def mainfunc(name):
    def run_decorator(func):
        func.__signature__ = inspect.signature(func)

        @functools.wraps(func)
        def wrapped(**kwargs):
            kw = opts.coerce_options(func.__signature__, kwargs)
            pprint.pprint({'Options': kw})
            return func(**kw)

        if name == '__main__':
            options = opts.parse_options(func.__signature__, sys.argv)
            pprint.pprint({'Options': options})
            wrapped(**options)

        return wrapped

    return run_decorator
