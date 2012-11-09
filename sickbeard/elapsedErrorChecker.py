from datetime import datetime
import inspect
from sickbeard import logger

__author__ = 'Dean Gardiner'

class ElapsedErrorChecker():
    def __init__(self):
        self.events = []
        self.methods = {} # { <method>: [<events>] }

    def set(self, method, identifier = None):
        if hasattr(method, 'msWarning') == False or hasattr(method, 'msError') == False:
            logger.log("Method does not have 'ElapsedMethodDecorator'", logger.ERROR)
            return None
        return ElapsedMethodState(method, ElapsedErrorChecker._buildName(method), identifier, datetime.now())

    def clock(self, state, result = None):
        if len(self.events) > 1000:
            self.events = []

        state.elapsed = datetime.now() - state.startTime
        state.result = result
        self.events.insert(0, state)
        if not self.methods.has_key(state.methodName):
            self.methods[state.methodName] = ElapsedMethodData(state.method.msWarning, state.method.msError)
        self.methods[state.methodName].append(state)
        logger.log("\"" + str(state.methodName) + "\" = " + str(state.elapsed))

    @staticmethod
    def _buildName(x):
        if inspect.ismethod(x):
            return ElapsedErrorChecker._buildName(x.im_self) + '.' + x.__name__
        elif inspect.isclass(x.__class__):
            return x.__class__.__name__

class ElapsedMethodData():
    def __init__(self, msWarning, msError):
        self.events = []
        self.msWarning = msWarning
        self.msError = msError

    def append(self, state):
        self.events.append(state)

    def __len__(self):
        return len(self.events)

    def events_times(self):
        times = []
        for t in self.events:
            times.append(t.elapsed.total_seconds() * 1000) # milliseconds
        return times

    def events_min(self):
        return min(self.events_times())

    def events_max(self):
        return max(self.events_times())

    def events_avg(self):
        times = self.events_times()
        return sum(times) / len(times)

class ElapsedMethodState():
    def __init__(self, method, methodName, identifier, startTime):
        self.methodName = methodName
        self.method = method

        self.ident = identifier

        self.startTime = startTime
        self.elapsed = None

        self.result = None

def ElapsedMethodDecorator(msWarning, msError):
    def decorator(target):
        target.msWarning = msWarning
        target.msError = msError
        return target
    return decorator

elapsedErrorChecker = ElapsedErrorChecker()