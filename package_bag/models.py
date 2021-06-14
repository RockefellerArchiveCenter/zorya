from django.contrib.auth.models import AbstractUser
from django.db import models

# TO DO: make fields nullable and blank


class Bag(models.Model):
    original_bag_name = models.CharField(max_length=255)
    bag_identifier = models.CharField(max_length=255, unique=True)
    bag_path = models.CharField(max_length=255)
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
