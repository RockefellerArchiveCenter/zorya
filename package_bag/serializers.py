from rest_framework import serializers

from .models import Bag


class BagSerializer(serializers.ModelSerializer):
    """Serializer for Digitization Bags"""

    identifier = serializers.CharField(source="bag_identifier")
    rights_statements = serializers.SerializerMethodField(source="rights_data")

    class Meta:
        model = Bag
        fields = ("identifier", "origin", "rights_statements")

    def get_rights_statements(self, obj):
        return obj.rights_data['rights_statements']
