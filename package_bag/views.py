from asterism.views import RoutineView
from rest_framework.viewsets import ModelViewSet

from .models import Bag
from .routines import (BagDiscoverer, PackageDeliverer, PackageMaker,
                       RightsAssigner)
from .serializers import BagSerializer


class BagViewSet(ModelViewSet):
    """Viewset for Bag objects."""
    model = Bag
    queryset = Bag.objects.all()
    serializer_class = BagSerializer


class BagDiscovererView(RoutineView):
    """Triggers the BagDiscoverer routine."""
    routine = BagDiscoverer


class RightsAssignerView(RoutineView):
    """Triggers the RightsAssigner routine."""
    routine = RightsAssigner


class PackageMakerView(RoutineView):
    """Triggers the PackageMaker routine."""
    routine = PackageMaker


class PackageDelivererView(RoutineView):
    """Triggers the PackageDeliverer routine."""
    routine = PackageDeliverer
