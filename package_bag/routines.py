from .models import Bag
import bagit
import os
import tarfile


class DiscoverBags(object):
    # Look into what's going on in Fornax and Aurora for bag validation - will
    # need import bagit library
    """
    Validates bag structure and bag info file, renames bag with unique ID
    """

    def discover_bags(self, arg):
        # get source directory
        # get list of directories
        # check if tar.gz?
        # return list
        pass

    def unpack_rename(self, bag, extract_dir):
        ext = os.path.splitext(bag.bag_path)[-1]
        if ext in ['.tgz', '.tar.gz', '.gz']:
            tf = tarfile.open(bag.bag_path, 'r')
            tf.extractall(extract_dir)
            tf.close()
            os.remove(bag.bag_path)
            # TODO: generate unique ID to rename
            bag.bag_path = os.path.join(extract_dir, bag.bag_identifier)
            bag.save()
            # TODO: what is this returning?
        else:
            raise Exception("Unrecognized archive format")
        pass

    def validate_structure(self, bag_path):
        """Validates a bag against the BagIt specification"""
        # gets one bag
        bag = bagit.Bag(bag_path)
        return bag.validate()

    def validate_metadata(self, bag_info):
        # takes bag path of unpacked bag
        # opens bag_info.txt file
        # takes schema to validate
        # validates
        # if validation fails, bag should fail
        pass

    def process_bags(self):
        processed = []
        new_bags = self.discover_bags(bags)
        for bag in new_bags:
            try:
                unpacked = self.unpack_rename(bag)
                validated = self.validate
                # create bag object
                process.append(validated)
                # parse data
                # save to database
            except Exception:
                # do something with error
                # return processed
                # since nothing's been saved in the database yet, where do logs go? - there are lots of different ways to do logging in django
                # what does this process bags function return? - you want to
                # return something out of the view that indicates which objects
                # were processed

    def get_data(self, arg):
        # open bag-info.txt
        # get origin
        # get rights id
        # save origin, rights id, new bag name (i.e., UUID)
        pass


# how does something get sent from one bag to another? how does batching work?
class GetRights(object):
    """Send rights ID to external service and receive JSON in return"""

# QUESTION: where does rights approval happen? will things be in limbo, or does there need to be a way to view rights here? Do things get delivered elsewhere instead?
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
