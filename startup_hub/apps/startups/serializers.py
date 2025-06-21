# startup_hub/apps/startups/serializers.py - Complete file with cover image URL support

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Industry, Startup, StartupFounder, StartupTag, StartupRating, 
    StartupComment, StartupBookmark, StartupLike, UserProfile, StartupEditRequest
)

User = get_user_model()

class IndustrySerializer(serializers.ModelSerializer):
    startup_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Industry
        fields = ['id', 'name', 'description', 'icon', 'startup_count']
    
    def get_startup_count(self, obj):
        return obj.startups.count()

class UserProfileSerializer(serializers.ModelSerializer):
    is_premium_active = serializers.ReadOnlyField()
    
    class Meta:
        model = UserProfile
        fields = ['is_premium', 'premium_expires_at', 'is_premium_active']

class StartupFounderSerializer(serializers.ModelSerializer):
    class Meta:
        model = StartupFounder
        fields = ['id', 'name', 'title', 'bio']

class StartupTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = StartupTag
        fields = ['id', 'tag']

class StartupRatingSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = StartupRating
        fields = ['id', 'user', 'user_name', 'rating', 'created_at']
        read_only_fields = ['user', 'created_at']

class StartupCommentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = StartupComment
        fields = ['id', 'user', 'user_name', 'text', 'likes', 'created_at']
        read_only_fields = ['user', 'likes', 'created_at']

# Base list serializer - MUST come before DetailSerializer
class StartupListSerializer(serializers.ModelSerializer):
    industry_name = serializers.CharField(source='industry.name', read_only=True)
    industry_icon = serializers.CharField(source='industry.icon', read_only=True)
    average_rating = serializers.ReadOnlyField()
    total_ratings = serializers.ReadOnlyField()
    is_bookmarked = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    tags_list = serializers.StringRelatedField(source='tags', many=True, read_only=True)
    total_likes = serializers.SerializerMethodField()
    total_bookmarks = serializers.SerializerMethodField()
    total_comments = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    has_pending_edits = serializers.SerializerMethodField()
    cover_image_display_url = serializers.ReadOnlyField()  # Add this field
    
    class Meta:
        model = Startup
        fields = [
            'id', 'name', 'description', 'industry', 'industry_name', 'industry_icon',
            'location', 'website', 'logo', 'funding_amount', 'valuation', 'employee_count',
            'founded_year', 'is_featured', 'revenue', 'user_count', 'growth_rate',
            'views', 'average_rating', 'total_ratings', 'is_bookmarked', 'is_liked',
            'tags_list', 'created_at', 'total_likes', 'total_bookmarks', 'total_comments',
            'cover_image_url', 'cover_image_display_url', 'can_edit', 'has_pending_edits', 'is_approved',
            'contact_email', 'contact_phone', 'business_model', 'target_market'
        ]
    
    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return StartupBookmark.objects.filter(startup=obj, user=request.user).exists()
        return False
    
    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return StartupLike.objects.filter(startup=obj, user=request.user).exists()
        return False
    
    def get_total_likes(self, obj):
        return obj.likes.count()
    
    def get_total_bookmarks(self, obj):
        return obj.bookmarks.count()
    
    def get_total_comments(self, obj):
        return obj.comments.count()
    
    def get_can_edit(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_edit(request.user)
        return False
    
    def get_has_pending_edits(self, obj):
        return obj.has_pending_edits()

# Detailed serializers for startup detail page
class StartupFounderDetailSerializer(serializers.ModelSerializer):
    """Detailed founder information for startup detail page"""
    class Meta:
        model = StartupFounder
        fields = ['id', 'name', 'title', 'bio', 'linkedin_url', 'twitter_url']

class StartupTagDetailSerializer(serializers.ModelSerializer):
    """Tag information for startup detail page"""
    class Meta:
        model = StartupTag
        fields = ['id', 'tag']

class StartupRatingDetailSerializer(serializers.ModelSerializer):
    """Rating information with user details"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_first_name = serializers.CharField(source='user.first_name', read_only=True)
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = StartupRating
        fields = ['id', 'user', 'user_name', 'user_first_name', 'rating', 'created_at', 'time_ago']
        read_only_fields = ['user', 'created_at']
    
    def get_time_ago(self, obj):
        from django.utils import timezone
        diff = timezone.now() - obj.created_at
        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} hours ago"
        else:
            return f"{diff.seconds // 60} minutes ago"

class StartupCommentDetailSerializer(serializers.ModelSerializer):
    """Comment information with user details"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_first_name = serializers.CharField(source='user.first_name', read_only=True)
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = StartupComment
        fields = ['id', 'user', 'user_name', 'user_first_name', 'text', 'likes', 'created_at', 'time_ago']
        read_only_fields = ['user', 'likes', 'created_at']
    
    def get_time_ago(self, obj):
        from django.utils import timezone
        diff = timezone.now() - obj.created_at
        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} hours ago"
        else:
            return f"{diff.seconds // 60} minutes ago"

# Edit Request Serializers
class StartupEditRequestSerializer(serializers.ModelSerializer):
    """Serializer for creating edit requests"""
    changes_display = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = StartupEditRequest
        fields = [
            'id', 'startup', 'requested_by', 'status', 'proposed_changes',
            'original_values', 'changes_display', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'requested_by', 'status', 'original_values', 'created_at', 'updated_at']
    
    def get_changes_display(self, obj):
        return obj.get_changes_display()

class StartupEditRequestDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for viewing edit requests"""
    startup_name = serializers.CharField(source='startup.name', read_only=True)
    requested_by_username = serializers.CharField(source='requested_by.username', read_only=True)
    reviewed_by_username = serializers.CharField(source='reviewed_by.username', read_only=True, allow_null=True)
    changes_display = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = StartupEditRequest
        fields = [
            'id', 'startup', 'startup_name', 'requested_by', 'requested_by_username',
            'status', 'proposed_changes', 'original_values', 'changes_display',
            'reviewed_by', 'reviewed_by_username', 'reviewed_at', 'review_notes',
            'created_at', 'updated_at', 'time_ago'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_changes_display(self, obj):
        return obj.get_changes_display()
    
    def get_time_ago(self, obj):
        from django.utils import timezone
        diff = timezone.now() - obj.created_at
        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} hours ago"
        else:
            return f"{diff.seconds // 60} minutes ago"

# Startup creation serializer
class StartupCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new startups"""
    founders = serializers.ListField(
        child=serializers.DictField(), 
        write_only=True, 
        required=False,
        help_text="List of founder objects with name, title, and bio"
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=30), 
        write_only=True, 
        required=False,
        help_text="List of tag strings"
    )
    
    class Meta:
        model = Startup
        fields = [
            'name', 'description', 'industry', 'location', 'website', 'logo',
            'funding_amount', 'valuation', 'employee_count', 'founded_year',
            'revenue', 'user_count', 'growth_rate', 'cover_image_url',  # ADDED cover_image_url
            'is_featured', 'founders', 'tags', 'contact_email', 'contact_phone',
            'business_model', 'target_market'
        ]
        extra_kwargs = {
            'name': {'required': True},
            'description': {'required': True},
            'industry': {'required': True},
            'location': {'required': True},
            'employee_count': {'required': True},
            'founded_year': {'required': True},
        }
    
    def validate_name(self, value):
        """Validate startup name"""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters long")
        if len(value) > 100:
            raise serializers.ValidationError("Name must be less than 100 characters")
        return value.strip()
    
    def validate_description(self, value):
        """Validate description"""
        if len(value.strip()) < 50:
            raise serializers.ValidationError("Description must be at least 50 characters long")
        if len(value) > 2000:
            raise serializers.ValidationError("Description must be less than 2000 characters")
        return value.strip()
    
    def validate_employee_count(self, value):
        """Validate employee count"""
        if value < 1:
            raise serializers.ValidationError("Employee count must be at least 1")
        if value > 100000:
            raise serializers.ValidationError("Employee count seems unrealistic")
        return value
    
    def validate_founded_year(self, value):
        """Validate founded year"""
        from datetime import datetime
        current_year = datetime.now().year
        
        if value < 1800:
            raise serializers.ValidationError("Founded year seems too early")
        if value > current_year:
            raise serializers.ValidationError("Founded year cannot be in the future")
        return value
    
    def validate_website(self, value):
        """Validate website URL"""
        if value and not value.startswith(('http://', 'https://')):
            return f'https://{value}'
        return value
    
    def validate_cover_image_url(self, value):
        """Validate cover image URL"""
        if value:
            # Basic URL validation
            if not value.startswith(('http://', 'https://')):
                raise serializers.ValidationError("Cover image URL must start with http:// or https://")
            
            # Check if URL ends with common image extensions
            valid_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
            if not any(value.lower().endswith(ext) for ext in valid_extensions):
                # Don't enforce this strictly, as some URLs might not have extensions
                pass
        
        return value
    
    def validate_founders(self, value):
        """Validate founders list"""
        if not value:
            return value
            
        valid_founders = []
        for founder_data in value:
            if not isinstance(founder_data, dict):
                raise serializers.ValidationError("Each founder must be an object")
            
            name = founder_data.get('name', '').strip()
            if not name:
                continue  # Skip empty founders
                
            if len(name) > 100:
                raise serializers.ValidationError("Founder name too long")
            
            title = founder_data.get('title', 'Founder').strip()
            bio = founder_data.get('bio', '').strip()
            
            if len(title) > 100:
                raise serializers.ValidationError("Founder title too long")
            if len(bio) > 500:
                raise serializers.ValidationError("Founder bio too long")
            
            valid_founders.append({
                'name': name,
                'title': title,
                'bio': bio,
                'linkedin_url': founder_data.get('linkedin_url', ''),
                'twitter_url': founder_data.get('twitter_url', '')
            })
        
        if not valid_founders:
            raise serializers.ValidationError("At least one founder is required")
        
        if len(valid_founders) > 5:
            raise serializers.ValidationError("Maximum 5 founders allowed")
        
        return valid_founders
    
    def validate_tags(self, value):
        """Validate tags list"""
        if not value:
            return []
            
        valid_tags = []
        for tag in value:
            tag = tag.strip()
            if not tag:
                continue
            if len(tag) > 30:
                raise serializers.ValidationError("Tag too long (max 30 characters)")
            if tag not in valid_tags:  # Avoid duplicates
                valid_tags.append(tag)
        
        if len(valid_tags) > 10:
            raise serializers.ValidationError("Maximum 10 tags allowed")
        
        return valid_tags
    
    def create(self, validated_data):
        """Create startup with founders and tags"""
        founders_data = validated_data.pop('founders', [])
        tags_data = validated_data.pop('tags', [])
        
        # Create the startup
        startup = Startup.objects.create(**validated_data)
        
        # Create founders
        for founder_data in founders_data:
            StartupFounder.objects.create(startup=startup, **founder_data)
        
        # Create tags
        for tag in tags_data:
            StartupTag.objects.create(startup=startup, tag=tag)
        
        return startup

# Detail serializer - NOW comes after StartupListSerializer
class StartupDetailSerializer(StartupListSerializer):
    """Comprehensive startup detail serializer"""
    industry_detail = serializers.SerializerMethodField()
    
    # User interaction status
    user_rating = serializers.SerializerMethodField()
    
    # Related data
    founders = StartupFounderDetailSerializer(many=True, read_only=True)
    tags = StartupTagDetailSerializer(many=True, read_only=True)
    
    # Ratings and comments with pagination-like limiting
    recent_ratings = serializers.SerializerMethodField()
    recent_comments = serializers.SerializerMethodField()
    
    # Jobs at this startup - using method field to avoid circular import
    open_jobs = serializers.SerializerMethodField()
    
    # Similar startups
    similar_startups = serializers.SerializerMethodField()
    
    # Social proof metrics
    engagement_metrics = serializers.SerializerMethodField()
    
    # Edit request info
    pending_edit_requests = serializers.SerializerMethodField()
    
    # Submitted by info
    submitted_by_username = serializers.CharField(source='submitted_by.username', read_only=True, allow_null=True)
    
    # Social media field
    social_media = serializers.JSONField(read_only=True)
    
    class Meta(StartupListSerializer.Meta):
        fields = StartupListSerializer.Meta.fields + [
            'industry_detail', 'user_rating', 'founders', 'tags',
            'recent_ratings', 'recent_comments', 'open_jobs',
            'similar_startups', 'engagement_metrics', 'pending_edit_requests',
            'submitted_by', 'submitted_by_username', 'social_media'
        ]
    
    def get_industry_detail(self, obj):
        """Get industry information"""
        return {
            'id': obj.industry.id,
            'name': obj.industry.name,
            'icon': obj.industry.icon,
            'description': obj.industry.description
        }
    
    def get_user_rating(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            rating = StartupRating.objects.filter(startup=obj, user=request.user).first()
            return rating.rating if rating else None
        return None
    
    def get_recent_ratings(self, obj):
        """Get 5 most recent ratings"""
        recent_ratings = obj.ratings.select_related('user').order_by('-created_at')[:5]
        return StartupRatingDetailSerializer(recent_ratings, many=True).data
    
    def get_recent_comments(self, obj):
        """Get 10 most recent comments"""
        recent_comments = obj.comments.select_related('user').order_by('-created_at')[:10]
        return StartupCommentDetailSerializer(recent_comments, many=True).data
    
    def get_open_jobs(self, obj):
        """Get open jobs at this startup - using inline serialization to avoid circular import"""
        jobs = obj.jobs.filter(is_active=True).select_related('job_type').prefetch_related('skills')[:5]
        
        # Inline job serialization to avoid circular import
        jobs_data = []
        for job in jobs:
            job_data = {
                'id': job.id,
                'title': job.title,
                'description': job.description,
                'location': job.location,
                'salary_range': job.salary_range,
                'is_remote': job.is_remote,
                'is_urgent': job.is_urgent,
                'experience_level': job.experience_level,
                'experience_level_display': job.get_experience_level_display(),
                'job_type_name': job.job_type.name if job.job_type else '',
                'posted_ago': job.posted_ago,
                'skills_list': [skill.skill for skill in job.skills.all()],
                'posted_at': job.posted_at,
            }
            jobs_data.append(job_data)
        
        return jobs_data
    
    def get_similar_startups(self, obj):
        """Get similar startups based on industry and tags"""
        from django.db.models import Q, Count
        
        # Get startups in same industry or with similar tags
        similar = Startup.objects.filter(
            Q(industry=obj.industry) | 
            Q(tags__tag__in=obj.tags.values_list('tag', flat=True))
        ).exclude(id=obj.id).annotate(
            similarity_score=Count('tags__tag', filter=Q(tags__tag__in=obj.tags.values_list('tag', flat=True)))
        ).order_by('-similarity_score', '-views')[:6]
        
        # Use a lighter serializer to avoid circular references
        return [{
            'id': startup.id,
            'name': startup.name,
            'logo': startup.logo,
            'industry_name': startup.industry.name,
            'location': startup.location,
            'employee_count': startup.employee_count,
            'average_rating': startup.average_rating,
            'is_featured': startup.is_featured,
            'cover_image_url': startup.cover_image_url
        } for startup in similar]
    
    def get_engagement_metrics(self, obj):
        """Calculate engagement metrics for the startup"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Calculate metrics for the past 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        recent_ratings = obj.ratings.filter(created_at__gte=thirty_days_ago).count()
        recent_comments = obj.comments.filter(created_at__gte=thirty_days_ago).count()
        recent_likes = obj.likes.filter(created_at__gte=thirty_days_ago).count()
        recent_bookmarks = obj.bookmarks.filter(created_at__gte=thirty_days_ago).count()
        
        total_engagement = recent_ratings + recent_comments + recent_likes + recent_bookmarks
        
        # Calculate engagement trend (basic implementation)
        prev_thirty_days = thirty_days_ago - timedelta(days=30)
        prev_engagement = (
            obj.ratings.filter(created_at__gte=prev_thirty_days, created_at__lt=thirty_days_ago).count() +
            obj.comments.filter(created_at__gte=prev_thirty_days, created_at__lt=thirty_days_ago).count() +
            obj.likes.filter(created_at__gte=prev_thirty_days, created_at__lt=thirty_days_ago).count() +
            obj.bookmarks.filter(created_at__gte=prev_thirty_days, created_at__lt=thirty_days_ago).count()
        )
        
        if prev_engagement > 0:
            engagement_change = ((total_engagement - prev_engagement) / prev_engagement) * 100
        else:
            engagement_change = 100 if total_engagement > 0 else 0
        
        return {
            'total_engagement_30d': total_engagement,
            'recent_ratings': recent_ratings,
            'recent_comments': recent_comments,
            'recent_likes': recent_likes,
            'recent_bookmarks': recent_bookmarks,
            'engagement_change_percent': round(engagement_change, 1)
        }
    
    def get_pending_edit_requests(self, obj):
        """Get pending edit requests if user has permission to see them"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return []
        
        # Only show to admins or the startup submitter
        if not (request.user.is_staff or request.user.is_superuser or request.user == obj.submitted_by):
            return []
        
        pending_requests = obj.edit_requests.filter(status='pending').order_by('-created_at')[:5]
        return StartupEditRequestDetailSerializer(pending_requests, many=True).data
