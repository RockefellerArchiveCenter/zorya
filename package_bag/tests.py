import json
import shutil
# import tarfile
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
                    RightsAssignerView, S3ObjectDownloaderView)

VALID_BAG_FIXTURE_DIR = join(settings.BASE_DIR, 'package_bag', 'fixtures', 'bags', 'valid')
INVALID_BAG_FIXTURE_DIR = join(settings.BASE_DIR, 'package_bag', 'fixtures', 'bags', 'invalid')
RIGHTS_FIXTURE_DIR = join(settings.BASE_DIR, 'package_bag', 'fixtures', 'rights')
PACKAGES_FIXTURE_DIR = join(settings.BASE_DIR, 'package_bag', 'fixtures', 'packages')


class TestHelpers(TestCase):

    def test_expected_filename(self):
        passing_filenames = ["7d24b2da347b48fe9e59d8c5d4424235.tar", "4b4334fba43a4cf4940f6c8e6d892f60.tar.gz"]
        failing_filenames = ["6163b89b00bb4c5cbfc50eb34cb49a75", "example_bag.tar"]
        for filename in passing_filenames:
            self.assertTrue(expected_file_name(filename))
        for filename in failing_filenames:
            self.assertFalse(expected_file_name(filename))


class TestS3Download(TestCase):
    fixtures = ["s3_download.json"]

    def setUp(self):
        self.factory = APIRequestFactory()

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
    def test_s3_download_view(self):
        self.configure_uploader(["4b4334fba43a4cf4940f6c8e6d892f60.tar"])
        request = self.factory.post(reverse("s3objectdownloader"))
        response = S3ObjectDownloaderView.as_view()(request)
        self.assertEqual(
            response.status_code, 200, "View error: {}".format(response.data))

    @mock_s3
    def test_get_list_to_download(self):
        """Tests that expected files are downloaded"""
        already_in_db = Bag.objects.get(pk=1).original_bag_name.split("/")[-1]
        objects_in_bucket = ["7d24b2da347b48fe9e59d8c5d4424235.tar", "4b4334fba43a4cf4940f6c8e6d892f60.tar", "example_file.txt"]
        objects_in_bucket.append(already_in_db)
        object_downloader = self.configure_uploader(objects_in_bucket)
        list_to_download = object_downloader.list_to_download()
        self.assertEqual(len(list_to_download), 2)

    @mock_s3
    def test_download_object_from_s3(self,):
        """Tests that object is downloaded from the S3 bucket to the source directory"""
        set_up_directories([settings.SRC_DIR])
        object_downloader = self.configure_uploader(["7d24b2da347b48fe9e59d8c5d4424235.tar"])
        object_to_download = "7d24b2da347b48fe9e59d8c5d4424235.tar"
        object_downloader.download_object_from_s3(object_to_download)
        self.assertIn(object_to_download, listdir(object_downloader.src_dir))

    @mock_s3
    def test_delete_object_from_s3(self,):
        """Tests that object is deleted from the S3 bucket"""
        set_up_directories([settings.SRC_DIR])
        object_downloader = self.configure_uploader(["7d24b2da347b48fe9e59d8c5d4424235.tar"])
        object_to_delete = "7d24b2da347b48fe9e59d8c5d4424235.tar"
        object_downloader.delete_object_from_s3(object_to_delete)
        self.assertNotIn(object_to_delete, object_downloader.list_to_download())


class BaseTest(TestCase):
    def setUp(self):
        self.expected_count = randint(1, 10)
        with open(join(RIGHTS_FIXTURE_DIR, 'rights_data.json')) as json_file:
            self.rights_json = json.load(json_file)
        with open(join(RIGHTS_FIXTURE_DIR, 'rights_service_response.json')) as json_file:
            self.rights_service_response = json.load(json_file)
        set_up_directories([settings.TMP_DIR, settings.SRC_DIR, settings.DEST_DIR])

    def tearDown(self):
        for d in [settings.TMP_DIR, settings.SRC_DIR, settings.DEST_DIR]:
            if isdir(d):
                shutil.rmtree(d)


class TestBagDiscoverer(BaseTest):

    def test_run(self):
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


class TestRightsAssigner(BaseTest):

    @patch('package_bag.routines.post')
    def test_run(self, mock_rights):
        """Ensures that rights are correctly retrieved and assigned."""
        add_bags_to_db(settings.TMP_DIR, self.expected_count)
        mock_rights.return_value.status_code = 200
        mock_rights.return_value.json.return_value = self.rights_service_response
        for bag in Bag.objects.filter(process_status=Bag.DISCOVERED):
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


class TestPackageMaker(BaseTest):

    def test_run(self):
        """Ensures that packages are correctly created."""
        add_bags_to_db(settings.TMP_DIR, self.expected_count, rights_data=self.rights_json, process_status=Bag.ASSIGNED_RIGHTS)
        copy_binaries(VALID_BAG_FIXTURE_DIR, settings.SRC_DIR)
        for bag in Bag.objects.filter(process_status=Bag.ASSIGNED_RIGHTS):
            create_package = PackageMaker().run()
            self.assertIsNot(False, create_package)
            self.assertEqual(
                len(listdir(settings.TMP_DIR)), 0,
                "Temporary directory is not empty.")
        self.assertEqual(
            len(listdir(settings.DEST_DIR)), self.expected_count,
            "Incorrect number of binaries in destination directory.")


class TestPackage(BaseTest):

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


class TestPackageArchiver(BaseTest):

    @ patch('package_bag.routines.post')
    def test_deliver_package(self, mock_post):
        """Ensures that packages are delivered correctly."""
        add_bags_to_db(settings.TMP_DIR, self.expected_count, rights_data=self.rights_json, process_status=Bag.TAR)
        copy_binaries(VALID_BAG_FIXTURE_DIR, settings.TMP_DIR)
        count = 0
        for bag in Bag.objects.filter(process_status=Bag.TAR):
            deliver_package = PackageDeliverer().run()
            self.assertIsNot(False, deliver_package)
            count += 1
        self.assertEqual(
            count, self.expected_count,
            "Incorrect number of bags processed.")
        self.assertEqual(
            mock_post.call_count, self.expected_count,
            "Incorrect number of update requests made.")


class TestViews(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        set_up_directories([settings.TMP_DIR, settings.SRC_DIR, settings.DEST_DIR])

    def test_routine_views(self):
        """S3ObjectDownloaderView is tested in the TestS3Download test case, due to the overlap of AWS setup work with the S3ObjectDownloader routine"""
        for view_str, view in [
                ("bagdiscoverer", BagDiscovererView),
                ("rightsassigner", RightsAssignerView),
                ("packagemaker", PackageMakerView),
                ("packagedeliverer", PackageDelivererView)]:
            request = self.factory.post(reverse(view_str))
            response = view.as_view()(request)
            self.assertEqual(
                response.status_code, 200, f"View error: {response.data} in {view}")

    def test_health_check_view(self):
        status = self.client.get(reverse('api_health_ping'))
        self.assertEqual(status.status_code, 200, "Wrong HTTP code")
