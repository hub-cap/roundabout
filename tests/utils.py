import json
import os
import unittest

from roundabout.config import Config

def testdata(filename):
    return os.path.join(os.path.dirname(__file__), "data", filename)

def load(filename):
    with open(filename) as fp:
        return json.JSONDecoder().decode(fp.read())

def reset_config():
    # Reset config
    Config.__shared_state__.clear()

class was_called(object):
    def __init__(self, method):
        self.was_called = False
        self.method = method
    
    def __call__(self, *args, **kwargs):
        try:
            self.method(*args, **kwargs)
        finally:
            self.was_called = True

    def __eq__(self):
        return self.was_called

class TestHelper(unittest.TestCase):
    def assertCalled(self, bound_method, caller, *args, **kwargs):
        bound_method = was_called(bound_method)
        caller(*args, **kwargs)
        self.assertTrue(bound_method)
