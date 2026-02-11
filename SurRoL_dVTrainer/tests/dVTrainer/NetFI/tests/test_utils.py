import threading

class ThreadWithReturn(threading.Thread):
    def __init__(self, target, args):
        super().__init__()
        self._target = target
        self._args = args
        self._result = None

    def run(self):
        self._result = self._target(*self._args)

    def join(self, timeout=None):
        super().join(timeout)
        return self._result