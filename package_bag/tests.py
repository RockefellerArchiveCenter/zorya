import shutil
import json

from unittest.mock import patch
from os import listdir, makedirs, getcwd
from os.path import isdir, join

from django.test import TestCase

from .routines import DiscoverBags, GetRights, CreatePackage, DeliverPackage

from zorya import settings

# Create your tests here.

bag_fixture_dir = join(settings.BASE_DIR, 'fixtures', 'bags')
rights_fixture_dir = join(settings.BASE_DIR, 'fixtures', 'rights')


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
            # TO DO: copy fixture rights to where they need to go
        self.discover_bags()
        self.get_rights()
        self.create_package()
        # move fixtures into watched dir

    def discover_bags(self):
        discover = DiscoverBags().run()
        self.assertIsNot(False, discover)
        # make sure the right number of objects were processed
        # make sure that invalid bags were invalidated

    @patch('package_bag.routines.GetRights.retrieve_rights')
    def get_rights(self, mock_rights):
        """docstring for fname"""
        with open(join(rights_fixture_dir, '1.json')) as json_file:
            rights_json = json.load(json_file)
        mock_rights.return_value = rights_json
        get_rights = GetRights().run()
        self.assertIsNot(False, get_rights)

    def create_package(self):
        """docstring for test_create_package"""
        create_package = CreatePackage().run()
        self.assertIsNot(False, create_package)

    def test_deliver_package(self):
        """docstring for test_deliver_package"""
        deliver_package = DeliverPackage().run()
        self.assertIsNot(False, deliver_package)
