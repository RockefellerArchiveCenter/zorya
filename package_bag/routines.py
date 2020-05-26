from .models import Bag
from package_bag.serializers import BagSerializer

from uuid import uuid4
from shutil import move
import bagit
import bagit_profile
from os import listdir, rename, remove, mkdir
from os.path import join, splitext, basename
from requests import post
import tarfile
import json

from zorya import settings


class BagDiscoverer(object):
    """
    Validates bag structure and bag info file, renames bag with unique ID
    """

    def run(self):
        processed = []
        unprocessed = self.discover_bags(settings.SRC_DIR)
        for u in unprocessed:
            try:
                bag_id = self.unpack_rename(u, settings.TMP_DIR)
                bag = Bag.objects.create(
                    original_bag_name=u,
                    bag_identifier=bag_id,
                    bag_path=join(
                        settings.TMP_DIR,
                        bag_id))
                self.validate_structure(bag.bag_path)
                self.validate_metadata(bag.bag_path)
                self.get_data(bag)
                processed.append(bag.bag_identifier)
            except Exception as e:
                print(e)
        # what does this process bags function return? - you want to return something out of the view that indicates which objects were processed
        # e.g.: "{} bags discovered".format(len(processed)), processed
        return processed

    def discover_bags(self, src):
        """Looks in a given directory for compressed bags, adds to list to process"""
        bags_list = []
        for d in listdir(src):
            ext = splitext(d)[-1]
            if ext in ['.tgz', '.gz']:
                bags_list.append(join(src, d))
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
        # TO DO: first vlaidation that "BagIt-Profile-Identifier" exists
        new_bag = bagit.Bag(bag_path)
        if "BagIt-Profile-Identifier" not in new_bag.info:
            print("no bagit profile identifier")
            # TO DO: return exception
        else:
            profile = bagit_profile.Profile(
                new_bag.info.get("BagIt-Profile-Identifier"))
            # TO DO: exception if cannot retrieve profile
            return profile.validate_bag_info(new_bag)
            # TO DO: exception if validation does not work

    def get_data(self, bag):
        """Saves bag data from the bag-info.txt file"""
        new_bag = bagit.Bag(bag.bag_path)
        bag.origin = new_bag.info.get('Origin')
        bag.rights_id = new_bag.info.get('Rights-ID')
        bag.end_date = new_bag.info.get('End-Date')
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
                self.save_rights(bag, rights_json)
                bags_with_rights.append(bag.bag_identifier)
            except Exception as e:
                print(e)
        # get rights ids from database
        # loop through rights ids
        # retrieve rights
        # save rights
        return bags_with_rights

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
        return rights_json

    def save_rights(self, bag, rights_json):
        """Save JSON from rights statement service to database"""
        bag.rights_data = rights_json
        bag.save()
        # save json...to file? rights.json?
        pass


class CreatePackage(object):
    """Create JSON according to Ursa Major schema and package with bag"""

    def run(self):
        temp_dir = settings.TMP_DIR
        dest_dir = settings.DEST_DIR
        packaged = []
        unpackaged = Bag.objects.filter(rights_data__isnull=False)
        for u in unpackaged:
            try:
                self.create_json(u, temp_dir)
                self.package_bag(temp_dir, dest_dir, u)
                packaged.append(u.bag_identifier)
            except Exception as e:
                print(e)
        return packaged

    def create_json(self, bag, temp_dir):
        """Create JSON file to send to Ursa Major"""
        bag_json = BagSerializer(bag).data
        # print(bag_json)
        with open(join(temp_dir, bag.bag_identifier, "{}.json".format(bag.bag_identifier),), "w",) as f:
            json.dump(bag_json, f, indent=4, sort_keys=True, default=str)
        return join(temp_dir, bag.bag_identifier,
                    "{}.json".format(bag.bag_identifier))

    def package_bag(self, temp_dir, dest_dir, bag):
        """Create package to send to Ursa Major"""
        tar_filename = "{}.tar.gz".format(bag.bag_identifier)
        with tarfile.open(join(temp_dir, tar_filename), "w:gz") as tar:
            tar.add(join(temp_dir, bag.bag_identifier),
                    arcname=basename(join(temp_dir, bag.bag_identifier)))
        mkdir(
            join(dest_dir, bag.bag_identifier)
        )
        move(
            join(temp_dir, tar_filename),
            join(dest_dir, bag.bag_identifier, tar_filename,),
        )


class DeliverPackage(object):
    """Deliver package to Ursa Major"""

    def run(self):
        dest_dir = settings.DEST_DIR
        delivered = []
        not_delivered = Bag.objects.filter(rights_data__isnull=False)
        for d in not_delivered:
            try:
                self.deliver_data(d, dest_dir, settings.DELIVERY_URL)
                delivered.append(d.bag_identifier)
            except Exception as e:
                print(e)
        return delivered

    def deliver_data(self, bag, dest_dir, url):
        """Send data to Ursa Major"""
        bag_data = join(dest_dir, bag.bag_identifier,
                    "{}.json".format(bag.bag_identifier))
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
