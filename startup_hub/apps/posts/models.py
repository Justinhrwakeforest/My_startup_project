# startup_hub/apps/posts/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import F, Q
import uuid
from django.core.validators import FileExtensionValidator

User = get_user_model()

class Topic(models.Model):
    """Topics/hashtags for posts"""
    name = models.CharField(max_length=50, unique=True, db_index=True)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=10, blank=True)  # Emoji icon
    created_at = models.DateTimeField(auto_now_add=True)
    post_count = models.PositiveIntegerField(default=0)
    follower_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-post_count', 'name']
        indexes = [
            models.Index(fields=['-post_count', 'name']),
        ]
    
    def __str__(self):
        return f"#{self.name}"

class Post(models.Model):
    """Main post model for discussions"""
    POST_TYPES = [
        ('discussion', 'Discussion'),
        ('question', 'Question'),
        ('announcement', 'Announcement'),
        ('resource', 'Resource'),
        ('event', 'Event'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField()  # Rich text content
    post_type = models.CharField(max_length=20, choices=POST_TYPES, default='discussion')
    
    # Topics/hashtags
    topics = models.ManyToManyField(Topic, related_name='posts', blank=True)
    
    # Privacy
    is_anonymous = models.BooleanField(default=False)
    is_draft = models.BooleanField(default=False)
    
    # Moderation
    is_approved = models.BooleanField(default=True)
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)  # No new comments allowed
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    edit_count = models.PositiveIntegerField(default=0)
    
    # Metrics
    view_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)
    share_count = models.PositiveIntegerField(default=0)
    bookmark_count = models.PositiveIntegerField(default=0)
    
    # SEO/Social
    slug = models.SlugField(max_length=250, blank=True)
    meta_description = models.TextField(blank=True, max_length=160)
    
    # Related startup/job (optional)
    related_startup = models.ForeignKey('startups.Startup', on_delete=models.SET_NULL, null=True, blank=True)
    related_job = models.ForeignKey('jobs.Job', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at', 'is_approved']),
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['-like_count', '-created_at']),
            models.Index(fields=['-comment_count', '-created_at']),
            models.Index(fields=['is_pinned', '-created_at']),
        ]
    
    def __str__(self):
        return self.title or f"Post by {self.get_author_name()}"
    
    def get_author_name(self):
        if self.is_anonymous:
            return "Anonymous"
        return self.author.get_full_name() or self.author.username
    
    def can_edit(self, user):
        if not user.is_authenticated:
            return False
        # Can edit within 30 minutes of creation
        if user == self.author:
            return (timezone.now() - self.created_at).total_seconds() < 1800
        return user.is_staff or user.is_superuser
    
    def can_delete(self, user):
        if not user.is_authenticated:
            return False
        return user == self.author or user.is_staff or user.is_superuser

class PostImage(models.Model):
    """Images attached to posts"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(
        upload_to='post_images/%Y/%m/%d/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif', 'webp'])]
    )
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'uploaded_at']

class PostLink(models.Model):
    """Links attached to posts with metadata"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='links')
    url = models.URLField()
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    domain = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']

class Comment(models.Model):
    """Comments on posts with threading support"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    content = models.TextField()
    is_anonymous = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    # Metrics
    like_count = models.PositiveIntegerField(default=0)
    reply_count = models.PositiveIntegerField(default=0)
    
    # Moderation
    is_approved = models.BooleanField(default=True)
    is_flagged = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'created_at']),
            models.Index(fields=['parent', 'created_at']),
            models.Index(fields=['author', '-created_at']),
        ]
    
    def __str__(self):
        return f"Comment by {self.get_author_name()} on {self.post}"
    
    def get_author_name(self):
        if self.is_anonymous:
            return "Anonymous"
        return self.author.get_full_name() or self.author.username
    
    def can_edit(self, user):
        if not user.is_authenticated:
            return False
        # Can edit within 15 minutes
        if user == self.author:
            return (timezone.now() - self.created_at).total_seconds() < 900
        return user.is_staff or user.is_superuser

class PostReaction(models.Model):
    """Reactions/likes on posts"""
    REACTION_TYPES = [
        ('like', '👍'),
        ('love', '❤️'),
        ('insightful', '💡'),
        ('celebrate', '🎉'),
        ('support', '🤝'),
        ('curious', '🤔'),
    ]
    
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_reactions')
    reaction_type = models.CharField(max_length=20, choices=REACTION_TYPES, default='like')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['post', 'user']
        indexes = [
            models.Index(fields=['post', 'reaction_type']),
            models.Index(fields=['user', '-created_at']),
        ]

class CommentReaction(models.Model):
    """Reactions on comments"""
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comment_reactions')
    is_like = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['comment', 'user']

class PostBookmark(models.Model):
    """Bookmarked posts"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='bookmarks')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['post', 'user']
        ordering = ['-created_at']

class PostView(models.Model):
    """Track post views"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['post', '-viewed_at']),
            models.Index(fields=['user', '-viewed_at']),
        ]

class PostShare(models.Model):
    """Track post shares"""
    PLATFORMS = [
        ('copy_link', 'Copy Link'),
        ('email', 'Email'),
        ('twitter', 'Twitter'),
        ('linkedin', 'LinkedIn'),
        ('facebook', 'Facebook'),
        ('whatsapp', 'WhatsApp'),
    ]
    
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='shares')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    platform = models.CharField(max_length=20, choices=PLATFORMS)
    shared_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['post', '-shared_at']),
        ]

class Mention(models.Model):
    """Track @mentions in posts and comments"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True, related_name='mentions')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True, related_name='mentions')
    mentioned_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mentions')
    mentioned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mentions_made')
    created_at = models.DateTimeField(auto_now_add=True)
    is_notified = models.BooleanField(default=False)
    
    class Meta:
        indexes = [
            models.Index(fields=['mentioned_user', '-created_at']),
        ]

class PostReport(models.Model):
    """Reports/flags on posts"""
    REPORT_REASONS = [
        ('spam', 'Spam or misleading'),
        ('inappropriate', 'Inappropriate content'),
        ('harassment', 'Harassment or hate speech'),
        ('misinformation', 'False information'),
        ('other', 'Other'),
    ]
    
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reports')
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_reports')
    reason = models.CharField(max_length=20, choices=REPORT_REASONS)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_reports')
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['post', 'reported_by']
