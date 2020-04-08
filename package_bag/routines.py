from .models import Bag
from package_bag.serializers import RightsInfoSerializer, BagSerializer

from uuid import uuid4
from shutil import move
import bagit
import os
import tarfile
import json

# TO DO: import settings file (directories)
from zorya import settings

# original_bag_name = models.CharField(max_length=255)
# bag_identifier = models.CharField(max_length=255, unique=True)
# bag_path = models.CharField(max_length=255, null=True, blank=True)
# origin = models.CharField(max_length=20, choices=ORIGIN_CHOICES)
# rights_id = models.CharField(max_length=255)
# created = models.DateTimeField(auto_now=True)
# last_modified = models.DateTimeField(auto_now_add=True)


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
        tf = tarfile.open(bag_path, 'r')
        tf.extractall(tmp)
        tf.close()
        os.remove(bag_path)
        bag_identifier = str(uuid4())
        return bag_identifier

    def validate_structure(self, bag_path):
        """Validates a bag against the BagIt specification"""
        new_bag = bagit.Bag(bag_path)
        return new_bag.validate()

    def validate_metadata(self, bag_path):
        new_bag = bagit.Bag(bag_path)
        bag_info = new_bag.info
        # TO DO: bag schema to validate against???
        # if validation fails, bag should fail
        pass

    def get_data(self, bag):
        new_bag = bagit.Bag(bag.bag_path)
        bag.save(
            origin=new_bag.info.get('origin'),
            rights_id=new_bag.info.get('rights_id'),
            end_date=new_bag.info.get('end_date'))  # TO DO: does field need to be renamed?
        # TO DO: what is this returning?


# how does something get sent from one bag to another? how does batching work?
class GetRights(object):
    """Send rights IDs to external service and receive JSON in return"""

    def run(self):
        url = "rights service url"
        has_rights = []
        no_rights = Bag.objects.filter(something)
        for r in no_rights:
            try:
                retrieve_rights(r, url)
                # save_rights(r)
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

    # def save_rights(self, bag):
    #     # do we want to validate rights schema here?
    #     # save json...to file? rights.json?
    #     # return saved file?
    #     pass


class CreatePackage(object):
    """Create JSON according to Ursa Major schema and package with bag"""

    def run(self):
        packaged = []
        unpackaged = Bag.objects.filter(something)
        for u in unpackaged:
            try:
                create_json(u)
            except Exception as e:
                print(e)
        return packaged

    def create_json(self, bag):
        bag_json = BagSerializer(
            bag
        ).data
        with open(
            join(
                delivery_queue_dir,
                bag.bag_identifier,
                "{}.json".format(bag.bag_identifier),
            ),
            "wb",
        ) as f:
            json.dump(bag_json, f, indent=4, sort_keys=True, default=str)
        # create json that conforms to digitization_bag or legacy_digital_bag in ursa major schema
        # check if there is json for rights file - for now assume it's rights.json
        # create json (makes extensible)
        # from database, add origin to json
        # from database, add bag uuid to json
        # combine everything as one json, save somewhere
        # return json file
        pass

    def add_rights(self, arg):
        # add rights from rights.json
        # delete rights.json
        # return json file
        pass


    def package_bag(self, storage_root_dir, delivery_queue_dir, bag):
        tar_filename = "{}.tar.gz".format(bag.bag_identifier)
        with tarfile.open(join(storage_root_dir, tar_filename), "w:gz") as tar:
            tar.add(
                join(
                    storage_root_dir,
                    bag.bag_identifier),
                arcname=os.path.basename(
                    join(
                        storage_root_dir,
                        bag.bag_identifier)))
        mkdir(
            join(delivery_queue_dir, bag.bag_identifier)
        )

        move(
            join(storage_root_dir, tar_filename),
            join(
                delivery_queue_dir,
                bag.bag_identifier,
                tar_filename,
            ),
        )

        
        
        with tarfile.open(join(
                delivery_queue_dir,
                "{}.tar.gz".format(bag.bag_identifier),
            ), "w:gz") as tar:
            tar.add(join(delivery_queue_dir, bag.bag_identifier), arcname=os.path.basename(join(delivery_queue_dir, bag.bag_identifier)))



class DeliverPackage(object):
    """Deliver package to Ursa Major"""

    # use package serializer here

    def run(self, arg):
        pass

    def send_data(self, arg):
        pass

    def send_package(self, arg):
        pass
