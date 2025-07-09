# startup_hub/apps/messaging/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import (
    Conversation, Message, MessageAttachment, MessageRead,
    ConversationParticipant, ChatRequest, UserConnection
)

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for messaging"""
    full_name = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'is_online']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    
    def get_is_online(self, obj):
        # Check if user has been active in last 5 minutes
        if hasattr(obj, 'community_profile') and obj.community_profile.last_seen:
            return (timezone.now() - obj.community_profile.last_seen).seconds < 300
        return False

class MessageAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageAttachment
        fields = ['id', 'file', 'file_name', 'file_size', 'uploaded_at']
        read_only_fields = ['file_name', 'file_size', 'uploaded_at']

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    is_read = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'content', 'sent_at',
            'edited_at', 'is_deleted', 'is_system_message',
            'reply_to', 'attachments', 'is_read'
        ]
        read_only_fields = ['sent_at', 'edited_at']
    
    def get_is_read(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.read_receipts.filter(user=request.user).exists()
        return False

class ConversationParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = ConversationParticipant
        fields = [
            'user', 'is_muted', 'muted_until', 'joined_at',
            'left_at', 'is_admin', 'labels'
        ]

class ConversationListSerializer(serializers.ModelSerializer):
    other_participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'is_group', 'group_name', 'created_at', 'updated_at',
            'other_participant', 'last_message', 'unread_count', 'display_name'
        ]
    
    def get_other_participant(self, obj):
        if not obj.is_group:
            request = self.context.get('request')
            if request and request.user.is_authenticated:
                other = obj.get_other_participant(request.user)
                if other:
                    return UserSerializer(other).data
        return None
    
    def get_last_message(self, obj):
        last_message = obj.messages.filter(is_deleted=False).last()
        if last_message:
            return MessageSerializer(last_message, context=self.context).data
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                participant = obj.participant_settings.get(user=request.user)
                if participant.last_read_message:
                    return obj.messages.filter(
                        sent_at__gt=participant.last_read_message.sent_at,
                        is_deleted=False
                    ).exclude(sender=request.user).count()
                else:
                    return obj.messages.filter(is_deleted=False).exclude(sender=request.user).count()
            except ConversationParticipant.DoesNotExist:
                return 0
        return 0
    
    def get_display_name(self, obj):
        if obj.is_group:
            return obj.group_name or f"Group Chat ({obj.participants.count()} members)"
        else:
            request = self.context.get('request')
            if request and request.user.is_authenticated:
                other = obj.get_other_participant(request.user)
                if other:
                    return other.get_full_name() or other.username
        return "Conversation"

class ConversationDetailSerializer(ConversationListSerializer):
    participants = UserSerializer(many=True, read_only=True)
    participant_settings = ConversationParticipantSerializer(many=True, read_only=True)
    messages = serializers.SerializerMethodField()
    
    class Meta(ConversationListSerializer.Meta):
        fields = ConversationListSerializer.Meta.fields + [
            'participants', 'participant_settings', 'messages',
            'group_description', 'is_archived', 'is_muted'
        ]
    
    def get_messages(self, obj):
        # Get last 50 messages
        messages = obj.messages.filter(is_deleted=False).order_by('-sent_at')[:50]
        return MessageSerializer(
            reversed(messages), 
            many=True, 
            context=self.context
        ).data

class ConversationCreateSerializer(serializers.ModelSerializer):
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=True
    )
    initial_message = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Conversation
        fields = ['participant_ids', 'initial_message', 'is_group', 'group_name']
    
    def validate_participant_ids(self, value):
        if len(value) < 1:
            raise serializers.ValidationError("At least one participant is required")
        
        # Check if all users exist
        users = User.objects.filter(id__in=value)
        if users.count() != len(value):
            raise serializers.ValidationError("Some participant IDs are invalid")
        
        return value
    
    def create(self, validated_data):
        participant_ids = validated_data.pop('participant_ids')
        initial_message = validated_data.pop('initial_message', None)
        request_user = self.context['request'].user
        
        # Add request user to participants
        all_participant_ids = set(participant_ids + [request_user.id])
        
        # Check if this is a group chat
        is_group = len(all_participant_ids) > 2 or validated_data.get('is_group', False)
        
        # For 1-on-1 chats, check if conversation already exists
        if not is_group and len(all_participant_ids) == 2:
            existing = Conversation.objects.filter(
                is_group=False,
                participants__in=all_participant_ids
            ).annotate(
                participant_count=Count('participants')
            ).filter(participant_count=2)
            
            if existing.exists():
                return existing.first()
        
        # Create conversation
        conversation = Conversation.objects.create(
            is_group=is_group,
            created_by=request_user,
            **validated_data
        )
        
        # Add participants
        participants = User.objects.filter(id__in=all_participant_ids)
        conversation.participants.set(participants)
        
        # Create participant settings
        for participant in participants:
            ConversationParticipant.objects.create(
                conversation=conversation,
                user=participant,
                is_admin=(participant == request_user)
            )
        
        # Send initial message if provided
        if initial_message:
            Message.objects.create(
                conversation=conversation,
                sender=request_user,
                content=initial_message
            )
        
        return conversation

class MessageCreateSerializer(serializers.ModelSerializer):
    attachments = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Message
        fields = ['conversation', 'content', 'reply_to', 'attachments']
    
    def create(self, validated_data):
        attachments = validated_data.pop('attachments', [])
        message = Message.objects.create(**validated_data)
        
        # Create attachments
        for file in attachments:
            MessageAttachment.objects.create(
                message=message,
                file=file,
                file_name=file.name,
                file_size=file.size
            )
        
        # Update conversation's updated_at
        message.conversation.save()
        
        return message

class ChatRequestSerializer(serializers.ModelSerializer):
    from_user = UserSerializer(read_only=True)
    to_user = UserSerializer(read_only=True)
    to_user_id = serializers.IntegerField(write_only=True)
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRequest
        fields = [
            'id', 'from_user', 'to_user', 'to_user_id', 'message',
            'status', 'sent_at', 'responded_at', 'expires_at', 'is_expired'
        ]
        read_only_fields = ['status', 'sent_at', 'responded_at', 'expires_at']
    
    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def validate_to_user_id(self, value):
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
        return value
    
    def validate_message(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Message must be at least 10 characters")
        if len(value) > 500:
            raise serializers.ValidationError("Message must be less than 500 characters")
        return value
    
    def create(self, validated_data):
        to_user_id = validated_data.pop('to_user_id')
        to_user = User.objects.get(id=to_user_id)
        
        # Set expiration (7 days)
        expires_at = timezone.now() + timedelta(days=7)
        
        return ChatRequest.objects.create(
            to_user=to_user,
            expires_at=expires_at,
            **validated_data
        )

class UserConnectionSerializer(serializers.ModelSerializer):
    from_user = UserSerializer(read_only=True)
    to_user = UserSerializer(read_only=True)
    is_mutual = serializers.SerializerMethodField()
    
    class Meta:
        model = UserConnection
        fields = [
            'id', 'from_user', 'to_user', 'connected_at',
            'connection_type', 'notes', 'is_mutual'
        ]
    
    def get_is_mutual(self, obj):
        return UserConnection.objects.filter(
            from_user=obj.to_user,
            to_user=obj.from_user
        ).exists()
