# startup_hub/startup_hub/urls.py
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def api_stats(request):
    """Simple stats endpoint"""
    from apps.startups.models import Startup
    from apps.jobs.models import Job
    from apps.startups.models import Industry
    
    return JsonResponse({
        'total_startups': Startup.objects.count(),
        'total_jobs': Job.objects.count(),
        'total_industries': Industry.objects.count(),
        'message': 'StartupHub API is running!'
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.users.urls')),
    path('api/startups/', include('apps.startups.urls')),
    path('api/jobs/', include('apps.jobs.urls')),
    path('api/stats/', api_stats, name='api_stats'),
]
