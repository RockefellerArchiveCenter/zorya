"""zorya URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from django.urls import include, path
from package_bag.views import (BagDiscovererView, BagViewSet,
                               PackageArchiverView, PackageDelivererView,
                               PackageMakerView, RightsAssignerView,
                               S3ObjectDownloaderView)
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'bags', BagViewSet, 'bag')

urlpatterns = [
    path('download-objects/', S3ObjectDownloaderView.as_view(), name="s3objectdownloader"),
    path('discover-bags/', BagDiscovererView.as_view(), name="bagdiscoverer"),
    path('assign-rights/', RightsAssignerView.as_view(), name="rightsassigner"),
    path('make-package/', PackageMakerView.as_view(), name="packagemaker"),
    path('archive-package/', PackageArchiverView.as_view(), name="packagearchiver"),
    path('deliver-package/', PackageDelivererView.as_view(), name="packagedeliverer"),
    path('admin/', admin.site.urls),
    path('', include(router.urls)),
    url('status/', include('health_check.api.urls')),
]
