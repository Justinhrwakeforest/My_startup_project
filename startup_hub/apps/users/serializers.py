from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, UserInterest

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name']
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return data
    
    def validate_password(self, value):
        validate_password(value)
        return value
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        if email and password:
            user = authenticate(username=email, password=password)
            if user:
                if user.is_active:
                    data['user'] = user
                else:
                    raise serializers.ValidationError('User account is disabled.')
            else:
                raise serializers.ValidationError('Invalid email or password.')
        else:
            raise serializers.ValidationError('Must include email and password.')
        
        return data

class UserInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserInterest
        fields = ['id', 'interest']

class UserProfileSerializer(serializers.ModelSerializer):
    interests = UserInterestSerializer(many=True, read_only=True)
    total_ratings = serializers.SerializerMethodField()
    total_comments = serializers.SerializerMethodField()
    total_bookmarks = serializers.SerializerMethodField()
    total_likes = serializers.SerializerMethodField()
    member_since = serializers.DateTimeField(source='date_joined', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'bio', 
            'location', 'is_premium', 'member_since', 'interests',
            'total_ratings', 'total_comments', 'total_bookmarks', 'total_likes'
        ]
        read_only_fields = ['email', 'is_premium']
    
    def get_total_ratings(self, obj):
        return obj.startuprating_set.count()
    
    def get_total_comments(self, obj):
        return obj.startupcomment_set.count()
    
    def get_total_bookmarks(self, obj):
        return obj.startupbookmark_set.count()
    
    def get_total_likes(self, obj):
        return obj.startuplike_set.count()

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)
    new_password_confirm = serializers.CharField()
    
    def validate_new_password(self, value):
        validate_password(value)
        return value
    
    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match")
        return data