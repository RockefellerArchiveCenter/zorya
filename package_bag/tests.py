import json
import shutil
from os import getcwd, listdir, makedirs
from os.path import isdir, join
from random import randint
from unittest.mock import patch
from uuid import uuid4


from django.test import TestCase

from zorya import settings

from .routines import (BagDiscoverer, PackageDeliverer, PackageMaker,
                       RightsAssigner)
                       
from .models import Bag



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
                
    def generate_date(self):
        date = []
        date.append(str(randint(1910,1995)))
        date.append(str(randint(1,12)).zfill(2))
        date.append(str(randint(1,28)).zfill(2))
        return "-".join(date)
    
    def add_bags_to_db(self):
        count = 0
        while count < 5:
            bag_id = str(uuid4())
            bag = Bag.objects.create(
                original_bag_name=bag_id,
                bag_identifier=bag_id,
                bag_path=join(
                    settings.TMP_DIR,
                    bag_id),
                origin="digitization",
                rights_id="1 2 3",
                end_date=self.generate_date()
                )
            bag.save()
            count += 1

    def test_discover_bags(self):
        """Ensures that bags are correctly discovered."""
        shutil.copytree(bag_fixture_dir, settings.SRC_DIR)
        discover = BagDiscoverer().run()
        self.assertIsNot(False, discover)
        # make sure the right number of objects were processed
        # check number of objects stored in database matches number of objects processed
        # make sure that invalid bags were invalidated

    @patch('package_bag.routines.RightsAssigner.retrieve_rights')
    def test_get_rights(self, mock_rights):
        """Ensures that rights are correctly retrieved and assigned."""
        # load data into database
        self.add_bags_to_db()
        with open(join(rights_fixture_dir, '1.json')) as json_file:
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
