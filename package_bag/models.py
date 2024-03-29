from asterism.models import BasePackage
from django.contrib.auth.models import AbstractUser
from django.db import models


class Bag(BasePackage):
    DISCOVERED = 1
    ASSIGNED_RIGHTS = 2
    PACKAGED = 3
    DELIVERED = 4
    TAR = 5
    ASSIGNING_RIGHTS = 11
    PACKAGING = 12
    DELIVERING = 13
    ARCHIVING = 14
    DOWNLOADED = 15
    DISCOVERING = 16
    SAVED = 17
    DOWNLOADING = 18
    PROCESS_STATUS_CHOICES = (
        (DISCOVERED, "Discovered"),
        (ASSIGNED_RIGHTS, "Assigned rights"),
        (PACKAGED, "Packaged"),
        (DELIVERED, "Delivered"),
        (TAR, "Archived"),
        (ASSIGNING_RIGHTS, "Assigning rights"),
        (PACKAGING, "Creating package"),
        (DELIVERING, "Delivering"),
        (ARCHIVING, "Creating archive"),
        (DOWNLOADED, "Downloaded object from S3"),
        (DISCOVERING, "Discovering"),
        (SAVED, "Saved to database"),
        (DOWNLOADING, "Downloaded object from S3")
    )
    process_status = models.IntegerField(choices=PROCESS_STATUS_CHOICES, default=DISCOVERED)
    original_bag_name = models.CharField(max_length=255)
    ORIGIN_CHOICES = (
        ('legacy_digital', 'Legacy Digital Processing'),
        ('digitization', 'Digitization')
    )
    origin = models.CharField(
        max_length=20,
        choices=ORIGIN_CHOICES,
        null=True,
        blank=True)
    rights_id = models.JSONField(null=True, blank=True)
    start_date = models.CharField(
        max_length=255,
        null=True,
        blank=True)
    end_date = models.CharField(
        max_length=255,
        null=True,
        blank=True)
    rights_data = models.JSONField(null=True, blank=True)
    created = models.DateTimeField(auto_now=True)
    last_modified = models.DateTimeField(auto_now_add=True)


class User(AbstractUser):
    pass
