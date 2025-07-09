# startup_hub/apps/messaging/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid
from django.core.validators import FileExtensionValidator

User = get_user_model()

class Conversation(models.Model):
    """Conversation between users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participants = models.ManyToManyField(User, related_name='conversations')
    is_group = models.BooleanField(default=False)
    group_name = models.CharField(max_length=100, blank=True)
    group_description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Settings
    is_archived = models.BooleanField(default=False)
    is_muted = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['-updated_at']),
        ]
    
    def __str__(self):
        if self.is_group:
            return self.group_name or f"Group ({self.participants.count()} members)"
        participants = list(self.participants.all()[:2])
        if len(participants) == 2:
            return f"{participants[0].username} & {participants[1].username}"
        return f"Conversation {self.id}"
    
    def get_other_participant(self, user):
        """Get the other participant in a 1-on-1 conversation"""
        if not self.is_group:
            return self.participants.exclude(id=user.id).first()
        return None

class Message(models.Model):
    """Individual messages in conversations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    
    # Message types
    is_system_message = models.BooleanField(default=False)
    
    # Timestamps
    sent_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # Reply to another message
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    
    class Meta:
        ordering = ['sent_at']
        indexes = [
            models.Index(fields=['conversation', 'sent_at']),
            models.Index(fields=['sender', '-sent_at']),
        ]
    
    def __str__(self):
        return f"Message from {self.sender.username} at {self.sent_at}"

class MessageAttachment(models.Model):
    """File attachments for messages"""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(
        upload_to='message_attachments/%Y/%m/%d/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'zip'])]
    )
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()  # in bytes
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['uploaded_at']

class MessageRead(models.Model):
    """Track read receipts"""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_receipts')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['message', 'user']
        indexes = [
            models.Index(fields=['user', '-read_at']),
        ]

class ConversationParticipant(models.Model):
    """Track participant-specific conversation settings"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='participant_settings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Notifications
    is_muted = models.BooleanField(default=False)
    muted_until = models.DateTimeField(null=True, blank=True)
    
    # Last read
    last_read_message = models.ForeignKey(Message, on_delete=models.SET_NULL, null=True, blank=True)
    last_read_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    is_admin = models.BooleanField(default=False)
    
    # Labels/tags (using JSONField for SQLite compatibility)
    labels = models.JSONField(default=list, blank=True)  # ['Investor Interest', 'Hiring', etc.]
    
    class Meta:
        unique_together = ['conversation', 'user']
        indexes = [
            models.Index(fields=['user', '-conversation__updated_at']),
        ]

class ChatRequest(models.Model):
    """Request to start a conversation (for investor protection)"""
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_chat_requests')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_chat_requests')
    message = models.TextField(help_text="Introduction message")
    
    # Status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Timestamps
    sent_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    
    # Created conversation (if accepted)
    conversation = models.ForeignKey(Conversation, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ['from_user', 'to_user']
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['to_user', 'status', '-sent_at']),
            models.Index(fields=['from_user', '-sent_at']),
        ]
    
    def __str__(self):
        return f"Chat request from {self.from_user.username} to {self.to_user.username}"
    
    def is_expired(self):
        return timezone.now() > self.expires_at

class UserConnection(models.Model):
    """Track connections between users"""
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='connections_from')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='connections_to')
    connected_at = models.DateTimeField(auto_now_add=True)
    
    # Connection context
    connection_type = models.CharField(max_length=50, blank=True)  # 'investor', 'founder', 'mentor', etc.
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['from_user', 'to_user']
        indexes = [
            models.Index(fields=['from_user', '-connected_at']),
            models.Index(fields=['to_user', '-connected_at']),
        ]
    
    @classmethod
    def are_connected(cls, user1, user2):
        return cls.objects.filter(
            models.Q(from_user=user1, to_user=user2) | 
            models.Q(from_user=user2, to_user=user1)
        ).exists()

class BlockedUser(models.Model):
    """Track blocked users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_users')
    blocked_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_by')
    blocked_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['user', 'blocked_user']
        indexes = [
            models.Index(fields=['user', 'blocked_user']),
        ]
