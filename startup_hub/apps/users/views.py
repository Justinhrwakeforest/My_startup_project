# apps/users/views.py - Enhanced with additional endpoints
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import check_password
from django.http import JsonResponse
import json
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer, 
    ChangePasswordSerializer, UserInterestSerializer
)
from .models import User, UserInterest

class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Create auth token
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'user': UserProfileSerializer(user).data,
            'token': token.key,
            'message': 'Account created successfully!'
        }, status=status.HTTP_201_CREATED)

class UserLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # Create or get auth token
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'user': UserProfileSerializer(user).data,
            'token': token.key,
            'message': 'Login successful!'
        })

class UserLogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            # Delete the user's token
            request.user.auth_token.delete()
        except:
            pass
        
        return Response({'message': 'Successfully logged out'})

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def delete(self, request, *args, **kwargs):
        """Delete user account"""
        user = self.get_object()
        user.delete()
        return Response({'message': 'Account deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        
        # Check old password
        if not check_password(serializer.validated_data['old_password'], user.password):
            return Response({'error': 'Old password is incorrect'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({'message': 'Password changed successfully'})

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def user_interests(request):
    """Get or add user interests"""
    if request.method == 'GET':
        interests = request.user.interests.all()
        serializer = UserInterestSerializer(interests, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        interest_name = request.data.get('interest', '').strip()
        if not interest_name:
            return Response({'error': 'Interest name is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        interest, created = UserInterest.objects.get_or_create(
            user=request.user, interest=interest_name
        )
        
        if created:
            return Response({'message': 'Interest added successfully'}, 
                          status=status.HTTP_201_CREATED)
        else:
            return Response({'message': 'Interest already exists'})

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_user_interest(request, interest_id):
    """Remove a user interest"""
    try:
        interest = UserInterest.objects.get(id=interest_id, user=request.user)
        interest.delete()
        return Response({'message': 'Interest removed successfully'})
    except UserInterest.DoesNotExist:
        return Response({'error': 'Interest not found'}, 
                      status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_activity(request):
    """Get user's activity summary"""
    user = request.user
    
    # Get recent ratings
    recent_ratings = user.startuprating_set.select_related('startup').order_by('-created_at')[:10]
    
    # Get recent comments
    recent_comments = user.startupcomment_set.select_related('startup').order_by('-created_at')[:10]
    
    # Get bookmarked startups
    bookmarks = user.startupbookmark_set.select_related('startup').order_by('-created_at')[:20]
    
    # Get liked startups
    likes = user.startuplike_set.select_related('startup').order_by('-created_at')[:20]
    
    return Response({
        'recent_ratings': [
            {
                'startup_id': rating.startup.id,
                'startup_name': rating.startup.name,
                'startup_logo': rating.startup.logo,
                'rating': rating.rating,
                'created_at': rating.created_at
            } for rating in recent_ratings
        ],
        'recent_comments': [
            {
                'startup_id': comment.startup.id,
                'startup_name': comment.startup.name,
                'startup_logo': comment.startup.logo,
                'text': comment.text,
                'created_at': comment.created_at
            } for comment in recent_comments
        ],
        'bookmarked_startups': [
            {
                'startup_id': bookmark.startup.id,
                'startup_name': bookmark.startup.name,
                'startup_logo': bookmark.startup.logo,
                'created_at': bookmark.created_at
            } for bookmark in bookmarks
        ],
        'liked_startups': [
            {
                'startup_id': like.startup.id,
                'startup_name': like.startup.name,
                'startup_logo': like.startup.logo,
                'created_at': like.created_at
            } for like in likes
        ]
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def export_user_data(request):
    """Export all user data"""
    user = request.user
    
    # Collect all user data
    data = {
        'user_info': {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'bio': user.bio,
            'location': user.location,
            'date_joined': user.date_joined.isoformat(),
            'is_premium': user.is_premium
        },
        'interests': [
            interest.interest for interest in user.interests.all()
        ],
        'ratings': [
            {
                'startup_name': rating.startup.name,
                'rating': rating.rating,
                'created_at': rating.created_at.isoformat()
            } for rating in user.startuprating_set.select_related('startup').all()
        ],
        'comments': [
            {
                'startup_name': comment.startup.name,
                'text': comment.text,
                'created_at': comment.created_at.isoformat()
            } for comment in user.startupcomment_set.select_related('startup').all()
        ],
        'bookmarks': [
            {
                'startup_name': bookmark.startup.name,
                'created_at': bookmark.created_at.isoformat()
            } for bookmark in user.startupbookmark_set.select_related('startup').all()
        ],
        'likes': [
            {
                'startup_name': like.startup.name,
                'created_at': like.created_at.isoformat()
            } for like in user.startuplike_set.select_related('startup').all()
        ],
        'job_applications': [
            {
                'job_title': app.job.title,
                'startup_name': app.job.startup.name,
                'status': app.status,
                'applied_at': app.applied_at.isoformat()
            } for app in user.jobapplication_set.select_related('job__startup').all()
        ]
    }
    
    return Response(data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_bookmarks(request):
    """Get user's bookmarked startups with full startup data"""
    user = request.user
    
    # Get bookmarked startups
    bookmarked_startup_ids = user.startupbookmark_set.values_list('startup_id', flat=True)
    
    from apps.startups.models import Startup
    from apps.startups.serializers import StartupListSerializer
    
    bookmarked_startups = Startup.objects.filter(
        id__in=bookmarked_startup_ids
    ).select_related('industry').prefetch_related('tags', 'ratings')
    
    serializer = StartupListSerializer(
        bookmarked_startups, 
        many=True, 
        context={'request': request}
    )
    
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_stats(request):
    """Get comprehensive user statistics"""
    user = request.user
    
    # Get various counts
    total_ratings = user.startuprating_set.count()
    total_comments = user.startupcomment_set.count()
    total_bookmarks = user.startupbookmark_set.count()
    total_likes = user.startuplike_set.count()
    total_applications = user.jobapplication_set.count()
    
    # Get activity this month
    from django.utils import timezone
    from datetime import timedelta
    
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    monthly_activity = {
        'ratings': user.startuprating_set.filter(created_at__gte=thirty_days_ago).count(),
        'comments': user.startupcomment_set.filter(created_at__gte=thirty_days_ago).count(),
        'bookmarks': user.startupbookmark_set.filter(created_at__gte=thirty_days_ago).count(),
        'likes': user.startuplike_set.filter(created_at__gte=thirty_days_ago).count(),
    }
    
    # Calculate average rating given
    avg_rating_given = user.startuprating_set.aggregate(
        avg=models.Avg('rating')
    )['avg'] or 0
    
    return Response({
        'totals': {
            'ratings': total_ratings,
            'comments': total_comments,
            'bookmarks': total_bookmarks,
            'likes': total_likes,
            'applications': total_applications
        },
        'monthly_activity': monthly_activity,
        'average_rating_given': round(avg_rating_given, 1),
        'member_since': user.date_joined.isoformat(),
        'total_activity': total_ratings + total_comments + total_likes
    })
