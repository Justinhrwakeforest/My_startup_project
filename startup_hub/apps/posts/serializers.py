# startup_hub/apps/posts/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import (
    Topic, Post, PostImage, PostLink, Comment, PostReaction,
    CommentReaction, PostBookmark, PostView, PostShare, Mention,
    PostReport
)
import re
from django.db import transaction

User = get_user_model()

class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ['id', 'name', 'slug', 'description', 'icon', 'post_count', 'follower_count']
        read_only_fields = ['slug', 'post_count', 'follower_count']

class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = ['id', 'image', 'caption', 'order']

class PostLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostLink
        fields = ['id', 'url', 'title', 'description', 'image_url', 'domain']
        read_only_fields = ['title', 'description', 'image_url', 'domain']

class AuthorSerializer(serializers.ModelSerializer):
    """Serializer for post/comment authors"""
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'avatar_url', 'is_verified']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    
    def get_avatar_url(self, obj):
        # Implement avatar logic here
        return None
    
    def get_is_verified(self, obj):
        return obj.is_staff or getattr(obj, 'is_verified', False)

class CommentSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    author_name = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'post', 'author', 'author_name', 'parent', 'content',
            'is_anonymous', 'created_at', 'updated_at', 'edited_at',
            'like_count', 'reply_count', 'replies', 'is_liked',
            'can_edit', 'can_delete'
        ]
        read_only_fields = ['author', 'created_at', 'updated_at', 'edited_at', 'like_count', 'reply_count']
    
    def get_author_name(self, obj):
        return obj.get_author_name()
    
    def get_replies(self, obj):
        if obj.parent is None:  # Only show replies for top-level comments
            replies = obj.replies.filter(is_approved=True).order_by('created_at')
            return CommentSerializer(replies, many=True, context=self.context).data
        return []
    
    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.reactions.filter(user=request.user, is_like=True).exists()
        return False
    
    def get_can_edit(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_edit(request.user)
        return False
    
    def get_can_delete(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user == obj.author or request.user.is_staff
        return False

class PostReactionSerializer(serializers.ModelSerializer):
    user = AuthorSerializer(read_only=True)
    
    class Meta:
        model = PostReaction
        fields = ['id', 'user', 'reaction_type', 'created_at']
        read_only_fields = ['user', 'created_at']

class PostListSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    author_name = serializers.SerializerMethodField()
    topics = TopicSerializer(many=True, read_only=True)
    topic_names = serializers.ListField(write_only=True, required=False)
    
    # Metrics
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    user_reaction = serializers.SerializerMethodField()
    
    # Permissions
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    
    # Related content preview
    first_image = serializers.SerializerMethodField()
    content_preview = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'author', 'author_name', 'title', 'content_preview', 'post_type',
            'topics', 'topic_names', 'is_anonymous', 'is_pinned', 'is_locked',
            'created_at', 'updated_at', 'view_count', 'like_count', 'comment_count',
            'share_count', 'bookmark_count', 'is_liked', 'is_bookmarked',
            'user_reaction', 'can_edit', 'can_delete', 'first_image'
        ]
        read_only_fields = [
            'author', 'created_at', 'updated_at', 'view_count', 'like_count',
            'comment_count', 'share_count', 'bookmark_count'
        ]
    
    def get_author_name(self, obj):
        return obj.get_author_name()
    
    def get_content_preview(self, obj):
        # Return first 200 characters of content
        return obj.content[:200] + '...' if len(obj.content) > 200 else obj.content
    
    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.reactions.filter(user=request.user).exists()
        return False
    
    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.bookmarks.filter(user=request.user).exists()
        return False
    
    def get_user_reaction(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            reaction = obj.reactions.filter(user=request.user).first()
            return reaction.reaction_type if reaction else None
        return None
    
    def get_can_edit(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_edit(request.user)
        return False
    
    def get_can_delete(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_delete(request.user)
        return False
    
    def get_first_image(self, obj):
        first_image = obj.images.first()
        if first_image:
            return PostImageSerializer(first_image).data
        return None

class PostDetailSerializer(PostListSerializer):
    """Detailed post serializer with all content"""
    content = serializers.CharField()  # Full content
    images = PostImageSerializer(many=True, read_only=True)
    links = PostLinkSerializer(many=True, read_only=True)
    comments = serializers.SerializerMethodField()
    reactions_summary = serializers.SerializerMethodField()
    related_startup = serializers.SerializerMethodField()
    related_job = serializers.SerializerMethodField()
    
    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + [
            'content', 'images', 'links', 'comments', 'reactions_summary',
            'related_startup', 'related_job', 'slug', 'meta_description'
        ]
    
    def get_comments(self, obj):
        # Get top-level comments only
        comments = obj.comments.filter(parent=None, is_approved=True).order_by('-created_at')
        return CommentSerializer(comments, many=True, context=self.context).data
    
    def get_reactions_summary(self, obj):
        # Group reactions by type
        summary = {}
        for reaction_type, emoji in PostReaction.REACTION_TYPES:
            count = obj.reactions.filter(reaction_type=reaction_type).count()
            if count > 0:
                summary[reaction_type] = {
                    'emoji': emoji,
                    'count': count
                }
        return summary
    
    def get_related_startup(self, obj):
        if obj.related_startup:
            from apps.startups.serializers import StartupListSerializer
            return StartupListSerializer(obj.related_startup, context=self.context).data
        return None
    
    def get_related_job(self, obj):
        if obj.related_job:
            from apps.jobs.serializers import JobListSerializer
            return JobListSerializer(obj.related_job, context=self.context).data
        return None

class PostCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating posts"""
    topic_names = serializers.ListField(
        child=serializers.CharField(max_length=50),
        write_only=True,
        required=False
    )
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False
    )
    mentioned_users = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Post
        fields = [
            'title', 'content', 'post_type', 'is_anonymous', 'is_draft',
            'topic_names', 'images', 'mentioned_users', 'related_startup',
            'related_job'
        ]
    
    def validate_content(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Content must be at least 10 characters long.")
        return value
    
    def create(self, validated_data):
        topic_names = validated_data.pop('topic_names', [])
        images = validated_data.pop('images', [])
        mentioned_users = validated_data.pop('mentioned_users', [])
        
        with transaction.atomic():
            # Create post
            post = Post.objects.create(**validated_data)
            
            # Handle topics
            for topic_name in topic_names:
                topic_name = topic_name.strip().lower()
                if topic_name:
                    topic, created = Topic.objects.get_or_create(
                        slug=topic_name.replace(' ', '-'),
                        defaults={'name': topic_name}
                    )
                    post.topics.add(topic)
                    topic.post_count = F('post_count') + 1
                    topic.save()
            
            # Handle images
            for i, image in enumerate(images):
                PostImage.objects.create(
                    post=post,
                    image=image,
                    order=i
                )
            
            # Handle mentions
            self._process_mentions(post, mentioned_users)
            
            return post
    
    def _process_mentions(self, post, mentioned_usernames):
        """Process @mentions in post content"""
        # Extract mentions from content
        content_mentions = re.findall(r'@(\w+)', post.content)
        all_mentions = set(mentioned_usernames + content_mentions)
        
        for username in all_mentions:
            try:
                user = User.objects.get(username=username)
                Mention.objects.create(
                    post=post,
                    mentioned_user=user,
                    mentioned_by=post.author
                )
            except User.DoesNotExist:
                pass

class CommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating comments"""
    mentioned_users = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Comment
        fields = ['post', 'parent', 'content', 'is_anonymous', 'mentioned_users']
    
    def validate_content(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Comment must be at least 2 characters long.")
        return value
    
    def create(self, validated_data):
        mentioned_users = validated_data.pop('mentioned_users', [])
        
        with transaction.atomic():
            comment = Comment.objects.create(**validated_data)
            
            # Update counts
            comment.post.comment_count = F('comment_count') + 1
            comment.post.save()
            
            if comment.parent:
                comment.parent.reply_count = F('reply_count') + 1
                comment.parent.save()
            
            # Handle mentions
            self._process_mentions(comment, mentioned_users)
            
            return comment
    
    def _process_mentions(self, comment, mentioned_usernames):
        """Process @mentions in comment"""
        content_mentions = re.findall(r'@(\w+)', comment.content)
        all_mentions = set(mentioned_usernames + content_mentions)
        
        for username in all_mentions:
            try:
                user = User.objects.get(username=username)
                Mention.objects.create(
                    comment=comment,
                    mentioned_user=user,
                    mentioned_by=comment.author
                )
            except User.DoesNotExist:
                pass

class PostBookmarkSerializer(serializers.ModelSerializer):
    post = PostListSerializer(read_only=True)
    
    class Meta:
        model = PostBookmark
        fields = ['id', 'post', 'created_at', 'notes']
        read_only_fields = ['created_at']

class PostReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostReport
        fields = ['id', 'post', 'reason', 'description', 'created_at']
        read_only_fields = ['created_at']
    
    def validate_description(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Please provide more details (at least 10 characters).")
        return value
