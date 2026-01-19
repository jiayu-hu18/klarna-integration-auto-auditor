"""
Main module tests
"""

import unittest
from src.main import main


class TestMain(unittest.TestCase):
    """Main function test class"""

    def test_main_function_exists(self):
        """Test that main function exists"""
        self.assertTrue(callable(main))


if __name__ == "__main__":
    unittest.main()
