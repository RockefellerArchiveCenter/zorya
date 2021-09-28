import json
import shutil
import tarfile
from os import listdir
from os.path import isdir, join
from random import randint
from unittest.mock import patch

import boto3
from django.test import TestCase
from django.urls import reverse
from moto import mock_s3
from package_bag.helpers import expected_file_name
from rac_schemas import is_valid
from rest_framework.test import APIRequestFactory
from zorya import settings

from .models import Bag
from .routines import (BagDiscoverer, PackageDeliverer, PackageMaker,
                       RightsAssigner, S3ObjectDownloader)
from .test_helpers import (END_DATE, RIGHTS_ID, add_bags_to_db, copy_binaries,
                           set_up_directories)
from .views import (BagDiscovererView, PackageDelivererView, PackageMakerView,
                    RightsAssignerView)

VALID_BAG_FIXTURE_DIR = join(settings.BASE_DIR, 'fixtures', 'bags', 'valid')
INVALID_BAG_FIXTURE_DIR = join(settings.BASE_DIR, 'fixtures', 'bags', 'invalid')
RIGHTS_FIXTURE_DIR = join(settings.BASE_DIR, 'fixtures', 'rights')


class TestHelpers(TestCase):

    def test_expected_filename(self):
        passing_filenames = ["7d24b2da347b48fe9e59d8c5d4424235.tar", "4b4334fba43a4cf4940f6c8e6d892f60.tar.gz"]
        failing_filenames = ["6163b89b00bb4c5cbfc50eb34cb49a75", "example_bag.tar"]
        for filename in passing_filenames:
            self.assertTrue(expected_file_name(filename))
        for filename in failing_filenames:
            self.assertFalse(expected_file_name(filename))


class TestS3Download(TestCase):
    fixtures = [join(settings.BASE_DIR, "fixtures", "s3_download.json")]

    def configure_uploader(self, upload_list):
        """Sets up an 3ObjectDownloader with mocked s3 bucket and objects."""
        object_downloader = S3ObjectDownloader()
        region_name, access_key, secret_key, bucket = settings.S3
        s3 = boto3.resource(service_name='s3', region_name=region_name, aws_access_key_id=access_key, aws_secret_access_key=secret_key)
        s3.create_bucket(Bucket=bucket)
        s3_client = boto3.client('s3', region_name=region_name)
        object_downloader.bucket = s3.Bucket(bucket)
        for item in upload_list:
            s3_client.put_object(Bucket=bucket, Key=item, Body='')
        return object_downloader

    @mock_s3
    def test_get_list_to_download(self):
        """Test list contains one filename than is in the database."""
        object_downloader = self.configure_uploader(["7d24b2da347b48fe9e59d8c5d4424235.tar", "4b4334fba43a4cf4940f6c8e6d892f60.tar", "4b1bf39c6b6745408ac8de9a5aec34ba.tar"])
        list_to_download = object_downloader.list_to_download()
        self.assertEqual(len(list_to_download), 2)

    @mock_s3
    def test_download_object_from_s3(self,):
        set_up_directories([settings.SRC_DIR])
        object_downloader = self.configure_uploader(["7d24b2da347b48fe9e59d8c5d4424235.tar"])
        object_to_download = "7d24b2da347b48fe9e59d8c5d4424235.tar"
        object_downloader.download_object_from_s3(object_to_download)
        self.assertIn(object_to_download, listdir(object_downloader.src_dir))


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
        add_bags_to_db(settings.TMP_DIR, self.expected_count, rights_data=self.rights_json, process_status=Bag.ASSIGNED_RIGHTS)
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
        add_bags_to_db(settings.TMP_DIR, self.expected_count, rights_data=self.rights_json, process_status=Bag.ASSIGNED_RIGHTS)
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
        add_bags_to_db(settings.TMP_DIR, self.expected_count, rights_data=self.rights_json, process_status=Bag.PACKAGED)
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
