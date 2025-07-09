# startup_hub/apps/community/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

User = get_user_model()

class UserProfile(models.Model):
    """Extended user profile for community features"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='community_profile')
    
    # Profile info
    headline = models.CharField(max_length=200, blank=True)
    expertise = models.JSONField(default=list)  # ['Python', 'AI/ML', 'Sales', etc.]
    looking_for = models.JSONField(default=list)  # ['Co-founder', 'Investor', 'Mentor', etc.]
    
    # Social links
    linkedin_url = models.URLField(blank=True)
    twitter_handle = models.CharField(max_length=50, blank=True)
    github_username = models.CharField(max_length=50, blank=True)
    personal_website = models.URLField(blank=True)
    
    # Preferences
    is_open_to_opportunities = models.BooleanField(default=True)
    preferred_contact_method = models.CharField(
        max_length=20,
        choices=[
            ('platform', 'Platform Messages'),
            ('email', 'Email'),
            ('linkedin', 'LinkedIn'),
        ],
        default='platform'
    )
    
    # Metrics
    reputation_score = models.IntegerField(default=0)
    helpful_votes = models.IntegerField(default=0)
    
    # Badges/achievements
    badges = models.JSONField(default=list)  # ['early_adopter', 'top_contributor', etc.]
    
    # Settings
    show_online_status = models.BooleanField(default=True)
    allow_direct_messages = models.BooleanField(default=True)
    email_on_mention = models.BooleanField(default=True)
    email_on_reply = models.BooleanField(default=True)
    
    # Timestamps
    last_seen = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['-reputation_score']),
            models.Index(fields=['-last_seen']),
        ]
    
    def __str__(self):
        return f"{self.user.username}'s profile"
    
    def update_last_seen(self):
        self.last_seen = timezone.now()
        self.save(update_fields=['last_seen'])
    
    @property
    def is_online(self):
        if not self.last_seen:
            return False
        return (timezone.now() - self.last_seen).seconds < 300  # 5 minutes

class Group(models.Model):
    """Community groups/spaces"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField()
    icon = models.CharField(max_length=10, default='👥')  # Emoji icon
    cover_image_url = models.URLField(blank=True)
    
    # Group type
    GROUP_TYPES = [
        ('public', 'Public'),
        ('private', 'Private'),
        ('invite_only', 'Invite Only'),
    ]
    group_type = models.CharField(max_length=20, choices=GROUP_TYPES, default='public')
    
    # Members
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_groups')
    moderators = models.ManyToManyField(User, related_name='moderated_groups', blank=True)
    
    # Settings
    auto_approve_members = models.BooleanField(default=True)
    allow_member_posts = models.BooleanField(default=True)
    require_post_approval = models.BooleanField(default=False)
    
    # Metrics
    member_count = models.PositiveIntegerField(default=0)
    post_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-member_count', 'name']
        indexes = [
            models.Index(fields=['-member_count']),
            models.Index(fields=['slug']),
        ]
    
    def __str__(self):
        return self.name

class GroupMembership(models.Model):
    """Track group memberships"""
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_memberships')
    
    # Role
    ROLE_CHOICES = [
        ('member', 'Member'),
        ('moderator', 'Moderator'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    
    # Status
    is_approved = models.BooleanField(default=True)
    is_banned = models.BooleanField(default=False)
    
    # Timestamps
    joined_at = models.DateTimeField(auto_now_add=True)
    banned_at = models.DateTimeField(null=True, blank=True)
    banned_reason = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['group', 'user']
        indexes = [
            models.Index(fields=['user', '-joined_at']),
            models.Index(fields=['group', 'role']),
        ]

class CofounderMatch(models.Model):
    """Co-founder matching system"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cofounder_profiles')
    
    # What they bring
    skills = models.JSONField(default=list)
    experience_years = models.PositiveIntegerField(validators=[MinValueValidator(0), MaxValueValidator(50)])
    commitment_level = models.CharField(
        max_length=20,
        choices=[
            ('full_time', 'Full-time'),
            ('part_time', 'Part-time'),
            ('advisory', 'Advisory'),
        ]
    )
    equity_expectation = models.CharField(max_length=50, blank=True)  # "10-20%", "Equal split", etc.
    
    # What they're looking for
    looking_for_skills = models.JSONField(default=list)
    startup_stage_preference = models.CharField(
        max_length=20,
        choices=[
            ('idea', 'Idea Stage'),
            ('mvp', 'MVP Stage'),
            ('revenue', 'Revenue Stage'),
            ('growth', 'Growth Stage'),
        ]
    )
    industry_preferences = models.ManyToManyField('startups.Industry', blank=True)
    
    # About them
    bio = models.TextField()
    achievements = models.TextField(blank=True)
    ideal_cofounder = models.TextField(blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', '-created_at']),
        ]

class MatchScore(models.Model):
    """Compatibility scores between users"""
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='match_scores_as_user1')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='match_scores_as_user2')
    
    # Scores
    overall_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    skills_complementarity = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    interest_alignment = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    experience_balance = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # Metadata
    calculated_at = models.DateTimeField(auto_now=True)
    interaction_count = models.PositiveIntegerField(default=0)  # Messages, comments, etc.
    
    class Meta:
        unique_together = ['user1', 'user2']
        indexes = [
            models.Index(fields=['-overall_score']),
            models.Index(fields=['user1', '-overall_score']),
        ]

class Event(models.Model):
    """Community events"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Event details
    event_type = models.CharField(
        max_length=20,
        choices=[
            ('meetup', 'Meetup'),
            ('workshop', 'Workshop'),
            ('pitch', 'Pitch Event'),
            ('networking', 'Networking'),
            ('webinar', 'Webinar'),
        ]
    )
    
    # Timing
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Location
    is_online = models.BooleanField(default=True)
    location = models.CharField(max_length=200, blank=True)
    meeting_url = models.URLField(blank=True)
    
    # Organization
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hosted_events')
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    
    # Registration
    requires_registration = models.BooleanField(default=True)
    max_attendees = models.PositiveIntegerField(null=True, blank=True)
    registration_deadline = models.DateTimeField(null=True, blank=True)
    
    # Status
    is_published = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['start_datetime']
        indexes = [
            models.Index(fields=['start_datetime', 'is_published']),
            models.Index(fields=['host', '-created_at']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def is_upcoming(self):
        return self.start_datetime > timezone.now()
    
    @property
    def is_ongoing(self):
        now = timezone.now()
        return self.start_datetime <= now <= self.end_datetime

class EventRegistration(models.Model):
    """Event registrations"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_registrations')
    
    # Status
    STATUS_CHOICES = [
        ('registered', 'Registered'),
        ('waitlisted', 'Waitlisted'),
        ('attended', 'Attended'),
        ('no_show', 'No Show'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='registered')
    
    # Timestamps
    registered_at = models.DateTimeField(auto_now_add=True)
    attended_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    registration_notes = models.TextField(blank=True)  # Any special requirements
    
    class Meta:
        unique_together = ['event', 'user']
        indexes = [
            models.Index(fields=['event', 'status']),
            models.Index(fields=['user', '-registered_at']),
        ]

class ResourceTemplate(models.Model):
    """Templates and resources"""
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(
        max_length=50,
        choices=[
            ('pitch_deck', 'Pitch Deck'),
            ('business_plan', 'Business Plan'),
            ('legal', 'Legal Documents'),
            ('marketing', 'Marketing Materials'),
            ('financial', 'Financial Models'),
            ('email', 'Email Templates'),
        ]
    )
    
    # Content
    content = models.TextField(blank=True)  # For text templates
    file_url = models.URLField(blank=True)  # For downloadable files
    preview_image_url = models.URLField(blank=True)
    
    # Metadata
    tags = models.JSONField(default=list)
    is_premium = models.BooleanField(default=False)
    download_count = models.PositiveIntegerField(default=0)
    
    # Contributor
    contributed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-download_count', '-created_at']
        indexes = [
            models.Index(fields=['category', '-download_count']),
        ]
    
    def __str__(self):
        return self.title
