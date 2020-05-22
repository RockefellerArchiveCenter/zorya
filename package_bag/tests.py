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

    def setUp(self):
        for d in [settings.TMP_DIR, settings.DEST_DIR]:
            if isdir(d):
                shutil.rmtree(d)
                makedirs(d)
            else:
                makedirs(d)

    def test_discover_bags(self):
        """Ensures that bags are correctly discovered."""
        shutil.copytree(bag_fixture_dir, settings.SRC_DIR)
        discover = DiscoverBags().run()
        self.assertIsNot(False, discover)
        # make sure the right number of objects were processed
        # make sure that invalid bags were invalidated

    @patch('package_bag.routines.GetRights.retrieve_rights')
    def test_get_rights(self, mock_rights):
        """Ensures that rights are correctly retrieved and assigned."""
        with open(join(rights_fixture_dir, '1.json')) as json_file:
            rights_json = json.load(json_file)
        mock_rights.return_value = rights_json
        get_rights = GetRights().run()
        self.assertIsNot(False, get_rights)

    def test_create_package(self):
        """Ensures that packages are correctly created."""
        create_package = CreatePackage().run()
        self.assertIsNot(False, create_package)

    def test_deliver_package(self):
        """Ensures that packages are delivered correctly."""
        deliver_package = DeliverPackage().run()
        self.assertIsNot(False, deliver_package)

    def tearDown(self):
        for d in [settings.TMP_DIR, settings.SRC_DIR, settings.DEST_DIR]:
            if isdir(d):
                shutil.rmtree(d)
