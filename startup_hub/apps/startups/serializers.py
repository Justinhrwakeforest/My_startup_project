# apps/startups/serializers.py - Enhanced serializers for startup details

from rest_framework import serializers
from .models import Industry, Startup, StartupFounder, StartupTag, StartupRating, StartupComment, StartupBookmark, StartupLike
from apps.jobs.models import Job
from apps.jobs.serializers import JobListSerializer

class StartupFounderDetailSerializer(serializers.ModelSerializer):
    """Detailed founder information for startup detail page"""
    class Meta:
        model = StartupFounder
        fields = ['id', 'name', 'title', 'bio']

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

class StartupDetailSerializer(serializers.ModelSerializer):
    """Comprehensive startup detail serializer"""
    industry_name = serializers.CharField(source='industry.name', read_only=True)
    industry_icon = serializers.CharField(source='industry.icon', read_only=True)
    industry_detail = serializers.SerializerMethodField()
    
    # User interaction status
    is_bookmarked = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    user_rating = serializers.SerializerMethodField()
    
    # Related data
    founders = StartupFounderDetailSerializer(many=True, read_only=True)
    tags = StartupTagDetailSerializer(many=True, read_only=True)
    tags_list = serializers.StringRelatedField(source='tags', many=True, read_only=True)
    
    # Ratings and comments with pagination-like limiting
    recent_ratings = serializers.SerializerMethodField()
    recent_comments = serializers.SerializerMethodField()
    
    # Jobs at this startup
    open_jobs = serializers.SerializerMethodField()
    
    # Statistics
    average_rating = serializers.ReadOnlyField()
    total_ratings = serializers.ReadOnlyField()
    total_likes = serializers.SerializerMethodField()
    total_bookmarks = serializers.SerializerMethodField()
    total_comments = serializers.SerializerMethodField()
    
    # Similar startups
    similar_startups = serializers.SerializerMethodField()
    
    # Social proof metrics
    engagement_metrics = serializers.SerializerMethodField()
    
    class Meta:
        model = Startup
        fields = [
            'id', 'name', 'description', 'industry', 'industry_name', 'industry_icon', 'industry_detail',
            'location', 'website', 'logo', 'funding_amount', 'valuation', 'employee_count',
            'founded_year', 'is_featured', 'revenue', 'user_count', 'growth_rate',
            'views', 'created_at', 'updated_at',
            'is_bookmarked', 'is_liked', 'user_rating',
            'founders', 'tags', 'tags_list',
            'recent_ratings', 'recent_comments', 'open_jobs',
            'average_rating', 'total_ratings', 'total_likes', 'total_bookmarks', 'total_comments',
            'similar_startups', 'engagement_metrics'
        ]
    
    def get_industry_detail(self, obj):
        """Get industry information"""
        return {
            'id': obj.industry.id,
            'name': obj.industry.name,
            'icon': obj.industry.icon,
            'description': obj.industry.description
        }
    
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
        """Get open jobs at this startup"""
        jobs = obj.jobs.filter(is_active=True).select_related('job_type').prefetch_related('skills')[:5]
        return JobListSerializer(jobs, many=True, context=self.context).data
    
    def get_total_likes(self, obj):
        return obj.likes.count()
    
    def get_total_bookmarks(self, obj):
        return obj.bookmarks.count()
    
    def get_total_comments(self, obj):
        return obj.comments.count()
    
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
            'is_featured': startup.is_featured
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
