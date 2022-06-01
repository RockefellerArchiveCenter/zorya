import json
import tarfile
from os import mkdir, remove, rename
from os.path import isdir, join
from uuid import uuid4

import bagit
import bagit_profile
import boto3
from asterism.bagit_helpers import validate
from asterism.file_helpers import make_tarfile
from botocore.exceptions import ClientError
from requests import post

from package_bag.helpers import expected_file_name
from package_bag.serializers import BagSerializer
from zorya import settings

from .models import Bag


class S3ClientMixin(object):
    """Mixin to handle communication with S3."""

    def __init__(self):
        region_name, access_key, secret_key, bucket = settings.S3
        s3 = boto3.resource(service_name='s3', region_name=region_name, aws_access_key_id=access_key, aws_secret_access_key=secret_key)
        self.bucket = s3.Bucket(bucket)


class S3ObjectFinder(S3ClientMixin):

    def run(self):
        list_to_download = self.list_to_download()
        for obj in list_to_download:
            new_bag = Bag.objects.create(
                original_bag_name=obj,
                bag_identifier=str(uuid4()),
                process_status=Bag.SAVED)
            new_bag.save()
        msg = "Saved bags to database." if list_to_download else "No bags in bucket."
        return msg, list_to_download if list_to_download else []

    def list_to_download(self):
        """Gets list of items to download from S3 bucket, and removes items which do no match criteria

        Returns:
            List of filenames (strings)"""
        files_in_bucket = [bucket_object.key for bucket_object in self.bucket.objects.all()]
        return [filename for filename in files_in_bucket if expected_file_name(filename) and not Bag.objects.filter(original_bag_name__contains=filename).exists()]


class BaseRoutine(object):
    """Base class which all routines (that start by looking at the database) inherit.

    Returns:
        msg (str): human-readable representation of the routine outcome

    Subclasses should implement a `process_bag` method which executes logic on
    one bag. They should also set the following attributes:
        start_process_status (int): a Bag process status which determines the starting
            queryset.
        end_process_status (int): a Bag process status which will be applied to
            Bags after they have been successfully processed.
        success_message (str): a message indicating that the routine completed
            successfully.
        idle_message (str): a message indicating that there were no objects for
            the routine to act on.
    """

    def run(self):
        if not Bag.objects.filter(process_status=self.in_process_status).exists():
            bag = Bag.objects.filter(process_status=self.start_process_status).first()
            if bag:
                bag.process_status = self.in_process_status
                bag.save()
                try:
                    self.process_bag(bag)
                except Exception:
                    bag.process_status = self.start_process_status
                    bag.save()
                    raise
                bag.process_status = self.end_process_status
                bag.save()
                msg = self.success_message
            else:
                msg = self.idle_message
        else:
            msg = "Service currently running"
            bag = None
        return msg, [bag.bag_identifier] if bag else []

    def process_bag(self, bag):
        raise NotImplementedError("You must implement a `process_bag` method")


class S3ObjectDownloader(BaseRoutine, S3ClientMixin):
    start_process_status = Bag.SAVED
    in_process_status = Bag.DOWNLOADING
    end_process_status = Bag.DOWNLOADED
    success_message = "File downloaded."
    idle_message = "No files ready to be downloaded."

    def __init__(self):
        super().__init__()
        self.src_dir = settings.SRC_DIR

    def process_bag(self, bag):
        downloaded_file = self.download_object_from_s3(bag.original_bag_name)
        self.delete_object_from_s3(bag.original_bag_name)
        bag.bag_path = downloaded_file

    def download_object_from_s3(self, filename):
        """Downloads an object from S3 to the source directory

        Args:
            filename (str): filename which should be the S3 object key as well as the filename to download to

        Returns:
            downloaded_file (str): full path to downloaded file"""
        downloaded_file = join(self.src_dir, filename)
        try:
            self.bucket.download_file(filename, downloaded_file)
            return downloaded_file
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                raise Exception("The object does not exist.")
            else:
                raise Exception("Error connecting to AWS: {}".format(e))

    def delete_object_from_s3(self, filename):
        """Deletes an object from an S3 bucket

        Args:
            filename (str): filename which should be the S3 object key

        Returns:
            downloaded_file (str): full path to downloaded file"""
        try:
            self.bucket.delete_objects(Delete={'Objects': [{'Key': filename}]})
        except ClientError as e:
            raise Exception("Error connecting to AWS: {}".format(e))


class BagDiscoverer(BaseRoutine):
    """
    Validates bag structure and bag info file, renames bag with unique ID
    """
    start_process_status = Bag.DOWNLOADED
    in_process_status = Bag.DISCOVERING
    end_process_status = Bag.DISCOVERED
    success_message = "Bag renamed, unpacked, and validated."
    idle_message = "No bags were found."

    def __init__(self):
        self.src_dir = settings.SRC_DIR
        self.tmp_dir = settings.TMP_DIR
        for dir in [self.src_dir, self.tmp_dir]:
            if not isdir(dir):
                raise Exception("Directory does not exist", dir)

    def process_bag(self, bag):
        bag.bag_path = self.unpack_rename(bag)
        bag.save()
        validate(bag.bag_path)
        bag_data = self.validate_metadata(bag)
        for key in ["Origin", "Rights-ID", "Start-Date", "End-Date"]:
            setattr(bag, key.lower().replace("-", "_"), bag_data.get(key))

    def unpack_rename(self, bag):
        """Unpacks tarfile to a new directory with the name of the bag identifier (a UUID)"""
        tf = tarfile.open(bag.bag_path, 'r')
        tf.extractall(self.tmp_dir)
        original_bag_name = tf.getnames()[0].split('/')[0]
        tf.close()
        rename(join(self.tmp_dir, original_bag_name),
               join(self.tmp_dir, bag.bag_identifier))
        remove(bag.bag_path)
        return join(self.tmp_dir, bag.bag_identifier)

    def validate_metadata(self, bag):
        """Validates the bag-info.txt file against the bagit profile"""
        new_bag = bagit.Bag(bag.bag_path)
        bagit_profile_json = "zorya_bagit_profile.json"
        with open(join(settings.BASE_DIR, "package_bag", bagit_profile_json), "r") as fp:
            data = json.load(fp)
        profile = bagit_profile.Profile(bagit_profile_json, profile=data)
        if not profile.validate(new_bag):
            raise TypeError(profile.report.errors)
        else:
            return new_bag.info


class RightsAssigner(BaseRoutine):
    """Send rights IDs to external service and receive JSON in return"""

    start_process_status = Bag.DISCOVERED
    in_process_status = Bag.ASSIGNING_RIGHTS
    end_process_status = Bag.ASSIGNED_RIGHTS
    success_message = "Rights assigned."
    idle_message = "No bags waiting for rights assignment."

    def process_bag(self, bag):
        bag.rights_data = self.retrieve_rights(bag)

    def retrieve_rights(self, bag):
        """Sends POST request to rights statement service, receives JSON in return"""
        url = settings.RIGHTS_URL
        resp = post(
            url,
            json={"identifiers": bag.rights_id, "start_date": bag.start_date, "end_date": bag.end_date}
        )
        if resp.status_code != 200:
            raise Exception("Error sending request to {}: {} {}".format(url, resp.status_code, resp.reason))
        return resp.json()['rights_statements']


class PackageMaker(BaseRoutine):
    """Create JSON according to Ursa Major schema and package with bag"""

    start_process_status = Bag.ASSIGNED_RIGHTS
    in_process_status = Bag.PACKAGING
    end_process_status = Bag.PACKAGED
    success_message = "Package created."
    idle_message = "No files ready for packaging."

    def process_bag(self, bag):
        package_root = join(settings.DEST_DIR, bag.bag_identifier)
        bag_tar_filename = "{}.tar.gz".format(bag.bag_identifier)
        self.serialize_json(bag, package_root)
        make_tarfile(bag.bag_path, join(package_root, bag_tar_filename), remove_src=True)

    def serialize_json(self, bag, package_root):
        """Serialize JSON to file"""
        bag_json = BagSerializer(bag).data
        mkdir(package_root)
        with open("{}.json".format(join(package_root, bag.bag_identifier)), "w",) as f:
            json.dump(bag_json, f, indent=4, sort_keys=True, default=str)


class PackageArchiver(BaseRoutine):
    """Create TAR of package"""

    start_process_status = Bag.PACKAGED
    in_process_status = Bag.ARCHIVING
    end_process_status = Bag.TAR
    success_message = "Package archive created."
    idle_message = "No files ready for archiving."

    def process_bag(self, bag):
        package_root = join(settings.DEST_DIR, bag.bag_identifier)
        package_path = "{}.tar.gz".format(package_root)
        make_tarfile(package_root, package_path, remove_src=True)


class PackageDeliverer(BaseRoutine):
    """Deliver package to Ursa Major"""

    start_process_status = Bag.TAR
    in_process_status = Bag.DELIVERING
    end_process_status = Bag.DELIVERED
    success_message = "Package delivered."
    idle_message = "No packages to deliver."

    def process_bag(self, bag):
        dest_dir = settings.DEST_DIR
        self.deliver_data(bag, dest_dir, settings.DELIVERY_URL)

    def deliver_data(self, bag, dest_dir, url):
        """Send data to Ursa Major"""
        bag_data = join(
            dest_dir, bag.bag_identifier, "{}.json".format(bag.bag_identifier))
        r = post(
            url,
            json={
                "data": bag_data,
                "origin": bag.origin,
                "bag_identifier": bag.bag_identifier},
            headers={
                "Content-Type": "application/json"},
        )
        r.raise_for_status()
