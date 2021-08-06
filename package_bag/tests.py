import json
import shutil
import tarfile
from os import listdir
from os.path import isdir, join
from random import randint
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rac_schemas import is_valid
from rest_framework.test import APIRequestFactory
from zorya import settings

from .models import Bag
from .routines import (BagDiscoverer, PackageDeliverer, PackageMaker,
                       RightsAssigner)
from .test_helpers import (END_DATE, RIGHTS_ID, add_bags_to_db, copy_binaries,
                           set_up_directories)
from .views import (BagDiscovererView, PackageDelivererView, PackageMakerView,
                    RightsAssignerView)

VALID_BAG_FIXTURE_DIR = join(settings.BASE_DIR, 'fixtures', 'bags', 'valid')
INVALID_BAG_FIXTURE_DIR = join(settings.BASE_DIR, 'fixtures', 'bags', 'invalid')
RIGHTS_FIXTURE_DIR = join(settings.BASE_DIR, 'fixtures', 'rights')


class TestPackage(TestCase):

    def setUp(self):
        self.expected_count = randint(1, 10)
        with open(join(RIGHTS_FIXTURE_DIR, 'rights_data.json')) as json_file:
            self.rights_json = json.load(json_file)
        with open(join(RIGHTS_FIXTURE_DIR, 'rights_service_response.json')) as json_file:
            self.rights_service_response = json.load(json_file)
        set_up_directories([settings.TMP_DIR, settings.SRC_DIR, settings.DEST_DIR])

    def test_discover_bags(self):
        """Ensures that bags are correctly discovered."""
        valid_bags = len([i for i in listdir(VALID_BAG_FIXTURE_DIR)])
        shutil.rmtree(settings.SRC_DIR)
        shutil.copytree(VALID_BAG_FIXTURE_DIR, settings.SRC_DIR)
        count = 0
        while count < (valid_bags + 1):
            discover = BagDiscoverer().run()
            count += 1
        self.assertTrue(isinstance(discover, tuple))
        self.assertTupleEqual(discover, ('No bags were found.', None), "Incorrect response when no bags are found.")
        self.assertEqual(len(Bag.objects.all()), valid_bags, "Wrong number of bags saved in database.")
        self.assertEqual(len(listdir(settings.TMP_DIR)), valid_bags, "Invalid bags were not deleted.")

        shutil.rmtree(settings.SRC_DIR)
        shutil.copytree(INVALID_BAG_FIXTURE_DIR, settings.SRC_DIR)
        with self.assertRaises(Exception) as exc:
            BagDiscoverer().run()
        self.assertIn("Error processing discovered bag", str(exc.exception))
        self.assertEqual(len(listdir(settings.TMP_DIR)), valid_bags)

    @patch('package_bag.routines.post')
    def test_get_rights(self, mock_rights):
        """Ensures that rights are correctly retrieved and assigned."""
        add_bags_to_db(settings.TMP_DIR, self.expected_count)
        mock_rights.return_value.status_code = 200
        mock_rights.return_value.json.return_value = self.rights_service_response
        assign_rights = RightsAssigner().run()
        mock_rights.assert_called_with(
            'http://aquila-web:8000/rights',
            json={'identifiers': RIGHTS_ID, 'start_date': None, 'end_date': END_DATE})
        self.assertIsNot(False, assign_rights)
        self.assertEqual(
            mock_rights.call_count, self.expected_count,
            "Incorrect number of calls to rights service.")
        for obj in Bag.objects.all():
            self.assertEqual(
                obj.rights_data, self.rights_service_response["rights_statements"],
                "Rights JSON was not correctly added to bag in database.")

    def test_create_package(self):
        """Ensures that packages are correctly created."""
        add_bags_to_db(settings.TMP_DIR, self.expected_count, rights_data=self.rights_json)
        copy_binaries(VALID_BAG_FIXTURE_DIR, settings.SRC_DIR)
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

    def test_serialize_json(self):
        """Ensures that valid JSON is created"""
        add_bags_to_db(settings.TMP_DIR, self.expected_count, rights_data=self.rights_json)
        copy_binaries(VALID_BAG_FIXTURE_DIR, settings.TMP_DIR)
        for bag in Bag.objects.filter(rights_data__isnull=False):
            package_root = join(settings.DEST_DIR, bag.bag_identifier)
            PackageMaker().serialize_json(bag, package_root)
            with open("{}.json".format(join(package_root, bag.bag_identifier)), "r") as f:
                serialized = json.load(f)
            self.assertTrue(is_valid(serialized, "{}_bag".format(bag.origin)))

    @patch('package_bag.routines.post')
    def test_deliver_package(self, mock_post):
        """Ensures that packages are delivered correctly."""
        add_bags_to_db(settings.TMP_DIR, self.expected_count, rights_data=self.rights_json)
        copy_binaries(VALID_BAG_FIXTURE_DIR, settings.TMP_DIR)
        deliver_package = PackageDeliverer().run()
        self.assertIsNot(False, deliver_package)
        self.assertEqual(
            len(deliver_package[1]), self.expected_count,
            "Incorrect number of bags processed.")
        self.assertEqual(
            mock_post.call_count, self.expected_count,
            "Incorrect number of update requests made.")

    def tearDown(self):
        for d in [settings.TMP_DIR, settings.SRC_DIR, settings.DEST_DIR]:
            if isdir(d):
                shutil.rmtree(d)


class TestViews(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        set_up_directories([settings.TMP_DIR, settings.SRC_DIR, settings.DEST_DIR])

    def test_routine_views(self):
        for view_str, view in [
                ("bagdiscoverer", BagDiscovererView),
                ("rightsassigner", RightsAssignerView),
                ("packagemaker", PackageMakerView),
                ("packagedeliverer", PackageDelivererView)]:
            request = self.factory.post(reverse(view_str))
            response = view.as_view()(request)
            self.assertEqual(
                response.status_code, 200, "View error: {}".format(response.data))

    def test_health_check_view(self):
        status = self.client.get(reverse('api_health_ping'))
        self.assertEqual(status.status_code, 200, "Wrong HTTP code")
