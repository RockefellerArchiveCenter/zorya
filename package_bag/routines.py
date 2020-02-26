from .models import Bag
from uuid import uuid4
import bagit
import os
import tarfile

# TO DO: import settings file (directories)

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
        unprocessed = self.discover_bags(src)
        for u in unprocessed:
            try:
                bag_id = self.unpack_rename(u, tmp)
                bag = Bag.objects.create(original_bag_name=u, bag_identifier=bag_id, bag_path=os.path.join(tmp, bag_id))
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
        bag.save(origin=new_bag.info.get('origin'), rights_id=new_bag.info.get('rights_id'))
        # save origin, rights id, new bag name (i.e., UUID)
        # what is this returning?


# how does something get sent from one bag to another? how does batching work?
class GetRights(object):
    """Send rights ID to external service and receive JSON in return"""

# QUESTION: where does rights approval happen? will things be in limbo, or
# does there need to be a way to view rights here? Do things get delivered
# elsewhere instead?
    def get_rights(self, arg):
        # url for post request
        # get id from database
        # send post request
        # get serialized rights back as json
        # save json...to file?
        pass


class CreatePackage(object):
    """Create JSON according to Ursa Major schema and package with bag"""

    def create_json(self, arg):
        # get json for rights (this is already a file?)
        # if no json exists, create json (makes extensible)
        # from database, add origin to json
        # from database, add bag uuid to json
        # combine everything as one json, save somewhere
        pass

    def package_bag(self, arg):
        pass

    def create_package(self, arg):
        pass


class DeliverPackage(object):
    """Deliver package to Ursa Major"""

    def send_data(self, arg):
        pass

    def send_package(self, arg):
        pass
