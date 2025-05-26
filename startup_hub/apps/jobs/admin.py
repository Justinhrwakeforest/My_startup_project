from django.contrib import admin
from .models import JobType, Job, JobSkill, JobApplication

@admin.register(JobType)
class JobTypeAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'startup', 'location', 'job_type', 'is_remote', 'is_urgent', 'posted_at']
    list_filter = ['job_type', 'is_remote', 'is_urgent', 'experience_level', 'posted_at']
    search_fields = ['title', 'description']

@admin.register(JobSkill)
class JobSkillAdmin(admin.ModelAdmin):
    list_display = ['skill', 'job']
    list_filter = ['skill']

@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ['job', 'user', 'status', 'applied_at']
    list_filter = ['status', 'applied_at']
