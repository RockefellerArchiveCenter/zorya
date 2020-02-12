from django.test import TestCase

from .routines import DiscoverBag

# Create your tests here.

class TestPackage(TestCase):
    """docstring for TestPackage"""

    def setUp(self):
        pass
        # move fixtures into watched dir

    def test_discover_bags(self):
        discover = DiscoverBag().process_bags()
        self.assertIsNot(False, discover)
        # make sure the right number of objects were processed
        # make sure that invalid bags were invalidated