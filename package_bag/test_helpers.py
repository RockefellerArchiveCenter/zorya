import shutil
import tarfile
from os import listdir, makedirs, remove, rename
from os.path import isdir, isfile, join
from random import choice
from uuid import uuid4

from .models import Bag

RIGHTS_ID = "1 2 3"
END_DATE = "2021-11-04"


def copy_binaries(bag_fixture_dir, dest_dir):
    '''Copies files from a directory of compressed bags to a destination'''
    shutil.rmtree(dest_dir)
    shutil.copytree(bag_fixture_dir, dest_dir)
    binary = choice([i for i in listdir(dest_dir) if isfile(join(dest_dir, i))])
    for obj in Bag.objects.all():
        current_path = join(dest_dir, "{}.tar.gz".format(obj.bag_identifier))
        shutil.copy(join(dest_dir, binary), current_path)
        bag_id = unpack_rename(current_path, dest_dir)
        obj.bag_identifier = bag_id
        obj.bag_path = join(dest_dir, bag_id)
        obj.save()


def unpack_rename(bag_path, tmp):
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


def set_up_directories(directories):
    '''For a list of directories, deletes directory if it exists and creates a directory'''
    for d in directories:
        if isdir(d):
            shutil.rmtree(d)
            makedirs(d)
        else:
            makedirs(d)
