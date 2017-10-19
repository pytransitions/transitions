from unittest import TestCase

from transitions.utils import get_callable


def test_func():
    pass


class TestTransitionsAddRemove(TestCase):

    def test_good_path(self):
        get_callable('tests.test_utils.test_func')

    def test_bad_path(self):
        with self.assertRaises(ImportError):
            get_callable('verybadstring')

    def test_non_existent_function(self):
        with self.assertRaises(ImportError):
            get_callable('tests.test_utils.AAAAA')

    def test_non_existent_module(self):
        with self.assertRaises(ImportError):
            get_callable('tests.test_utilsAAAAA.BBB')

    def test_module_not_callable(self):
        with self.assertRaises(ImportError):
            get_callable('tests.test_utils')
