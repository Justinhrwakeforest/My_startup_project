# startup_hub/apps/startups/models.py - Complete file with edit request functionality

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import json

User = get_user_model()

class Industry(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=10, blank=True)  # Emoji or icon class
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Industries"

class UserProfile(models.Model):
    """User profile to track premium membership status"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_premium = models.BooleanField(default=False)
    premium_expires_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {'Premium' if self.is_premium else 'Free'}"
    
    @property
    def is_premium_active(self):
        """Check if premium membership is currently active"""
        if not self.is_premium:
            return False
        if self.premium_expires_at and self.premium_expires_at < timezone.now():
            return False
        return True
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

class Startup(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    industry = models.ForeignKey(Industry, on_delete=models.CASCADE, related_name='startups')
    location = models.CharField(max_length=100)
    website = models.URLField(blank=True)
    logo = models.CharField(max_length=10, default='🚀')  # Emoji logo
    cover_image_url = models.URLField(blank=True, null=True, help_text='URL to cover image')
    
    # Financial info
    funding_amount = models.CharField(max_length=20, blank=True)
    valuation = models.CharField(max_length=20, blank=True)
    
    # Company details
    employee_count = models.PositiveIntegerField(default=0)
    founded_year = models.PositiveIntegerField()
    is_featured = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False, help_text='Whether startup is approved for public listing')
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_startups')
    
    # Metrics
    revenue = models.CharField(max_length=20, blank=True)
    user_count = models.CharField(max_length=20, blank=True)
    growth_rate = models.CharField(max_length=10, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views = models.PositiveIntegerField(default=0)
    
    # Contact information
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    business_model = models.CharField(max_length=50, blank=True)
    target_market = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return self.name
    
    @property
    def average_rating(self):
        ratings = self.ratings.all()
        if ratings:
            return sum(r.rating for r in ratings) / len(ratings)
        return 0
    
    @property
    def total_ratings(self):
        return self.ratings.count()
    
    def can_edit(self, user):
        """Check if user can edit this startup"""
        if not user.is_authenticated:
            return False
        
        # Admins can always edit
        if user.is_staff or user.is_superuser:
            return True
        
        # Original submitter can edit if they're premium
        if self.submitted_by == user:
            try:
                profile = user.profile
                return profile.is_premium_active
            except UserProfile.DoesNotExist:
                return False
        
        return False
    
    def has_pending_edits(self):
        """Check if there are pending edit requests"""
        return self.edit_requests.filter(status='pending').exists()
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_approved', 'is_featured'], name='startups_st_is_appr_80fd95_idx'),
            models.Index(fields=['industry', 'is_approved'], name='startups_st_industr_7f011e_idx'),
            models.Index(fields=['location', 'is_approved'], name='startups_st_locatio_5f06e2_idx'),
            models.Index(fields=['created_at'], name='startups_st_created_93e688_idx'),
        ]

class StartupEditRequest(models.Model):
    """Track edit requests from premium members that need admin approval"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE, related_name='edit_requests')
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='startup_edit_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Store the proposed changes as JSON
    proposed_changes = models.JSONField(help_text='JSON object of field names and new values')
    
    # Original values for comparison (stored when request is created)
    original_values = models.JSONField(help_text='JSON object of field names and original values')
    
    # Review information
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_edit_requests')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['startup', 'status']),
            models.Index(fields=['requested_by', 'created_at']),
        ]
    
    def __str__(self):
        return f"Edit request for {self.startup.name} by {self.requested_by.username}"
    
    def get_changes_display(self):
        """Get a human-readable display of the changes"""
        changes = []
        for field, new_value in self.proposed_changes.items():
            old_value = self.original_values.get(field, '')
            if old_value != new_value:
                changes.append(f"{field}: '{old_value}' → '{new_value}'")
        return changes
    
    def apply_changes(self):
        """Apply the proposed changes to the startup"""
        if self.status != 'approved':
            raise ValueError("Can only apply approved changes")
        
        # Apply each field change
        for field, new_value in self.proposed_changes.items():
            if hasattr(self.startup, field) and field not in ['id', 'created_at', 'updated_at', 'views']:
                setattr(self.startup, field, new_value)
        
        self.startup.save()
        return self.startup
    
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

class StartupSubmission(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('revision_requested', 'Revision Requested'),
    ]
    
    startup = models.OneToOneField(Startup, on_delete=models.CASCADE, related_name='submission')
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='startup_submissions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_submissions')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', 'submitted_at'], name='startups_st_status_594e10_idx'),
            models.Index(fields=['submitted_by', 'submitted_at'], name='startups_st_submitt_ce1579_idx'),
        ]

class StartupFounder(models.Model):
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE, related_name='founders')
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=100, default='Co-Founder')
    bio = models.TextField(blank=True, max_length=500)
    linkedin_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    
    def __str__(self):
        return f"{self.name} - {self.startup.name}"
    
    class Meta:
        ordering = ['id']

class StartupTag(models.Model):
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE, related_name='tags')
    tag = models.CharField(max_length=30)
    
    class Meta:
        unique_together = ['startup', 'tag']
        ordering = ['tag']
        
    def __str__(self):
        return self.tag

class StartupRating(models.Model):
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['startup', 'user']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['startup', 'created_at'], name='startups_st_startup_4e8f79_idx'),
        ]

class StartupComment(models.Model):
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(max_length=1000)
    likes = models.PositiveIntegerField(default=0)
    is_approved = models.BooleanField(default=True)
    is_flagged = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['startup', 'created_at'], name='startups_st_startup_6fb60b_idx'),
            models.Index(fields=['user', 'created_at'], name='startups_st_user_id_00fb2a_idx'),
        ]

class StartupBookmark(models.Model):
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE, related_name='bookmarks')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notes = models.TextField(blank=True, max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['startup', 'user']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at'], name='startups_st_user_id_92c6b9_idx'),
        ]

class StartupLike(models.Model):
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['startup', 'user']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['startup', 'created_at'], name='startups_st_startup_618547_idx'),
        ]
