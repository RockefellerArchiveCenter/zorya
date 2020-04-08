from rest_framework import serializers

from .models import Bag


class BagSerializer(serializers.ModelSerializer):
    """docstring for BagSerializer"""
    # to send to ursa major
    class Meta:
        model = Bag
        fields = ("bag_identifier", "bag_path", "origin")
