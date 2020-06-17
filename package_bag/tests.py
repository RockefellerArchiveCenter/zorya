import json
import shutil
from datetime import datetime
from os import listdir, makedirs
from os.path import isdir, isfile, join
from random import choice, randint
from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase
from zorya import settings

from .models import Bag
from .routines import (BagDiscoverer, PackageDeliverer, PackageMaker,
                       RightsAssigner)

BAG_FIXTURE_DIR = join(settings.BASE_DIR, 'fixtures', 'bags')
RIGHTS_FIXTURE_DIR = join(settings.BASE_DIR, 'fixtures', 'rights')


class TestPackage(TestCase):

    def setUp(self):
        self.expected_count = randint(1, 10)
        with open(join(RIGHTS_FIXTURE_DIR, '1.json')) as json_file:
            self.rights_json = json.load(json_file)
        for d in [settings.TMP_DIR, settings.DEST_DIR]:
            if isdir(d):
                shutil.rmtree(d)
                makedirs(d)
            else:
                makedirs(d)

    def add_bags_to_db(self, count=5, rights_data=None):
        for n in range(count):
            bag_id = str(uuid4())
            Bag.objects.create(
                original_bag_name=bag_id,
                bag_identifier=bag_id,
                bag_path=join(
                    settings.TMP_DIR,
                    bag_id),
                origin="digitization",
                rights_id="1 2 3",
                rights_data=rights_data,
                end_date=datetime.now().strftime("%Y-%m-%d"))

    def copy_binaries(self, dest_dir):
        shutil.copytree(BAG_FIXTURE_DIR, settings.SRC_DIR)
        binary = choice([i for i in listdir(settings.SRC_DIR) if isfile(join(settings.SRC_DIR, i)) and not i.startswith("invalid_")])
        for obj in Bag.objects.all():
            current_path = join(settings.SRC_DIR, "{}.tar.gz".format(obj.bag_identifier))
            shutil.copy(join(settings.SRC_DIR, binary), current_path)
            bag_id = BagDiscoverer().unpack_rename(current_path, settings.TMP_DIR)
            obj.bag_identifier = bag_id
            obj.bag_path = join(settings.TMP_DIR, bag_id)
            obj.save()

    def test_discover_bags(self):
        """Ensures that bags are correctly discovered."""
        expected = len([i for i in listdir(BAG_FIXTURE_DIR) if i.startswith("invalid_")])
        shutil.copytree(BAG_FIXTURE_DIR, settings.SRC_DIR)
        discover = BagDiscoverer().run()
        self.assertIsNot(False, discover)
        self.assertEqual(len(discover), expected, "Wrong number of bags processed.")
        self.assertEqual(len(Bag.objects.all()), expected, "Wrong number of bags saved in database.")

    @patch('package_bag.routines.RightsAssigner.retrieve_rights')
    def test_get_rights(self, mock_rights):
        """Ensures that rights are correctly retrieved and assigned."""
        self.add_bags_to_db(self.expected_count)
        mock_rights.return_value = self.rights_json
        assign_rights = RightsAssigner().run()
        self.assertIsNot(False, assign_rights)
        self.assertEqual(mock_rights.call_count, self.expected_count, "Incorrect number of calls to rights service.")
        for obj in Bag.objects.all():
            self.assertEqual(obj.rights_data, self.rights_json, "Rights JSON was not correctly added to bag in database.")

    def test_create_package(self):
        """Ensures that packages are correctly created."""
        self.add_bags_to_db(self.expected_count, rights_data=self.rights_json)
        self.copy_binaries(settings.TMP_DIR)
        create_package = PackageMaker().run()
        self.assertIsNot(False, create_package)
        print(listdir(settings.DEST_DIR))
        self.assertEqual(
            len(listdir(settings.TMP_DIR)), 0,
            "Temporary directory is not empty.")
        self.assertEqual(
            len(listdir(settings.DEST_DIR)), self.expected_count,
            "Incorrect number of binaries in destination directory.")

    @patch('package_bag.routines.post')
    def test_deliver_package(self, mock_post):
        """Ensures that packages are delivered correctly."""
        self.add_bags_to_db(self.expected_count, rights_data=self.rights_json)
        self.copy_binaries(settings.DEST_DIR)
        deliver_package = PackageDeliverer().run()
        self.assertIsNot(False, deliver_package)
        self.assertEqual(
            len(deliver_package), self.expected_count,
            "Incorrect number of bags processed.")
        self.assertEqual(
            mock_post.call_count, self.expected_count,
            "Incorrect number of update requests made.")

    def tearDown(self):
        for d in [settings.TMP_DIR, settings.SRC_DIR, settings.DEST_DIR]:
            if isdir(d):
                shutil.rmtree(d)
