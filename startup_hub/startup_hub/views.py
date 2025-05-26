from django.http import JsonResponse
from django.shortcuts import render

def home(request):
    return render(request, 'home.html')

def api_stats(request):
    return JsonResponse({
        'total_startups': 6,
        'total_jobs': 4,
        'total_industries': 6,
        'message': 'StartupHub API is running!'
    })