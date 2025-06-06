# startup_hub/urls.py - Updated main URL configuration
from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.users.urls')),
    path('api/startups/', include('apps.startups.urls')),
    path('api/jobs/', include('apps.jobs.urls')),
    path('api/stats/', views.api_stats, name='api_stats'),
    path('', views.home, name='home'),
]

# apps/startups/urls.py - Updated startups URL configuration with detail routes
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import IndustryViewSet, StartupViewSet

router = DefaultRouter()
router.register(r'industries', IndustryViewSet)
router.register(r'', StartupViewSet, basename='startup')

urlpatterns = [
    path('', include(router.urls)),
]

# The router automatically creates these endpoints:
# GET /api/startups/ - List startups
# POST /api/startups/ - Create startup (if permitted)
# GET /api/startups/{id}/ - Retrieve startup detail
# PUT /api/startups/{id}/ - Update startup (if permitted)
# PATCH /api/startups/{id}/ - Partial update startup (if permitted)
# DELETE /api/startups/{id}/ - Delete startup (if permitted)

# Custom action endpoints:
# GET /api/startups/featured/ - Get featured startups
# GET /api/startups/trending/ - Get trending startups
# GET /api/startups/recommendations/ - Get personalized recommendations
# GET /api/startups/filters/ - Get filter options
# GET /api/startups/{id}/metrics/ - Get startup metrics
# GET /api/startups/{id}/ratings/ - Get startup ratings (paginated)
# GET /api/startups/{id}/comments/ - Get startup comments (paginated)
# GET /api/startups/{id}/jobs/ - Get startup jobs
# POST /api/startups/{id}/rate/ - Rate a startup
# POST /api/startups/{id}/comment/ - Comment on a startup
# POST /api/startups/{id}/bookmark/ - Bookmark/unbookmark startup
# POST /api/startups/{id}/like/ - Like/unlike startup
# DELETE /api/startups/{id}/delete_comment/ - Delete user's comment
