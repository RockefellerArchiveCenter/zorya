from rest_framework import serializers

from .models import Bag


class BagSerializer(serializers.ModelSerializer):
    """Serializer for Digitization Bags"""

    identifier = serializers.CharField(source="bag_identifier")
    rights_statements = serializers.JSONField(source="rights_data")

    class Meta:
        model = Bag
        fields = ("identifier", "origin", "rights_statements")
