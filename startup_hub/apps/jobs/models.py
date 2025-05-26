from django.db import models
from django.contrib.auth import get_user_model
from apps.startups.models import Startup

User = get_user_model()

class JobType(models.Model):
    name = models.CharField(max_length=20, unique=True)  # Full-time, Part-time, Contract, etc.
    
    def __str__(self):
        return self.name

class Job(models.Model):
    EXPERIENCE_CHOICES = [
        ('entry', 'Entry Level'),
        ('mid', 'Mid Level'), 
        ('senior', 'Senior Level'),
        ('lead', 'Lead/Principal'),
    ]
    
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE, related_name='jobs')
    title = models.CharField(max_length=100)
    description = models.TextField()
    location = models.CharField(max_length=100)
    job_type = models.ForeignKey(JobType, on_delete=models.CASCADE)
    salary_range = models.CharField(max_length=50)
    is_remote = models.BooleanField(default=False)
    is_urgent = models.BooleanField(default=False)
    
    # Requirements
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_CHOICES, default='mid')
    
    # Metadata
    posted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.title} at {self.startup.name}"
    
    @property
    def posted_ago(self):
        from django.utils import timezone
        diff = timezone.now() - self.posted_at
        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} hours ago"
        else:
            return f"{diff.seconds // 60} minutes ago"

class JobSkill(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='skills')
    skill = models.CharField(max_length=30)
    
    class Meta:
        unique_together = ['job', 'skill']
        
    def __str__(self):
        return self.skill

class JobApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewing', 'Under Review'),
        ('interview', 'Interview Scheduled'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cover_letter = models.TextField(blank=True)
    resume = models.FileField(upload_to='resumes/', blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    applied_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['job', 'user']
