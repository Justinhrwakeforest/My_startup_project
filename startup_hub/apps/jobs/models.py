# startup_hub/apps/jobs/models.py - Updated without email verification requirement

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta
import re

User = get_user_model()

class JobType(models.Model):
    name = models.CharField(max_length=20, unique=True)
    
    def __str__(self):
        return self.name

class Job(models.Model):
    EXPERIENCE_CHOICES = [
        ('entry', 'Entry Level'),
        ('mid', 'Mid Level'),
        ('senior', 'Senior Level'),
        ('lead', 'Lead/Principal'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('closed', 'Closed'),
        ('rejected', 'Rejected'),
    ]
    
    # Basic job information
    startup = models.ForeignKey('startups.Startup', on_delete=models.CASCADE, related_name='jobs', null=True, blank=True)
    title = models.CharField(max_length=100)
    description = models.TextField()
    location = models.CharField(max_length=100)
    job_type = models.ForeignKey(JobType, on_delete=models.CASCADE)
    salary_range = models.CharField(max_length=50, blank=True)
    
    # Work options
    is_remote = models.BooleanField(default=False)
    is_urgent = models.BooleanField(default=False)
    
    # Requirements
    experience_level = models.CharField(
        max_length=20, 
        choices=EXPERIENCE_CHOICES, 
        default='mid'
    )
    
    # Status and dates
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    posted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    
    # Approval and posting tracking
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posted_jobs')
    company_email = models.EmailField(help_text="Company contact email")
    # Removed is_verified field - no longer needed
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_jobs')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Tracking
    view_count = models.PositiveIntegerField(default=0)
    application_deadline = models.DateTimeField(null=True, blank=True)
    
    # Additional fields
    requirements = models.TextField(blank=True, help_text="Job requirements in detail")
    benefits = models.TextField(blank=True, help_text="Benefits and perks")
    
    class Meta:
        ordering = ['-posted_at']
        indexes = [
            models.Index(fields=['posted_at']),
            models.Index(fields=['is_active', 'status']),
            models.Index(fields=['startup', 'is_active']),
            models.Index(fields=['status', 'posted_at']),
            models.Index(fields=['posted_by', 'status']),
        ]
    
    def __str__(self):
        startup_name = self.startup.name if self.startup else "Independent"
        return f"{self.title} at {startup_name}"
    
    @property
    def posted_ago(self):
        """Human readable time since posting"""
        now = timezone.now()
        diff = now - self.posted_at
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"
    
    @property
    def days_since_posted(self):
        """Number of days since posting"""
        return (timezone.now() - self.posted_at).days
    
    @property
    def is_expired(self):
        """Check if job posting has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @property
    def days_until_expiry(self):
        """Days until job expires"""
        if self.expires_at:
            diff = self.expires_at - timezone.now()
            return max(0, diff.days)
        return None
    
    @property
    def can_edit(self):
        """Check if job can be edited by the original poster"""
        # Original poster can edit draft, pending, rejected jobs
        return self.status in ['draft', 'pending', 'rejected']
    
    def increment_view_count(self):
        """Increment view count"""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def approve(self, approved_by_user):
        """Approve the job posting"""
        self.status = 'active'
        self.is_active = True
        self.approved_by = approved_by_user
        self.approved_at = timezone.now()
        self.save(update_fields=['status', 'is_active', 'approved_by', 'approved_at'])
    
    def reject(self, rejected_by_user, reason=''):
        """Reject the job posting"""
        self.status = 'rejected'
        self.is_active = False
        self.approved_by = rejected_by_user
        self.approved_at = timezone.now()
        self.rejection_reason = reason
        self.save(update_fields=['status', 'is_active', 'approved_by', 'approved_at', 'rejection_reason'])
    
    def can_user_edit(self, user):
        """Check if a specific user can edit this job"""
        if not user or not user.is_authenticated:
            return False
        
        # Admins can edit any job without approval workflow
        if user.is_staff or user.is_superuser:
            return True
        
        # Original poster can edit draft, pending, or rejected jobs
        # When they edit, the job will be reset to pending for re-approval
        if user == self.posted_by:
            return self.status in ['draft', 'pending', 'rejected']
        
        return False
    
    def reset_for_reapproval(self, edited_by):
        """Reset job to pending status when edited by non-admin poster"""
        if not (edited_by.is_staff or edited_by.is_superuser):
            # Only reset if edited by non-admin (the original poster)
            self.status = 'pending'
            self.is_active = False
            self.approved_by = None
            self.approved_at = None
            self.rejection_reason = ''
            self.save(update_fields=[
                'status', 'is_active', 'approved_by', 
                'approved_at', 'rejection_reason'
            ])
    
    def can_user_delete(self, user):
        """Check if a specific user can delete this job"""
        if not user or not user.is_authenticated:
            return False
        
        # Admins can delete any job
        if user.is_staff or user.is_superuser:
            return True
        
        # Original poster can delete their own jobs
        if user == self.posted_by:
            return True
        
        return False

class JobEditRequest(models.Model):
    """Track edit requests for approved jobs"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='edit_requests')
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_edit_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Store the proposed changes as JSON
    proposed_changes = models.JSONField(help_text='JSON object of field names and new values')
    original_values = models.JSONField(help_text='JSON object of field names and original values')
    
    # Review information
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_job_edits')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['job', 'status']),
        ]
    
    def __str__(self):
        return f"Edit request for {self.job.title} by {self.requested_by.username}"
    
    def get_changes_display(self):
        """Get a human-readable display of the changes"""
        changes = []
        for field, new_value in self.proposed_changes.items():
            old_value = self.original_values.get(field, '')
            if old_value != new_value:
                changes.append(f"{field}: '{old_value}' → '{new_value}'")
        return changes
    
    def apply_changes(self):
        """Apply the proposed changes to the job"""
        if self.status != 'approved':
            raise ValueError("Can only apply approved changes")
        
        # Apply each field change
        for field, new_value in self.proposed_changes.items():
            if hasattr(self.job, field) and field not in ['id', 'created_at', 'updated_at', 'views']:
                setattr(self.job, field, new_value)
        
        self.job.save()
        return self.job
    
    def approve(self, user):
        """Approve the edit request and apply changes"""
        self.status = 'approved'
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.save()
        
        # Apply the changes
        self.apply_changes()
        
        return self
    
    def reject(self, user, notes=''):
        """Reject the edit request"""
        self.status = 'rejected'
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()
        return self

class JobSkill(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='skills')
    skill = models.CharField(max_length=30)
    is_required = models.BooleanField(default=True)
    proficiency_level = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
            ('expert', 'Expert'),
        ],
        default='intermediate'
    )
    
    class Meta:
        unique_together = ['job', 'skill']
        indexes = [
            models.Index(fields=['skill']),
        ]
    
    def __str__(self):
        return f"{self.skill} ({self.job.title})"

class JobApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewing', 'Under Review'),
        ('interview', 'Interview Scheduled'),
        ('offer', 'Offer Extended'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ]
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_applications')
    
    # Application content
    cover_letter = models.TextField(blank=True)
    resume = models.FileField(upload_to='resumes/', blank=True)
    
    # Additional application data
    additional_info = models.JSONField(default=dict, blank=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Review tracking
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reviewed_applications'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    # Interview details
    interview_scheduled_at = models.DateTimeField(null=True, blank=True)
    interview_notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['job', 'user']
        ordering = ['-applied_at']
        indexes = [
            models.Index(fields=['status', 'applied_at']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['job', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.job.title}"
    
    @property
    def days_since_applied(self):
        """Days since application was submitted"""
        return (timezone.now() - self.applied_at).days

class JobAlert(models.Model):
    ALERT_FREQUENCY_CHOICES = [
        ('immediate', 'Immediate'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_alerts')
    title = models.CharField(max_length=100)
    
    # Alert criteria
    keywords = models.TextField(blank=True, help_text="Comma-separated keywords")
    location = models.CharField(max_length=100, blank=True)
    job_type = models.ForeignKey(JobType, on_delete=models.SET_NULL, null=True, blank=True)
    experience_level = models.CharField(max_length=20, choices=Job.EXPERIENCE_CHOICES, blank=True)
    is_remote = models.BooleanField(default=False)
    industry = models.ForeignKey('startups.Industry', on_delete=models.SET_NULL, null=True, blank=True)
    min_salary = models.CharField(max_length=20, blank=True)
    max_salary = models.CharField(max_length=20, blank=True)
    
    # Alert settings
    frequency = models.CharField(max_length=20, choices=ALERT_FREQUENCY_CHOICES, default='daily')
    is_active = models.BooleanField(default=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_sent = models.DateTimeField(null=True, blank=True)
    total_sent = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['frequency', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def get_matching_jobs(self):
        """Get jobs that match this alert criteria"""
        from django.db.models import Q
        
        queryset = Job.objects.filter(is_active=True, status='active')
        
        # Filter by keywords
        if self.keywords:
            keywords = [k.strip() for k in self.keywords.split(',') if k.strip()]
            keyword_q = Q()
            for keyword in keywords:
                keyword_q |= (
                    Q(title__icontains=keyword) |
                    Q(description__icontains=keyword) |
                    Q(skills__skill__icontains=keyword) |
                    Q(startup__name__icontains=keyword)
                )
            queryset = queryset.filter(keyword_q).distinct()
        
        # Filter by location
        if self.location:
            queryset = queryset.filter(
                Q(location__icontains=self.location) | 
                Q(is_remote=True)  # Include remote jobs for any location
            )
        
        # Filter by job type
        if self.job_type:
            queryset = queryset.filter(job_type=self.job_type)
        
        # Filter by experience level
        if self.experience_level:
            queryset = queryset.filter(experience_level=self.experience_level)
        
        # Filter by remote
        if self.is_remote:
            queryset = queryset.filter(is_remote=True)
        
        # Filter by industry
        if self.industry:
            queryset = queryset.filter(startup__industry=self.industry)
        
        return queryset.order_by('-posted_at')
    
    def should_send_alert(self):
        """Check if alert should be sent based on frequency"""
        if not self.is_active:
            return False
        
        now = timezone.now()
        
        if self.frequency == 'immediate':
            # Send immediately when new jobs are posted
            return True
        elif self.frequency == 'daily':
            # Send daily if not sent today
            if not self.last_sent or self.last_sent.date() < now.date():
                return True
        elif self.frequency == 'weekly':
            # Send weekly if not sent in the last 7 days
            if not self.last_sent or self.last_sent < now - timedelta(days=7):
                return True
        
        return False
    
    def mark_as_sent(self):
        """Mark alert as sent"""
        self.last_sent = timezone.now()
        self.total_sent += 1
        self.save(update_fields=['last_sent', 'total_sent'])

class JobView(models.Model):
    """Track job views for analytics"""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='job_views')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['job', 'viewed_at']),
            models.Index(fields=['user', 'viewed_at']),
        ]

class JobBookmark(models.Model):
    """Allow users to bookmark jobs"""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='bookmarks')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['job', 'user']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} bookmarked {self.job.title}"

class JobShare(models.Model):
    """Track job shares"""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='shares')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    platform = models.CharField(
        max_length=20,
        choices=[
            ('email', 'Email'),
            ('linkedin', 'LinkedIn'),
            ('twitter', 'Twitter'),
            ('facebook', 'Facebook'),
            ('copy_link', 'Copy Link'),
            ('other', 'Other'),
        ],
        default='copy_link'
    )
    shared_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['job', 'shared_at']),
        ]

class ApplicationNote(models.Model):
    """Notes for job applications (by recruiters/hiring managers)"""
    application = models.ForeignKey(
        JobApplication, 
        on_delete=models.CASCADE, 
        related_name='notes'
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    note = models.TextField()
    is_internal = models.BooleanField(default=True)  # Internal notes vs candidate-visible
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['application', 'created_at']),
        ]
    
    def __str__(self):
        return f"Note for {self.application}"

class JobTemplate(models.Model):
    """Job posting templates for startups"""
    startup = models.ForeignKey('startups.Startup', on_delete=models.CASCADE, related_name='job_templates')
    name = models.CharField(max_length=100)
    title_template = models.CharField(max_length=100)
    description_template = models.TextField()
    requirements_template = models.TextField(blank=True)
    benefits_template = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['startup', 'name']
    
    def __str__(self):
        return f"{self.startup.name} - {self.name}"
