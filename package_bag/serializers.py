from rest_framework import serializers

from .models import Bag

# QUESTION: should I use HyperlinkedModelSerializer instead?

class RightsInfoSerializer(serializers.ModelSerializer):
    """docstring for RightsInfoSerializer"""
    # to send to rights service
    class Meta:
        model = Bag
        fields = ("bag_identifier", "rights_id", "end_date")
        

class BagSerializer(serializers.ModelSerializer):
    """docstring for BagSerializer"""
    # to send to ursa major
    class Meta:
        model = Bag
        fields = ("bag_identifier", "bag_path", "origin")
        
        
