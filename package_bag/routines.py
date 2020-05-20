from .models import Bag
from package_bag.serializers import BagSerializer

from uuid import uuid4
from shutil import move
import bagit
import bagit_profile
import os
import tarfile
import json

# TO DO: import settings file (directories)
# api key for rights service?
from zorya import settings


class DiscoverBags(object):
    """
    Validates bag structure and bag info file, renames bag with unique ID
    """

    def run(self):
        # TO DO: assign src variable
        # TO DO: assign tmp variable
        processed = []
        unprocessed = self.discover_bags(settings.SRC_DIR)
        for u in unprocessed:
            try:
                bag_id = self.unpack_rename(u, settings.TMP_DIR)
                bag = Bag.objects.create(
                    original_bag_name=u,
                    bag_identifier=bag_id,
                    bag_path=os.path.join(
                        settings.TMP_DIR,
                        bag_id))
                self.validate_structure(bag.bag_path)
                self.validate_metadata(bag.bag_path)
                self.get_data(bag)
                processed.append(bag)
            except Exception as e:
                print(e)
                # since nothing's been saved in the database yet, where do logs go? - there are lots of different ways to do logging in django
                # what does this process bags function return? - you want to
                # return something out of the view that indicates which objects
                # were processed
        return processed

    def discover_bags(self, src):
        bags_list = []
        for d in os.listdir(src):
            ext = os.path.splitext(d)[-1]
            if ext in ['.tgz', '.tar.gz', '.gz']:
                bags_list.append(os.path.join(src, d))
        return bags_list

    def unpack_rename(self, bag_path, tmp):
        bag_identifier = str(uuid4())
        tf = tarfile.open(bag_path, 'r')
        tf.extractall(tmp)
        original_bag_name = tf.getnames()[0]
        tf.close()
        os.rename(os.path.join(tmp, original_bag_name),
                  os.path.join(tmp, bag_identifier))
        os.remove(bag_path)
        return bag_identifier

    def validate_structure(self, bag_path):
        """Validates a bag against the BagIt specification"""
        new_bag = bagit.Bag(bag_path)
        return new_bag.validate()

    def validate_metadata(self, bag_path):
        # TO DO: first vlaidation that "BagIt-Profile-Identifier" exists
        new_bag = bagit.Bag(bag_path)
        bag_info = new_bag.info
        if "BagIt-Profile-Identifier" not in bag_info:
            print("no bagit profile identifier")
            # TO DO: return exception
        else:
            profile = bagit_profile.Profile(
                new_bag.info.get("BagIt-Profile-Identifier"))
            # TO DO: exception if cannot retrieve profile
            return profile.validate_bag_info(new_bag)
            # TO DO: exception if validation does not work

    def get_data(self, bag):
        new_bag = bagit.Bag(bag.bag_path)
        bag.origin = new_bag.info.get('Origin')
        bag.rights_id = new_bag.info.get('Rights-ID')
        bag.end_date = new_bag.info.get('End-Date')
        bag.save()
        # TO DO: what is this returning?


# how does something get sent from one bag to another? how does batching work?
class GetRights(object):
    """Send rights IDs to external service and receive JSON in return"""

    def run(self):
        url = "rights service url"
        apikey = "rights service apikey"
        has_rights = []
        for bag in Bag.objects.filter(rights_data__isnull=True):
            try:
                rights_json = self.retrieve_rights(bag, url, apikey)
                self.save_rights(bag, rights_json)
            except Exception as e:
                print(e)
        # get rights ids from database
        # loop through rights ids
        # retrieve rights
        # save rights
        return has_rights

    def retrieve_rights(self, bag, url, apikey):
        # url for get request
        resp = requests.post(
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
        # do we want to validate rights schema here?
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
        unpackaged = Bag.objects.all()  # Bag.objects.filter(something)
        for u in unpackaged:
            try:
                self.create_json(u, temp_dir)
                self.package_bag(temp_dir, dest_dir, u)
            except Exception as e:
                print(e)
        return packaged

    def create_json(self, bag, temp_dir):
        bag_json = BagSerializer(bag).data
        # print(bag_json)
        with open(
            os.path.join(
                temp_dir,
                bag.bag_identifier,
                "{}.json".format(bag.bag_identifier),
            ),
            "w",
        ) as f:
            json.dump(bag_json, f, indent=4, sort_keys=True, default=str)
        return os.path.join(temp_dir, bag.bag_identifier, "{}.json".format(bag.bag_identifier))

    def package_bag(self, temp_dir, dest_dir, bag):
        tar_filename = "{}.tar.gz".format(bag.bag_identifier)
        with tarfile.open(os.path.join(temp_dir, tar_filename), "w:gz") as tar:
            tar.add(
                os.path.join(
                    temp_dir,
                    bag.bag_identifier),
                arcname=os.path.basename(
                    os.path.join(
                        temp_dir,
                        bag.bag_identifier)))
        os.mkdir(
            os.path.join(dest_dir, bag.bag_identifier)
        )
        move(
            os.path.join(temp_dir, tar_filename),
            os.path.join(
                dest_dir,
                bag.bag_identifier,
                tar_filename,
            ),
        )


class DeliverPackage(object):
    """Deliver package to Ursa Major"""

    # use package serializer here

    def run(self, arg):
        pass

    def send_data(self, arg):
        pass

    def send_package(self, arg):
        pass
