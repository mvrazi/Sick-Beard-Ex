from datetime import datetime
import inspect
from sickbeard import logger

__author__ = 'Dean Gardiner'

class ElapsedErrorChecker():
    def __init__(self):
        self.events = []

    def set(self, method, identifier = None):
        return ElapsedErrorCheckerState(self._buildName(method), identifier, datetime.now())

    def clock(self, state, result = None):
        if len(self.events) > 1000:
            self.events = []

        state.elapsed = datetime.now() - state.startTime
        state.result = result
        self.events.insert(0, state)
        logger.log("\"" + str(state.method) + "\" = " + str(state.elapsed))

    def _buildName(self, x):
        if inspect.ismethod(x):
            return self._buildName(x.im_self) + '.' + x.__name__
        elif inspect.isclass(x.__class__):
            return x.__class__.__name__

class ElapsedErrorCheckerState():
    def __init__(self, method, identifier, startTime):
        self.method = method
        self.ident = identifier
        self.startTime = startTime

elapsedErrorChecker = ElapsedErrorChecker()