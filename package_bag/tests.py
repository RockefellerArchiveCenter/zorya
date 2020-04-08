from django.test import TestCase

from .routines import DiscoverBags, GetRights, CreatePackage, DeliverPackage

# Create your tests here.


class TestPackage(TestCase):
    """docstring for TestPackage"""

    def setUp(self):
        pass
        # move fixtures into watched dir

    def test_discover_bags(self):
        discover = DiscoverBags().run()
        self.assertIsNot(False, discover)
        # make sure the right number of objects were processed
        # make sure that invalid bags were invalidated

    def test_get_rights(self):
        """docstring for fname"""
        get_rights = GetRights().run()
        self.assertIsNot(False, get_rights)

    def test_create_package(self):
        """docstring for test_create_package"""
        create_package = CreatePackage().run()
        self.assertIsNot(False, create_package)

    def test_deliver_package(self):
        """docstring for test_deliver_package"""
        deliver_package = DeliverPackage().run()
        self.assertIsNot(False, deliver_package)
