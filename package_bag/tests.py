import json
import shutil
from datetime import datetime
from os import getcwd, listdir, makedirs
from os.path import isdir, join
from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase

from zorya import settings

from .routines import (BagDiscoverer, PackageDeliverer, PackageMaker,
                       RightsAssigner)
from .models import Bag


BAG_FIXTURE_DIR = join(settings.BASE_DIR, 'fixtures', 'bags')
RIGHTS_FIXTURE_DIR = join(settings.BASE_DIR, 'fixtures', 'rights')


class TestPackage(TestCase):

    def setUp(self):
        for d in [settings.TMP_DIR, settings.DEST_DIR]:
            if isdir(d):
                shutil.rmtree(d)
                makedirs(d)
            else:
                makedirs(d)

    def add_bags_to_db(self, count=5):
        for n in range(count):
            bag_id = str(uuid4())
            bag = Bag.objects.create(
                original_bag_name=bag_id,
                bag_identifier=bag_id,
                bag_path=join(
                    settings.TMP_DIR,
                    bag_id),
                origin="digitization",
                rights_id="1 2 3",
                end_date=datetime.now().strftime("%Y-%m-%d"))

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
        # load data into database
        self.add_bags_to_db()
        with open(join(RIGHTS_FIXTURE_DIR, '1.json')) as json_file:
            rights_json = json.load(json_file)
        mock_rights.return_value = rights_json
        assign_rights = RightsAssigner().run()
        self.assertIsNot(False, assign_rights)
        # make sure mock_rights was called the correct number of times
        # make sure bag.rights is not null and matches rights_json

    def test_create_package(self):
        """Ensures that packages are correctly created."""
        # move binaries into TMP_DIR
        # load data into database
        create_package = PackageMaker().run()
        self.assertIsNot(False, create_package)
        # make sure TMP_DIR is empty
        # test the number of objects in DEST_DIR

    # patch the POST method here
    def test_deliver_package(self):
        """Ensures that packages are delivered correctly."""
        # move binaries into DEST_DIR
        # load data into database
        deliver_package = PackageDeliverer().run()
        self.assertIsNot(False, deliver_package)
        # ensure the mock was called the correct number of times
        # ensure the mock was called with the correct data

    def tearDown(self):
        for d in [settings.TMP_DIR, settings.SRC_DIR, settings.DEST_DIR]:
            if isdir(d):
                shutil.rmtree(d)
