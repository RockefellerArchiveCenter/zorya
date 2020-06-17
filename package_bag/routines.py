import json
import tarfile
from os import listdir, mkdir, remove, rename
from os.path import basename, join, splitext
from shutil import rmtree
from uuid import uuid4

import bagit
import bagit_profile
from package_bag.serializers import BagSerializer
from requests import post
from zorya import settings

from .models import Bag


class BagDiscoverer(object):
    """
    Validates bag structure and bag info file, renames bag with unique ID
    """

    def run(self):
        processed = []
        unprocessed = self.discover_bags(settings.SRC_DIR)
        for bag in unprocessed:
            try:
                bag_id = self.unpack_rename(bag, settings.TMP_DIR)
                bag_path = join(settings.TMP_DIR, bag_id)
                self.validate_structure(bag_path)
                self.validate_metadata(bag_path)
                new_bag = Bag.objects.create(
                    original_bag_name=bag,
                    bag_identifier=bag_id,
                    bag_path=bag_path)
                self.get_data(new_bag)
                processed.append(bag_id)
            except Exception as e:
                print(e)
        # what does this process bags function return? - you want to return something out of the view that indicates which objects were processed
        # e.g.: "{} bags discovered".format(len(processed)), processed
        msg = "Bags discovered." if len(processed) else "No bags were found."
        return msg, processed

    def discover_bags(self, src):
        """Looks in a given directory for compressed bags, adds to list to process"""
        bags_list = []
        for bag in listdir(src):
            ext = splitext(bag)[-1]
            if ext in ['.tgz', '.gz']:
                bags_list.append(join(src, bag))
        return bags_list

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

    def validate_structure(self, bag_path):
        """Validates a bag against the BagIt specification"""
        new_bag = bagit.Bag(bag_path)
        return new_bag.validate()

    def validate_metadata(self, bag_path):
        """Validates the bag-info.txt file against the bagit profile"""
        # TO DO: first validation that "BagIt-Profile-Identifier" exists
        new_bag = bagit.Bag(bag_path)
        if "BagIt-Profile-Identifier" not in new_bag.info:
            print("no bagit profile identifier")
            # TO DO: return exception
        else:
            profile = bagit_profile.Profile(
                new_bag.info.get("BagIt-Profile-Identifier"))
            # TO DO: exception if cannot retrieve profile
            if not profile.validate(new_bag):
                raise Exception(profile.report.errors)

    def get_data(self, bag):
        """Saves bag data from the bag-info.txt file"""
        new_bag = bagit.Bag(bag.bag_path)
        for key in ["Origin", "Rights-ID", "End-Date"]:
            setattr(bag, key.lower().replace("-", "_"), new_bag.info.get(key))
        bag.save()
        # TO DO: what is this returning?


# how does something get sent from one bag to another? how does batching work?
class RightsAssigner(object):
    """Send rights IDs to external service and receive JSON in return"""

    def run(self):
        url = "rights service url"
        apikey = "rights service apikey"
        bags_with_rights = []
        for bag in Bag.objects.filter(rights_data__isnull=True):
            try:
                rights_json = self.retrieve_rights(bag, url, apikey)
                bag.rights_data = rights_json
                bag.save()
                bags_with_rights.append(bag.bag_identifier)
            except Exception as e:
                print(e)
        # get rights ids from database
        # loop through rights ids
        # retrieve rights
        # save rights
        msg = "Rights assigned." if len(bags_with_rights) else "No bags to assign rights to found."
        return msg, bags_with_rights

    def retrieve_rights(self, bag, url, apikey):
        """Sends POST request to rights statement service, receives JSON in return"""
        # url for get request
        resp = post(
            url,
            data="data",  # TO DO: what data is sent to rights service? obviously includes rights ids
            headers={
                "Content-Type": "application/json",
                "apikey": apikey,
            },
        )
        # send get request
        # get serialized rights back as json
        # QUESTION: do we want to validate the json we get back?
        # return saved json
        return resp.json()


class PackageMaker(object):
    """Create JSON according to Ursa Major schema and package with bag"""

    def run(self):
        packaged = []
        unpackaged = Bag.objects.filter(rights_data__isnull=False)
        for bag in unpackaged:
            try:
                self.create_package(bag, BagSerializer(bag).data)
                packaged.append(bag.bag_identifier)
            except Exception as e:
                print(e)
        msg = "Packages created." if len(packaged) else "No files ready for packaging."
        return msg, packaged

    # TODO: There are a number of things that need to be replaced with asterism
    # helpers here. I'm also not sure it makes sense to delegate to this function
    # out of the run method - I think we could just call this all within that
    # method.
    def create_package(self, bag, bag_json):
        """Create package to send to Ursa Major"""
        package_root = join(settings.DEST_DIR, bag.bag_identifier)
        mkdir(package_root)
        with open("{}.json".format(join(package_root, bag.bag_identifier)), "w",) as f:
            json.dump(bag_json, f, indent=4, sort_keys=True, default=str)
        bag_tar_filename = "{}.tar.gz".format(bag.bag_identifier)
        with tarfile.open(join(package_root, bag_tar_filename), "w:gz") as tar:
            tar.add(
                bag.bag_path, arcname=basename(bag.bag_identifier))
        package_path = "{}.tar.gz".format(package_root)
        with tarfile.open(package_path, "w:gz") as tar:
            tar.add(
                package_root, arcname=basename(package_root))
        rmtree(bag.bag_path)
        rmtree(package_root)
        return package_path


class PackageDeliverer(object):
    """Deliver package to Ursa Major"""

    def run(self):
        dest_dir = settings.DEST_DIR
        delivered = []
        not_delivered = Bag.objects.filter(rights_data__isnull=False)
        for bag in not_delivered:
            try:
                self.deliver_data(bag, dest_dir, settings.DELIVERY_URL)
                delivered.append(bag.bag_identifier)
            except Exception as e:
                print(e)
        msg = "Packages delivered." if len(delivered) else "No packages to deliver."
        return msg, delivered

    def deliver_data(self, bag, dest_dir, url):
        """Send data to Ursa Major"""
        bag_data = join(
            dest_dir, bag.bag_identifier, "{}.json".format(bag.bag_identifier))
        r = post(
            url,
            json={
                "bag_data": bag_data,
                "origin": bag.origin,
                "identifier": bag.bag_identifier},
            headers={
                "Content-Type": "application/json"},
        )
        r.raise_for_status()
