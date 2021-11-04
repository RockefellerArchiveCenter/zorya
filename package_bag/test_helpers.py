import shutil
from datetime import datetime
from os import listdir, makedirs
from os.path import isdir, isfile, join
from random import choice

from .models import Bag
from .routines import BagDiscoverer

RIGHTS_ID = "1 2 3"
END_DATE = datetime.now().strftime("%Y-%m-%d")


def copy_binaries(bag_fixture_dir, dest_dir):
    '''Copies files from a directory of compressed bags to a destination'''
    shutil.rmtree(dest_dir)
    shutil.copytree(bag_fixture_dir, dest_dir)
    binary = choice([i for i in listdir(dest_dir) if isfile(join(dest_dir, i))])
    for obj in Bag.objects.all():
        current_path = join(dest_dir, "{}.tar.gz".format(obj.bag_identifier))
        shutil.copy(join(dest_dir, binary), current_path)
        bag_id = BagDiscoverer().unpack_rename(current_path, dest_dir)
        obj.bag_identifier = bag_id
        obj.bag_path = join(dest_dir, bag_id)
        obj.save()


def set_up_directories(directories):
    '''For a list of directories, deletes directory if it exists and creates a directory'''
    for d in directories:
        if isdir(d):
            shutil.rmtree(d)
            makedirs(d)
        else:
            makedirs(d)
