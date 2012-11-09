from datetime import datetime
import inspect
from sickbeard import logger

__author__ = 'Dean Gardiner'

class ElapsedErrorChecker():
    def __init__(self):
        self.events = []
        self.methods = {} # { <method>: [<events>] }

    def set(self, method, identifier = None):
        return ElapsedErrorCheckerState(self._buildName(method), identifier, datetime.now())

    def clock(self, state, result = None):
        if len(self.events) > 1000:
            self.events = []

        state.elapsed = datetime.now() - state.startTime
        state.result = result
        self.events.insert(0, state)
        if not self.methods.has_key(state.method):
            self.methods[state.method] = ElapsedErrorCheckerMethod()
        self.methods[state.method].append(state)
        logger.log("\"" + str(state.method) + "\" = " + str(state.elapsed))

    def _buildName(self, x):
        if inspect.ismethod(x):
            return self._buildName(x.im_self) + '.' + x.__name__
        elif inspect.isclass(x.__class__):
            return x.__class__.__name__

class ElapsedErrorCheckerMethod():
    def __init__(self):
        self.events = []

    def append(self, state):
        self.events.append(state)

    def __len__(self):
        return len(self.events)

    def events_times(self):
        times = []
        for t in self.events:
            times.append(t.elapsed.total_seconds())
        return times

    def events_min(self):
        return min(self.events_times())

    def events_max(self):
        return max(self.events_times())

    def events_avg(self):
        times = self.events_times()
        return sum(times) / len(times)

class ElapsedErrorCheckerState():
    def __init__(self, method, identifier, startTime):
        self.method = method
        self.ident = identifier
        self.startTime = startTime
        self.elapsed = None
        self.result = None

elapsedErrorChecker = ElapsedErrorChecker()