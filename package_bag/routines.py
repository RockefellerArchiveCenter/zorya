import json
import tarfile
from os import listdir, mkdir, remove, rename
from os.path import isdir, join, splitext
from uuid import uuid4

import bagit
import bagit_profile
import boto3
from asterism.bagit_helpers import validate
from asterism.file_helpers import make_tarfile, remove_file_or_dir
from botocore.exceptions import ClientError
from package_bag.helpers import expected_file_name
from package_bag.serializers import BagSerializer
from requests import post
from zorya import settings

from .models import Bag


class S3ObjectDownloader(object):
    def __init__(self):
        region_name, access_key, secret_key, bucket = settings.S3
        s3 = boto3.resource(service_name='s3', region_name=region_name, aws_access_key_id=access_key, aws_secret_access_key=secret_key)
        self.bucket = s3.Bucket(bucket)
        self.src_dir = settings.SRC_DIR

    def run(self):
        downloaded = []
        files_to_download = self.get_list_to_download
        for file in files_to_download:
            downloaded_file = self.download_object_from_s3(file)
            downloaded.append(downloaded_file)
        msg = "Files downloaded." if len(downloaded) else "No files ready to be downloaded."
        return msg, downloaded

    def get_list_to_download(self):
        """Gets list of items to download from S3 bucket, and removes items which do no match criteria

        Returns:
            List of filenames (strings)"""
        files_in_bucket = [bucket_object.key for bucket_object in self.bucket.objects.all()]
        for filename in files_in_bucket:
            if not expected_file_name(filename):
                files_in_bucket.remove(filename)
            elif Bag.objects.filter(original_bag_name=join(self.src_dir, filename)):
                files_in_bucket.remove(filename)
        return files_in_bucket

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


class BagDiscoverer(object):
    """
    Validates bag structure and bag info file, renames bag with unique ID
    """

    def __init__(self):
        self.src_dir = settings.SRC_DIR
        self.tmp_dir = settings.TMP_DIR
        for dir in [self.src_dir, self.tmp_dir]:
            if not isdir(dir):
                raise Exception("Directory does not exist", dir)
        # TODO: check for json profile

    def run(self):
        bag = self.discover_next_bag()
        if bag:
            try:
                bag_id = self.unpack_rename(bag, self.tmp_dir)
                bag_path = join(self.tmp_dir, bag_id)
                validate(bag_path)
                bag_data = self.validate_metadata(bag_path)
                new_bag = Bag.objects.create(
                    original_bag_name=bag,
                    bag_identifier=bag_id,
                    bag_path=bag_path,
                    process_status=Bag.DISCOVERED)
                for key in ["Origin", "Rights-ID", "Start-Date", "End-Date"]:
                    setattr(new_bag, key.lower().replace("-", "_"), bag_data.get(key))
                new_bag.save()
            except Exception as e:
                remove_file_or_dir(bag_path)
                raise Exception("Error processing discovered bag {}: {}".format(bag, str(e)))
        msg = "Bag discovered, renamed and saved." if bag else "No bags were found."
        return (msg, bag_id) if bag else (msg, None)

    def discover_next_bag(self):
        """Looks in a given directory for compressed bags, adds to list to process"""
        bag = None
        for bag in listdir(self.src_dir):
            ext = splitext(bag)[-1]
            if ext in ['.tar''.tgz', '.gz']:
                bag = join(self.src_dir, bag)
        return bag

    def unpack_rename(self, bag_path, tmp):
        """Unpacks tarfile to a new directory with the name of the bag identifier (a UUID)"""
        bag_identifier = str(uuid4())
        tf = tarfile.open(bag_path, 'r')
        tf.extractall(tmp)
        original_bag_name = tf.getnames()[0]
        tf.close()
        rename(join(tmp, original_bag_name),
               join(tmp, bag_identifier))
        remove(bag_path)
        return bag_identifier

    def validate_metadata(self, bag_path):
        """Validates the bag-info.txt file against the bagit profile"""
        new_bag = bagit.Bag(bag_path)
        bagit_profile_json = "zorya_bagit_profile.json"
        with open(join(settings.BASE_DIR, "package_bag", bagit_profile_json), "r") as fp:
            data = json.load(fp)
        profile = bagit_profile.Profile(bagit_profile_json, profile=data)
        if not profile.validate(new_bag):
            raise TypeError(profile.report.errors)
        else:
            return new_bag.info


# how does something get sent from one bag to another? how does batching work?
class RightsAssigner(object):
    """Send rights IDs to external service and receive JSON in return"""

    def run(self):
        bags_with_rights = []
        for bag in Bag.objects.filter(process_status=Bag.DISCOVERED):
            try:
                rights_json = self.retrieve_rights(bag)
                bag.rights_data = rights_json
                bag.process_status = Bag.ASSIGNED_RIGHTS
                bag.save()
                bags_with_rights.append(bag.bag_identifier)
            except Exception as e:
                raise Exception(
                    "Error assigning rights to bag {}: {}".format(bag.bag_identifier, str(e)))

        msg = "Rights assigned." if len(bags_with_rights) else "No bags to assign rights to found."
        return msg, bags_with_rights

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


class PackageMaker(object):
    """Create JSON according to Ursa Major schema and package with bag"""

    def run(self):
        packaged = []
        unpackaged = Bag.objects.filter(process_status=Bag.ASSIGNED_RIGHTS)
        for bag in unpackaged:
            package_root = join(settings.DEST_DIR, bag.bag_identifier)
            package_path = "{}.tar.gz".format(package_root)
            bag_tar_filename = "{}.tar.gz".format(bag.bag_identifier)
            try:
                self.serialize_json(bag, package_root)
                make_tarfile(bag.bag_path, join(package_root, bag_tar_filename), remove_src=True)
                make_tarfile(package_root, package_path, remove_src=True)
                packaged.append(bag.bag_identifier)
                bag.process_status = Bag.PACKAGED
                bag.save()
            except Exception as e:
                raise Exception(
                    "Error making package for bag {}: {}".format(bag.bag_identifier, str(e)))
        msg = "Packages created." if len(packaged) else "No files ready for packaging."
        return msg, packaged

    def serialize_json(self, bag, package_root):
        """Serialize JSON to file"""
        bag_json = BagSerializer(bag).data
        mkdir(package_root)
        with open("{}.json".format(join(package_root, bag.bag_identifier)), "w",) as f:
            json.dump(bag_json, f, indent=4, sort_keys=True, default=str)


class PackageDeliverer(object):
    """Deliver package to Ursa Major"""

    def run(self):
        dest_dir = settings.DEST_DIR
        delivered = []
        not_delivered = Bag.objects.filter(process_status=Bag.PACKAGED)
        for bag in not_delivered:
            try:
                self.deliver_data(bag, dest_dir, settings.DELIVERY_URL)
                delivered.append(bag.bag_identifier)
                bag.process_status = Bag.DELIVERED
                bag.save()
            except Exception as e:
                raise Exception(
                    "Error delivering bag {}: {}".format(bag.bag_identifier, str(e))) from e
        msg = "Packages delivered." if len(delivered) else "No packages to deliver."
        return msg, delivered

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
