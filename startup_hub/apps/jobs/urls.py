# startup_hub/apps/jobs/urls.py - Updated with all endpoints

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import JobTypeViewSet, JobViewSet

router = DefaultRouter()
router.register(r'types', JobTypeViewSet)
router.register(r'', JobViewSet)

# Additional URL patterns for specific endpoints
urlpatterns = [
    # Job types
    path('types/', JobTypeViewSet.as_view({'get': 'list'}), name='jobtype-list'),
    
    # Jobs basic CRUD
    path('', JobViewSet.as_view({'get': 'list', 'post': 'create'}), name='job-list'),
    path('<int:pk>/', JobViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='job-detail'),
    
    # Job listing filters and views
    path('recent/', JobViewSet.as_view({'get': 'recent'}), name='job-recent'),
    path('urgent/', JobViewSet.as_view({'get': 'urgent'}), name='job-urgent'),
    path('remote/', JobViewSet.as_view({'get': 'remote'}), name='job-remote'),
    path('filters/', JobViewSet.as_view({'get': 'filters'}), name='job-filters'),
    path('recommendations/', JobViewSet.as_view({'get': 'recommendations'}), name='job-recommendations'),
    
    # User-specific endpoints
    path('my-jobs/', JobViewSet.as_view({'get': 'my_jobs'}), name='job-my-jobs'),
    path('my-applications/', JobViewSet.as_view({'get': 'my_applications'}), name='job-my-applications'),
    
    # Job application endpoints
    path('<int:pk>/apply/', JobViewSet.as_view({'post': 'apply'}), name='job-apply'),
    
    # Admin endpoints
    path('admin/', JobViewSet.as_view({'get': 'admin_list'}), name='job-admin-list'),
    path('<int:pk>/admin/', JobViewSet.as_view({'patch': 'admin_action'}), name='job-admin-action'),
    path('bulk-admin/', JobViewSet.as_view({'post': 'bulk_admin'}), name='job-bulk-admin'),
    path('admin_stats/', JobViewSet.as_view({'get': 'admin_stats'}), name='job-admin-stats'),
]
