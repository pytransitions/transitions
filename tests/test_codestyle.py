import unittest
import pycodestyle


class TestCodeFormat(unittest.TestCase):
    def test_conformance(self):
        """Test that we conform to PEP-8."""
        style = pycodestyle.StyleGuide(quiet=False, ignore=['E501'])
        style.input_dir('transitions')
        # style.input_dir('tests')
        result = style.check_files()
        self.assertEqual(result.total_errors, 0,
                         "Found code style errors (and warnings).")
