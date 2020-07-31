import json
import shutil
import tarfile
from datetime import datetime
from os import listdir, makedirs
from os.path import isdir, isfile, join
from random import choice, randint
from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory
from zorya import settings

from .models import Bag
from .routines import (BagDiscoverer, PackageDeliverer, PackageMaker,
                       RightsAssigner)
from .views import (BagDiscovererView, PackageDelivererView, PackageMakerView,
                    RightsAssignerView)

BAG_FIXTURE_DIR = join(settings.BASE_DIR, 'fixtures', 'bags')
RIGHTS_FIXTURE_DIR = join(settings.BASE_DIR, 'fixtures', 'rights')


class TestPackage(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.expected_count = randint(1, 10)
        with open(join(RIGHTS_FIXTURE_DIR, '1.json')) as json_file:
            self.rights_json = json.load(json_file)
        for d in [settings.TMP_DIR, settings.SRC_DIR, settings.DEST_DIR]:
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
        shutil.rmtree(settings.SRC_DIR)
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
        total_bags = len([i for i in listdir(BAG_FIXTURE_DIR)])
        expected = len([i for i in listdir(BAG_FIXTURE_DIR) if not i.startswith("invalid_")])
        shutil.rmtree(settings.SRC_DIR)
        shutil.copytree(BAG_FIXTURE_DIR, settings.SRC_DIR)
        count = 0
        while count < (total_bags + 1):
            discover = BagDiscoverer().run()
            count += 1
        self.assertTrue(isinstance(discover, tuple))
        self.assertTupleEqual(discover, ('No bags were found.', None), "Incorrect response when no bags are found.")
        self.assertEqual(len(Bag.objects.all()), expected, "Wrong number of bags saved in database.")
        self.assertEqual(len(listdir(settings.TMP_DIR)), expected, "Invalid bags were not deleted.")

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
        self.assertEqual(
            len(listdir(settings.TMP_DIR)), 0,
            "Temporary directory is not empty.")
        self.assertEqual(
            len(listdir(settings.DEST_DIR)), self.expected_count,
            "Incorrect number of binaries in destination directory.")
        for package in listdir(settings.DEST_DIR):
            with tarfile.open(join(settings.DEST_DIR, package), "r") as tf:
                names = tf.getnames()
                bag_id = package.replace(".tar.gz", "")
                expected = [bag_id, join(bag_id, package), join(bag_id, "{}.json".format(bag_id))]
                self.assertEqual(
                    set(expected), set(names),
                    "Incorrectly structured package: expected {} but got {}".format(expected, names))

    @patch('package_bag.routines.post')
    def test_deliver_package(self, mock_post):
        """Ensures that packages are delivered correctly."""
        self.add_bags_to_db(self.expected_count, rights_data=self.rights_json)
        self.copy_binaries(settings.DEST_DIR)
        deliver_package = PackageDeliverer().run()
        self.assertIsNot(False, deliver_package)
        self.assertEqual(
            len(deliver_package[1]), self.expected_count,
            "Incorrect number of bags processed.")
        self.assertEqual(
            mock_post.call_count, self.expected_count,
            "Incorrect number of update requests made.")

    def test_views(self):
        for view_str, view in [
                ("bagdiscoverer", BagDiscovererView),
                ("rightsassigner", RightsAssignerView),
                ("packagemaker", PackageMakerView),
                ("packagedeliverer", PackageDelivererView)]:
            request = self.factory.post(reverse(view_str))
            response = view.as_view()(request)
            self.assertEqual(
                response.status_code, 200, "View error: {}".format(response.data))

    def health_check(self):
        print('*** Getting status view ***')
        status = self.client.get(reverse('api_health_ping'))
        self.assertEqual(status.status_code, 200, "Wrong HTTP code")

    def tearDown(self):
        for d in [settings.TMP_DIR, settings.SRC_DIR, settings.DEST_DIR]:
            if isdir(d):
                shutil.rmtree(d)
