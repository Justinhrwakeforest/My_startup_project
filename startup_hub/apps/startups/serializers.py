# startup_hub/apps/startups/serializers.py - Complete file with startup claiming support

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import (
    Industry, Startup, StartupFounder, StartupTag, StartupRating, 
    StartupComment, StartupBookmark, StartupLike, UserProfile, 
    StartupEditRequest, StartupClaimRequest
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

# Claim Request Serializers
class StartupClaimRequestSerializer(serializers.ModelSerializer):
    """Serializer for creating claim requests"""
    startup_name = serializers.CharField(source='startup.name', read_only=True)
    startup_domain = serializers.SerializerMethodField(read_only=True)
    email_domain_valid = serializers.SerializerMethodField(read_only=True)
    time_ago = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = StartupClaimRequest
        fields = [
            'id', 'startup', 'startup_name', 'startup_domain', 'email', 'position', 
            'reason', 'email_verified', 'email_verified_at', 'status', 'created_at', 
            'expires_at', 'email_domain_valid', 'time_ago'
        ]
        read_only_fields = [
            'id', 'email_verified', 'email_verified_at', 'status', 'created_at', 
            'expires_at'
        ]
    
    def get_startup_domain(self, obj):
        return obj.startup.get_company_domain()
    
    def get_email_domain_valid(self, obj):
        return obj.is_email_domain_valid()
    
    def get_time_ago(self, obj):
        from django.utils import timezone
        diff = timezone.now() - obj.created_at
        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} hours ago"
        else:
            return f"{diff.seconds // 60} minutes ago"
    
    def validate_email(self, value):
        """Validate email format and domain"""
        if not value:
            raise serializers.ValidationError("Email is required")
        
        # Basic email validation
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            raise serializers.ValidationError("Invalid email format")
        
        return value.lower()
    
    def validate_position(self, value):
        """Validate position field"""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Position must be at least 2 characters long")
        if len(value) > 100:
            raise serializers.ValidationError("Position must be less than 100 characters")
        return value.strip()
    
    def validate_reason(self, value):
        """Validate reason field"""
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError("Reason must be at least 10 characters long")
        if len(value) > 1000:
            raise serializers.ValidationError("Reason must be less than 1000 characters")
        return value.strip()
    
    def validate(self, attrs):
        """Validate the entire claim request"""
        startup = attrs.get('startup')
        email = attrs.get('email')
        
        if startup and email:
            # Check if email domain matches startup domain
            email_domain = email.split('@')[1].lower()
            startup_domain = startup.get_company_domain()
            
            if not startup_domain:
                raise serializers.ValidationError({
                    'startup': 'This startup does not have a website configured for domain verification.'
                })
            
            # Check domain match
            if not (email_domain == startup_domain or email_domain.endswith('.' + startup_domain)):
                raise serializers.ValidationError({
                    'email': f'Email domain ({email_domain}) does not match startup domain ({startup_domain}). Please use a company email address.'
                })
        
        return attrs
    
    def create(self, validated_data):
        """Create claim request with verification token"""
        # Set expiration time (24 hours)
        validated_data['expires_at'] = timezone.now() + timedelta(hours=24)
        
        # Create the claim request
        claim_request = StartupClaimRequest.objects.create(**validated_data)
        
        # Generate verification token
        claim_request.generate_verification_token()
        claim_request.save()
        
        return claim_request

class StartupClaimRequestDetailSerializer(StartupClaimRequestSerializer):
    """Detailed serializer for viewing claim requests (admin)"""
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    reviewed_by_username = serializers.CharField(source='reviewed_by.username', read_only=True, allow_null=True)
    startup_website = serializers.CharField(source='startup.website', read_only=True)
    is_expired = serializers.SerializerMethodField()
    
    class Meta(StartupClaimRequestSerializer.Meta):
        fields = StartupClaimRequestSerializer.Meta.fields + [
            'user_username', 'user_email', 'reviewed_by', 'reviewed_by_username', 
            'reviewed_at', 'review_notes', 'startup_website', 'verification_token', 
            'is_expired', 'updated_at'
        ]
        read_only_fields = StartupClaimRequestSerializer.Meta.read_only_fields + [
            'user', 'reviewed_by', 'reviewed_at', 'review_notes', 'verification_token',
            'updated_at'
        ]
    
    def get_is_expired(self, obj):
        return obj.is_expired()

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
    can_claim = serializers.SerializerMethodField()
    has_pending_edits = serializers.SerializerMethodField()
    has_pending_claims = serializers.SerializerMethodField()
    cover_image_display_url = serializers.ReadOnlyField()
    
    # Claim information
    is_claimed = serializers.ReadOnlyField()
    claim_verified = serializers.ReadOnlyField()
    claimed_by_username = serializers.CharField(source='claimed_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = Startup
        fields = [
            'id', 'name', 'description', 'industry', 'industry_name', 'industry_icon',
            'location', 'website', 'logo', 'funding_amount', 'valuation', 'employee_count',
            'founded_year', 'is_featured', 'revenue', 'user_count', 'growth_rate',
            'views', 'average_rating', 'total_ratings', 'is_bookmarked', 'is_liked',
            'tags_list', 'created_at', 'total_likes', 'total_bookmarks', 'total_comments',
            'cover_image_url', 'cover_image_display_url', 'can_edit', 'can_claim', 'has_pending_edits',
            'has_pending_claims', 'is_approved', 'contact_email', 'contact_phone', 
            'business_model', 'target_market', 'is_claimed', 'claim_verified', 'claimed_by_username'
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
    
    def get_can_claim(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_claim(request.user)
        return False
    
    def get_has_pending_edits(self, obj):
        return obj.has_pending_edits()
    
    def get_has_pending_claims(self, obj):
        return obj.has_pending_claims()
