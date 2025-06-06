# startup_hub/urls.py - Corrected main URL configuration
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
