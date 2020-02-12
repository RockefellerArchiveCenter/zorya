from .models import Bag
import bagit
import os
import tarfile

class DiscoverBags(object):
    #Look into what's going on in Fornax and Aurora for bag validation - will need import bagit library
    """
    Validates bag structure and bag info file, renames bag with unique ID
    """

    def discover_bags(self, arg):
        pass

    def unpack_rename(self, sip, extract_dir):
        ext = os.path.splitext(sip.bag_path)[-1]
        if ext in ['.tgz', '.tar.gz', '.gz']:
            tf = tarfile.open(sip.bag_path, 'r')
            tf.extractall(extract_dir)
            tf.close()
            os.remove(sip.bag_path)
            # TODO: generate unique ID to rename
            sip.bag_path = os.path.join(extract_dir, sip.bag_identifier)
            sip.save()
            # TODO: what is this returning?
        else:
            raise Exception("Unrecognized archive format")
        pass

    def validate_structure(self, bag_path):
        """Validates a bag against the BagIt specification"""
        bag = bagit.Bag(bag_path)
        return bag.validate()

    def validate_metadata(self, arg):
        pass

    def process_bags(self):
        processed = []
        new_bags = self.discover(bags)
        for bag in new_bags:
            try:
                unpacked = self.unpack_rename(bag)
                validated = self.validate
                # create bag object
                process.append(validated)
            except Exception:
                # do something with error
        # return processed
    # since nothing's been saved in the database yet, where do logs go? - there are lots of different ways to do logging in django
    # what does this process bags function return? - you want to return something out of the view that indicates which objects were processed
    def parse_data(self, arg):
        # open bag-info.txt
        # get origin
        # get rights id
        pass
    def save_data(self, arg):
        pass

      
class GetRights(object):
    """Send rights ID to external service and receive JSON in return"""
    def get_rights(self, arg):
        pass
        
class CreatePackage(object):
    """Create JSON according to Ursa Major schema and package with bag"""
    def create_json(self, arg):
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