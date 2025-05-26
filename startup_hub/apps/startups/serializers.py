from rest_framework import serializers
from .models import Industry, Startup, StartupFounder, StartupTag, StartupRating, StartupComment, StartupBookmark, StartupLike

class IndustrySerializer(serializers.ModelSerializer):
    startup_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Industry
        fields = ['id', 'name', 'description', 'icon', 'startup_count']
    
    def get_startup_count(self, obj):
        return obj.startups.count()

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

class StartupListSerializer(serializers.ModelSerializer):
    industry_name = serializers.CharField(source='industry.name', read_only=True)
    industry_icon = serializers.CharField(source='industry.icon', read_only=True)
    average_rating = serializers.ReadOnlyField()
    total_ratings = serializers.ReadOnlyField()
    is_bookmarked = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    tags_list = serializers.StringRelatedField(source='tags', many=True, read_only=True)
    
    class Meta:
        model = Startup
        fields = [
            'id', 'name', 'description', 'industry', 'industry_name', 'industry_icon',
            'location', 'logo', 'funding_amount', 'valuation', 'employee_count',
            'founded_year', 'is_featured', 'revenue', 'user_count', 'growth_rate',
            'views', 'average_rating', 'total_ratings', 'is_bookmarked', 'is_liked',
            'tags_list', 'created_at'
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

class StartupDetailSerializer(StartupListSerializer):
    founders = StartupFounderSerializer(many=True, read_only=True)
    tags = StartupTagSerializer(many=True, read_only=True)
    ratings = StartupRatingSerializer(many=True, read_only=True)
    comments = StartupCommentSerializer(many=True, read_only=True)
    
    class Meta(StartupListSerializer.Meta):
        fields = StartupListSerializer.Meta.fields + ['founders', 'tags', 'ratings', 'comments', 'website']