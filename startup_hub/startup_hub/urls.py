# In startup_hub/urls.py - Updated with media files support
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static

def api_stats(request):
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

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
