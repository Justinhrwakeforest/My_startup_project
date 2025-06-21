# apps/startups/urls.py - Complete URL configuration with all missing endpoints
from django.urls import path
from .views import StartupViewSet, IndustryViewSet

# Define URL patterns manually
urlpatterns = [
    # Industries
    path('industries/', IndustryViewSet.as_view({'get': 'list'}), name='industry-list'),
    
    # Startups basic CRUD
    path('', StartupViewSet.as_view({'get': 'list', 'post': 'create'}), name='startup-list'),
    path('<int:pk>/', StartupViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='startup-detail'),
    
    # CRITICAL: Edit functionality endpoints (THESE WERE MISSING!)
    path('<int:pk>/submit_edit/', StartupViewSet.as_view({'post': 'submit_edit'}), name='startup-submit-edit'),
    path('<int:pk>/edit_requests/', StartupViewSet.as_view({'get': 'edit_requests'}), name='startup-edit-requests'),
    path('<int:pk>/upload_cover_image/', StartupViewSet.as_view({'post': 'upload_cover_image'}), name='startup-upload-cover'),
    
    # User-specific endpoints
    path('my-startups/', StartupViewSet.as_view({'get': 'my_startups'}), name='startup-my-startups'),
    
    # Admin endpoints
    path('admin/', StartupViewSet.as_view({'get': 'admin_list'}), name='startup-admin-list'),
    path('<int:pk>/admin/', StartupViewSet.as_view({'patch': 'admin_action'}), name='startup-admin-action'),
    path('bulk-admin/', StartupViewSet.as_view({'post': 'bulk_admin'}), name='startup-bulk-admin'),
    
    # Admin edit request management
    path('edit-requests/', StartupViewSet.as_view({'get': 'admin_edit_requests'}), name='startup-admin-edit-requests'),
    path('edit-requests/<int:request_id>/approve/', StartupViewSet.as_view({'post': 'approve_edit_request'}), name='startup-approve-edit'),
    path('edit-requests/<int:request_id>/reject/', StartupViewSet.as_view({'post': 'reject_edit_request'}), name='startup-reject-edit'),
    
    # Interaction endpoints
    path('<int:pk>/rate/', StartupViewSet.as_view({'post': 'rate'}), name='startup-rate'),
    path('<int:pk>/like/', StartupViewSet.as_view({'post': 'like'}), name='startup-like'),
    path('<int:pk>/bookmark/', StartupViewSet.as_view({'post': 'bookmark'}), name='startup-bookmark'),
    path('<int:pk>/comment/', StartupViewSet.as_view({'post': 'comment'}), name='startup-comment'),
    
    # List endpoints
    path('featured/', StartupViewSet.as_view({'get': 'featured'}), name='startup-featured'),
    path('trending/', StartupViewSet.as_view({'get': 'trending'}), name='startup-trending'),
    path('bookmarked/', StartupViewSet.as_view({'get': 'bookmarked'}), name='startup-bookmarked'),
    path('filters/', StartupViewSet.as_view({'get': 'filters'}), name='startup-filters'),
    
    # Test endpoint (optional - for debugging)
    path('<int:pk>/test_edit/', StartupViewSet.as_view({'post': 'test_edit'}), name='startup-test-edit'),
]
