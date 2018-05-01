import functools
from .metadata import MetricMetadata
import pyformance.registry
import re
import time
from pyformance.registry import (clear, count_calls, dump_metrics,  # noqa
                                 global_registry, hist_calls, meter_calls,
                                 set_global_registry, time_calls)


class MetricsRegistry(pyformance.registry.MetricsRegistry):
    """An extension of the pyformance MetricsRegistry
    which accepts and manages dimensional data to emit to SignalFx
    """
    def __init__(self, clock=time):
        self.metadata = MetricMetadata()
        super(MetricsRegistry, self).__init__(clock=clock)

    def add(self, key, metric, **dims):
        """Adds custom metric instances to the registry with dimensions
        which are not created with their constructors default arguments
        """
        return super(MetricsRegistry, self).add(
            self.metadata.register(key, **dims), metric)

    def counter(self, key, **dims):
        """adds counter with dimensions to the registry"""
        return super(MetricsRegistry, self).counter(
            self.metadata.register(key, **dims))

    def histogram(self, key, **dims):
        """adds histogram with dimensions to the registry"""
        return super(MetricsRegistry, self).histogram(
            self.metadata.register(key, **dims))

    def gauge(self, key, gauge=None, default=float("nan"), **dims):
        """adds gauge with dimensions to the registry"""
        return super(MetricsRegistry, self).gauge(
            self.metadata.register(key, **dims), gauge=gauge, default=default)

    def meter(self, key, **dims):
        """adds meter with dimensions to the registry"""
        return super(MetricsRegistry, self).meter(
            self.metadata.register(key, **dims))

    def timer(self, key, **dims):
        """adds timer with dimensions to the registry"""
        return super(MetricsRegistry, self).timer(
            self.metadata.register(key, **dims))

    def clear(self):    # noqa flake8 complains that this is
                        # a redefinition of the imported clear,
                        # but obviously it isn't
        """clears the registered metrics and metadata"""
        self.metadata.clear()
        super(MetricsRegistry, self).clear()


# set global registry on import to the SignalFx MetricsRegistry
set_global_registry(MetricsRegistry())


class RegexRegistry(MetricsRegistry):
    """
    An extension of the pyformance RegexRegistry
    which accepts and manages dimensional data to emit to SignalFx
    """
    def __init__(self, pattern=None, clock=time):
        super(RegexRegistry, self).__init__(clock)
        if pattern is not None:
            self.pattern = re.compile(pattern)
        else:
            self.pattern = re.compile('^$')

    def _get_key(self, key):
        matches = self.pattern.finditer(key)
        key = '/'.join((v for match in matches for v in match.groups() if v))
        return key

    def timer(self, key, **dims):
        return super(RegexRegistry, self).timer(self._get_key(key), **dims)

    def histogram(self, key, **dims):
        return super(RegexRegistry, self).histogram(self._get_key(key), **dims)

    def counter(self, key, **dims):
        return super(RegexRegistry, self).counter(self._get_key(key), **dims)

    def gauge(self, key, gauge=None, default=float("nan"), **dims):
        return super(RegexRegistry, self).gauge(
            self._get_key(key), gauge=gauge, default=default, **dims)

    def meter(self, key, **dims):
        return super(RegexRegistry, self).meter(self._get_key(key), **dims)


def counter(key, **dims):
    """adds counter with dimensions to the global pyformance registry"""
    return global_registry().counter(key, **dims)


def histogram(key, **dims):
    """adds histogram with dimensions to the global pyformance registry"""
    return global_registry().histogram(key, **dims)


def meter(key, **dims):
    """adds meter with dimensions to the global pyformance registry"""
    return global_registry().meter(key, **dims)


def timer(key, **dims):
    """adds timer with dimensions to the global pyformance registry"""
    return global_registry().timer(key, **dims)


def gauge(key, gauge=None, default=float("nan"), **dims):
    """adds gauge with dimensions to the global pyformance registry"""
    return global_registry().gauge(key, gauge=gauge, default=default, **dims)


def count_calls_with_dims(**dims):
    """decorator to track the number of times a function is called."""
    def counter_wrapper(fn):
        @functools.wraps(fn)
        def fn_wrapper(*args, **kwargs):
            counter("%s_calls" %
                    pyformance.registry.get_qualname(fn), **dims).inc()
            return fn(*args, **kwargs)
        return fn_wrapper
    return counter_wrapper


def meter_calls_with_dims(**dims):
    """decorator to track the rate at which a function is called."""
    def meter_wrapper(fn):
        @functools.wraps(fn)
        def fn_wrapper(*args, **kwargs):
            meter("%s_calls" %
                  pyformance.registry.get_qualname(fn), **dims).mark()
            return fn(*args, **kwargs)
        return fn_wrapper
    return meter_wrapper


def hist_calls_with_dims(**dims):
    """decorator to check the distribution of return values of a
    function.
    """
    def hist_wrapper(fn):
        @functools.wraps(fn)
        def fn_wrapper(*args, **kwargs):
            _histogram = histogram(
                "%s_calls" % pyformance.registry.get_qualname(fn), **dims)
            rtn = fn(*args, **kwargs)
            if type(rtn) in (int, float):
                _histogram.update(rtn)
            return rtn
        return fn_wrapper
    return hist_wrapper


def time_calls_with_dims(**dims):
    """decorator to time the execution of the function."""
    def time_wrapper(fn):
        @functools.wraps(fn)
        def fn_wrapper(*args, **kwargs):
            _timer = timer("%s_calls" %
                           pyformance.registry.get_qualname(fn), **dims)
            with _timer.time(fn=pyformance.registry.get_qualname(fn)):
                return fn(*args, **kwargs)
        return fn_wrapper
    return time_wrapper
