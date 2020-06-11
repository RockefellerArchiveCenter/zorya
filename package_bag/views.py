from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet

from .models import Bag
from .serializers import BagSerializer


class BagViewSet(ModelViewSet):
    """docstring for BagViewSet"""

    model = Bag
    queryset = Bag.objects.all()
    serializer_class = BagSerializer
