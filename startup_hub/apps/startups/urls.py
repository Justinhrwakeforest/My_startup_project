# apps/startups/urls.py - Complete fixed configuration
from django.urls import path
from .views import StartupViewSet, IndustryViewSet

# Define URL patterns manually
urlpatterns = [
    # Industries
    path('industries/', IndustryViewSet.as_view({'get': 'list'}), name='industry-list'),
    
    # Startups
    path('', StartupViewSet.as_view({'get': 'list', 'post': 'create'}), name='startup-list'),
    path('<int:pk>/', StartupViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='startup-detail'),
    
    # Admin endpoints - FIXED
    path('admin/', StartupViewSet.as_view({'get': 'admin_list'}), name='startup-admin-list'),
    path('<int:pk>/admin/', StartupViewSet.as_view({'patch': 'admin_action'}), name='startup-admin-action'),
    path('bulk-admin/', StartupViewSet.as_view({'post': 'bulk_admin'}), name='startup-bulk-admin'),
    
    # Custom actions
    path('<int:pk>/rate/', StartupViewSet.as_view({'post': 'rate'}), name='startup-rate'),
    path('<int:pk>/like/', StartupViewSet.as_view({'post': 'like'}), name='startup-like'),
    path('<int:pk>/bookmark/', StartupViewSet.as_view({'post': 'bookmark'}), name='startup-bookmark'),
    path('<int:pk>/comment/', StartupViewSet.as_view({'post': 'comment'}), name='startup-comment'),
    
    # List actions
    path('featured/', StartupViewSet.as_view({'get': 'featured'}), name='startup-featured'),
    path('trending/', StartupViewSet.as_view({'get': 'trending'}), name='startup-trending'),
    path('bookmarked/', StartupViewSet.as_view({'get': 'bookmarked'}), name='startup-bookmarked'),
    path('filters/', StartupViewSet.as_view({'get': 'filters'}), name='startup-filters'),
]
