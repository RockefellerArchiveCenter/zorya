import shutil
from os import listdir, makedirs, getcwd
from os.path import isdir, join

from django.test import TestCase

from .routines import DiscoverBags, GetRights, CreatePackage, DeliverPackage

from zorya import settings

# Create your tests here.

bag_fixture_dir = join(settings.BASE_DIR, 'fixtures', 'bags')

class TestPackage(TestCase):
    """docstring for TestPackage"""

    def setUp(self):
        self.src_dir = settings.SRC_DIR
        self.tmp_dir = settings.TMP_DIR
        self.dest_dir = settings.DEST_DIR
        for d in [self.src_dir, self.tmp_dir, self.dest_dir]:
            if isdir(d):
                shutil.rmtree(d)
        shutil.copytree(bag_fixture_dir, self.src_dir)
        for dir in [self.dest_dir, self.tmp_dir]:
            makedirs(dir)
        # self.create_objects()
        # move fixtures into watched dir

    def test_discover_bags(self):
        discover = DiscoverBags().run()
        self.assertIsNot(False, discover)
        # make sure the right number of objects were processed
        # make sure that invalid bags were invalidated

    # def test_get_rights(self):
    #     """docstring for fname"""
    #     get_rights = GetRights().run()
    #     self.assertIsNot(False, get_rights)
    #
    # def test_create_package(self):
    #     """docstring for test_create_package"""
    #     create_package = CreatePackage().run()
    #     self.assertIsNot(False, create_package)
    #
    # def test_deliver_package(self):
    #     """docstring for test_deliver_package"""
    #     deliver_package = DeliverPackage().run()
    #     self.assertIsNot(False, deliver_package)
