from rest_framework import serializers

from .models import Bag


class BagSerializer(serializers.ModelSerializer):
    """Serializer for Digitization Bags"""

    identifier = serializers.CharField(source="bag_identifier")

    class Meta:
        model = Bag
        fields = ("identifier", "origin", "rights_data")
