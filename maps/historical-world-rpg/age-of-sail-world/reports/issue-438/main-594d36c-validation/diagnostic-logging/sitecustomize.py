"""Print unittest failures immediately; preserve standard result accounting."""
import functools
import traceback
import unittest


def _with_immediate_traceback(original):
    @functools.wraps(original)
    def record(self, test, err):
        result = original(self, test, err)
        self.stream.write("\nEARLY_UNITTEST_FAILURE " + test.id() + "\n")
        traceback.print_exception(*err, file=self.stream)
        self.stream.flush()
        return result
    return record


for _name in ("addError", "addFailure"):
    setattr(unittest.TextTestResult, _name,
            _with_immediate_traceback(getattr(unittest.TextTestResult, _name)))
