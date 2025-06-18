from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import IndustryViewSet, StartupViewSet

router = DefaultRouter()
router.register(r'industries', IndustryViewSet)
router.register(r'', StartupViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
