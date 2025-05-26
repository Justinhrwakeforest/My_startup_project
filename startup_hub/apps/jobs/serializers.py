from rest_framework import serializers
from django.db import models
from .models import JobType, Job, JobSkill, JobApplication
from apps.startups.serializers import StartupListSerializer

class JobTypeSerializer(serializers.ModelSerializer):
    job_count = serializers.SerializerMethodField()
    
    class Meta:
        model = JobType
        fields = ['id', 'name', 'job_count']
    
    def get_job_count(self, obj):
        return obj.job_set.filter(is_active=True).count()

class JobSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobSkill
        fields = ['id', 'skill']

class JobListSerializer(serializers.ModelSerializer):
    startup_name = serializers.CharField(source='startup.name', read_only=True)
    startup_logo = serializers.CharField(source='startup.logo', read_only=True)
    startup_location = serializers.CharField(source='startup.location', read_only=True)
    startup_industry = serializers.CharField(source='startup.industry.name', read_only=True)
    startup_employee_count = serializers.IntegerField(source='startup.employee_count', read_only=True)
    job_type_name = serializers.CharField(source='job_type.name', read_only=True)
    skills_list = serializers.StringRelatedField(source='skills', many=True, read_only=True)
    posted_ago = serializers.ReadOnlyField()
    has_applied = serializers.SerializerMethodField()
    experience_level_display = serializers.CharField(source='get_experience_level_display', read_only=True)
    days_since_posted = serializers.SerializerMethodField()
    application_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'description', 'location', 'salary_range', 'is_remote',
            'is_urgent', 'experience_level', 'experience_level_display', 'posted_at', 
            'startup', 'startup_name', 'startup_logo', 'startup_location', 
            'startup_industry', 'startup_employee_count', 'job_type', 'job_type_name',
            'skills_list', 'posted_ago', 'has_applied', 'days_since_posted',
            'application_count'
        ]
    
    def get_has_applied(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return JobApplication.objects.filter(job=obj, user=request.user).exists()
        return False
    
    def get_days_since_posted(self, obj):
        from django.utils import timezone
        diff = timezone.now() - obj.posted_at
        return diff.days
    
    def get_application_count(self, obj):
        return obj.applications.count()

class JobDetailSerializer(JobListSerializer):
    startup_detail = StartupListSerializer(source='startup', read_only=True)
    skills = JobSkillSerializer(many=True, read_only=True)
    similar_jobs = serializers.SerializerMethodField()
    requirements = serializers.SerializerMethodField()
    
    class Meta(JobListSerializer.Meta):
        fields = JobListSerializer.Meta.fields + [
            'startup_detail', 'skills', 'similar_jobs', 'requirements'
        ]
    
    def get_similar_jobs(self, obj):
        """Get similar jobs from the same company or with similar skills"""
        similar = Job.objects.filter(
            models.Q(startup=obj.startup) | 
            models.Q(skills__skill__in=obj.skills.values_list('skill', flat=True))
        ).exclude(id=obj.id).filter(is_active=True).distinct()[:3]
        
        # Use a simple serializer to avoid infinite recursion
        return [{
            'id': job.id,
            'title': job.title,
            'startup_name': job.startup.name,
            'location': job.location,
            'is_remote': job.is_remote
        } for job in similar]
    
    def get_requirements(self, obj):
        """Extract job requirements from description"""
        # This is a simple implementation - you could make this more sophisticated
        requirements = []
        if obj.skills.exists():
            requirements.extend([skill.skill for skill in obj.skills.all()])
        
        # Add experience level as a requirement
        requirements.append(f"{obj.get_experience_level_display()} experience")
        
        return requirements

class JobApplicationSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='job.title', read_only=True)
    startup_name = serializers.CharField(source='job.startup.name', read_only=True)
    startup_logo = serializers.CharField(source='job.startup.logo', read_only=True)
    job_location = serializers.CharField(source='job.location', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = JobApplication
        fields = [
            'id', 'job', 'job_title', 'startup_name', 'startup_logo', 
            'job_location', 'cover_letter', 'status', 'status_display', 
            'applied_at'
        ]
        read_only_fields = ['status', 'applied_at']