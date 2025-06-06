# apps/startups/views.py - Enhanced views with detail page actions

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg, Count, Case, When, IntegerField, Min, Max
from django.db import models
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.paginator import Paginator
from .models import Industry, Startup, StartupRating, StartupComment, StartupBookmark, StartupLike
from .serializers import (
    IndustrySerializer, StartupListSerializer, StartupDetailSerializer,
    StartupRatingDetailSerializer, StartupCommentDetailSerializer
)

class StartupViewSet(viewsets.ModelViewSet):
    queryset = Startup.objects.all().select_related('industry').prefetch_related(
        'founders', 'tags', 'ratings', 'comments', 'likes', 'bookmarks'
    )
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['industry', 'is_featured', 'founded_year', 'location']
    search_fields = ['name', 'description', 'tags__tag', 'location', 'founders__name']
    ordering_fields = ['name', 'founded_year', 'created_at', 'views', 'employee_count', 'average_rating']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return StartupDetailSerializer
        return StartupListSerializer
    
    def retrieve(self, request, *args, **kwargs):
        """Enhanced retrieve method with view tracking and optimized queries"""
        instance = self.get_object()
        
        # Increment views (you might want to implement IP-based or user-based view tracking)
        instance.views += 1
        instance.save(update_fields=['views'])
        
        # Use optimized queryset for detail view
        optimized_instance = Startup.objects.select_related('industry').prefetch_related(
            'founders',
            'tags',
            'ratings__user',
            'comments__user',
            'likes__user',
            'bookmarks__user',
            'jobs__job_type',
            'jobs__skills'
        ).get(pk=instance.pk)
        
        serializer = self.get_serializer(optimized_instance)
        return Response(serializer.data)
    
    # ... (keep existing methods like get_queryset, featured, trending, recommendations, filters)
    
    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        """Get detailed metrics for a startup"""
        startup = self.get_object()
        
        # Calculate various metrics
        total_views = startup.views
        total_ratings = startup.ratings.count()
        total_comments = startup.comments.count()
        total_likes = startup.likes.count()
        total_bookmarks = startup.bookmarks.count()
        
        # Recent activity (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_activity = {
            'ratings': startup.ratings.filter(created_at__gte=thirty_days_ago).count(),
            'comments': startup.comments.filter(created_at__gte=thirty_days_ago).count(),
            'likes': startup.likes.filter(created_at__gte=thirty_days_ago).count(),
            'bookmarks': startup.bookmarks.filter(created_at__gte=thirty_days_ago).count(),
        }
        
        # Rating distribution
        rating_distribution = {}
        for i in range(1, 6):
            rating_distribution[f'{i}_star'] = startup.ratings.filter(rating=i).count()
        
        return Response({
            'total_views': total_views,
            'total_ratings': total_ratings,
            'total_comments': total_comments,
            'total_likes': total_likes,
            'total_bookmarks': total_bookmarks,
            'average_rating': startup.average_rating,
            'recent_activity': recent_activity,
            'rating_distribution': rating_distribution,
        })
    
    @action(detail=True, methods=['get'])
    def ratings(self, request, pk=None):
        """Get paginated ratings for a startup"""
        startup = self.get_object()
        ratings = startup.ratings.select_related('user').order_by('-created_at')
        
        # Pagination
        page = request.query_params.get('page', 1)
        paginator = Paginator(ratings, 10)  # 10 ratings per page
        ratings_page = paginator.get_page(page)
        
        serializer = StartupRatingDetailSerializer(ratings_page, many=True)
        
        return Response({
            'results': serializer.data,
            'count': paginator.count,
            'has_next': ratings_page.has_next(),
            'has_previous': ratings_page.has_previous(),
            'current_page': int(page),
            'total_pages': paginator.num_pages
        })
    
    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        """Get paginated comments for a startup"""
        startup = self.get_object()
        comments = startup.comments.select_related('user').order_by('-created_at')
        
        # Pagination
        page = request.query_params.get('page', 1)
        paginator = Paginator(comments, 10)  # 10 comments per page
        comments_page = paginator.get_page(page)
        
        serializer = StartupCommentDetailSerializer(comments_page, many=True)
        
        return Response({
            'results': serializer.data,
            'count': paginator.count,
            'has_next': comments_page.has_next(),
            'has_previous': comments_page.has_previous(),
            'current_page': int(page),
            'total_pages': paginator.num_pages
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticatedOrReadOnly])
    def rate(self, request, pk=None):
        """Rate a startup (1-5 stars)"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        startup = self.get_object()
        rating_value = request.data.get('rating')
        
        try:
            rating_value = int(rating_value)
            if not (1 <= rating_value <= 5):
                return Response({'error': 'Rating must be between 1 and 5'}, 
                              status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid rating value'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        rating, created = StartupRating.objects.update_or_create(
            startup=startup, user=request.user,
            defaults={'rating': rating_value}
        )
        
        action_text = 'created' if created else 'updated'
        
        # Return updated startup metrics
        startup.refresh_from_db()
        
        return Response({
            'message': f'Rating {action_text} successfully',
            'rating': rating_value,
            'average_rating': startup.average_rating,
            'total_ratings': startup.total_ratings,
            'user_rating': rating_value
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticatedOrReadOnly])
    def comment(self, request, pk=None):
        """Add a comment to a startup"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        startup = self.get_object()
        text = request.data.get('text', '').strip()
        
        if not text:
            return Response({'error': 'Comment text is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        if len(text) > 1000:
            return Response({'error': 'Comment too long (max 1000 characters)'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        comment = StartupComment.objects.create(
            startup=startup, user=request.user, text=text
        )
        
        serializer = StartupCommentDetailSerializer(comment)
        return Response({
            'message': 'Comment added successfully',
            'comment': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticatedOrReadOnly])
    def bookmark(self, request, pk=None):
        """Bookmark/unbookmark a startup"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        startup = self.get_object()
        bookmark, created = StartupBookmark.objects.get_or_create(
            startup=startup, user=request.user
        )
        
        if not created:
            bookmark.delete()
            return Response({
                'bookmarked': False, 
                'message': 'Bookmark removed',
                'total_bookmarks': startup.bookmarks.count()
            })
        
        return Response({
            'bookmarked': True, 
            'message': 'Startup bookmarked',
            'total_bookmarks': startup.bookmarks.count()
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticatedOrReadOnly])
    def like(self, request, pk=None):
        """Like/unlike a startup"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        startup = self.get_object()
        like, created = StartupLike.objects.get_or_create(
            startup=startup, user=request.user
        )
        
        if not created:
            like.delete()
            return Response({
                'liked': False, 
                'message': 'Like removed',
                'total_likes': startup.likes.count()
            })
        
        return Response({
            'liked': True, 
            'message': 'Startup liked',
            'total_likes': startup.likes.count()
        })
    
    @action(detail=True, methods=['delete'])
    def delete_comment(self, request, pk=None):
        """Delete a comment (only by comment author)"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        startup = self.get_object()
        comment_id = request.data.get('comment_id')
        
        if not comment_id:
            return Response({'error': 'Comment ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            comment = StartupComment.objects.get(
                id=comment_id, 
                startup=startup, 
                user=request.user
            )
            comment.delete()
            return Response({'message': 'Comment deleted successfully'})
        except StartupComment.DoesNotExist:
            return Response({'error': 'Comment not found or unauthorized'}, 
                          status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def jobs(self, request, pk=None):
        """Get all jobs for this startup"""
        startup = self.get_object()
        from apps.jobs.serializers import JobListSerializer
        
        jobs = startup.jobs.filter(is_active=True).select_related('job_type').prefetch_related('skills')
        
        # Optional filtering
        job_type = request.query_params.get('job_type')
        experience_level = request.query_params.get('experience_level')
        is_remote = request.query_params.get('is_remote')
        
        if job_type:
            jobs = jobs.filter(job_type__id=job_type)
        if experience_level:
            jobs = jobs.filter(experience_level=experience_level)
        if is_remote == 'true':
            jobs = jobs.filter(is_remote=True)
        
        jobs = jobs.order_by('-posted_at')
        
        # Pagination
        page = request.query_params.get('page', 1)
        paginator = Paginator(jobs, 10)
        jobs_page = paginator.get_page(page)
        
        serializer = JobListSerializer(jobs_page, many=True, context={'request': request})
        
        return Response({
            'results': serializer.data,
            'count': paginator.count,
            'has_next': jobs_page.has_next(),
            'has_previous': jobs_page.has_previous(),
            'current_page': int(page),
            'total_pages': paginator.num_pages
        })
