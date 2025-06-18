# apps/startups/views.py - Fixed version with startup creation support

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg, Count, Case, When, IntegerField, Min, Max
from django.db import models
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.paginator import Paginator
from .models import Industry, Startup, StartupRating, StartupComment, StartupBookmark, StartupLike
from .serializers import (
    IndustrySerializer, StartupListSerializer, StartupDetailSerializer,
    StartupRatingDetailSerializer, StartupCommentDetailSerializer, StartupCreateSerializer
)

class IndustryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Industry.objects.all()
    serializer_class = IndustrySerializer

class StartupViewSet(viewsets.ModelViewSet):
    queryset = Startup.objects.filter(is_approved=True).select_related('industry').prefetch_related(
        'founders', 'tags', 'ratings', 'comments', 'likes', 'bookmarks'
    )
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['industry', 'is_featured', 'founded_year', 'location']
    search_fields = ['name', 'description', 'tags__tag', 'location', 'founders__name']
    ordering_fields = ['name', 'founded_year', 'created_at', 'views', 'employee_count', 'average_rating']
    ordering = ['-created_at']
    
    def get_queryset(self):
        # For list/retrieve actions, only show approved startups
        if self.action in ['list', 'retrieve']:
            queryset = Startup.objects.filter(is_approved=True)
        else:
            # For create/update/delete, show all startups
            queryset = Startup.objects.all()
            
        queryset = queryset.select_related('industry').prefetch_related(
            'founders', 'tags', 'ratings', 'comments', 'likes', 'bookmarks'
        )
        
        params = self.request.query_params
        
        # Check if we want only bookmarked startups
        bookmarked_only = params.get('bookmarked')
        if bookmarked_only == 'true' and self.request.user.is_authenticated:
            bookmarked_ids = self.request.user.startupbookmark_set.values_list('startup_id', flat=True)
            queryset = queryset.filter(id__in=bookmarked_ids)
        
        # Advanced search across multiple fields
        search_query = params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(tags__tag__icontains=search_query) |
                Q(location__icontains=search_query) |
                Q(founders__name__icontains=search_query) |
                Q(industry__name__icontains=search_query)
            ).distinct()
        
        # Industry filtering (multiple industries)
        industries = params.getlist('industry')
        if industries:
            queryset = queryset.filter(industry__id__in=industries)
        
        # Location filtering
        location = params.get('location')
        if location:
            queryset = queryset.filter(location__icontains=location)
        
        # Company size filtering
        min_employees = params.get('min_employees')
        max_employees = params.get('max_employees')
        if min_employees:
            queryset = queryset.filter(employee_count__gte=int(min_employees))
        if max_employees:
            queryset = queryset.filter(employee_count__lte=int(max_employees))
        
        # Founded year range
        min_year = params.get('min_founded_year')
        max_year = params.get('max_founded_year')
        if min_year:
            queryset = queryset.filter(founded_year__gte=int(min_year))
        if max_year:
            queryset = queryset.filter(founded_year__lte=int(max_year))
        
        # Filter by minimum rating
        min_rating = params.get('min_rating')
        if min_rating:
            queryset = queryset.annotate(
                avg_rating=Avg('ratings__rating')
            ).filter(avg_rating__gte=float(min_rating))
        
        # Filter by funding status
        has_funding = params.get('has_funding')
        if has_funding == 'true':
            queryset = queryset.exclude(Q(funding_amount='') | Q(funding_amount__isnull=True))
        elif has_funding == 'false':
            queryset = queryset.filter(Q(funding_amount='') | Q(funding_amount__isnull=True))
        
        # Filter by tags
        tags = params.getlist('tags')
        if tags:
            queryset = queryset.filter(tags__tag__in=tags).distinct()
        
        # Featured filter
        featured_only = params.get('featured')
        if featured_only == 'true':
            queryset = queryset.filter(is_featured=True)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return StartupCreateSerializer
        elif self.action == 'retrieve':
            return StartupDetailSerializer
        return StartupListSerializer
    
    def get_permissions(self):
        """
        Instantiate and return the list of permissions that this view requires.
        """
        if self.action == 'create':
            # Require authentication for creating startups
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticatedOrReadOnly]
        
        return [permission() for permission in permission_classes]
    
    def create(self, request, *args, **kwargs):
        """Create a new startup submission"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Set the submitted_by field to the current user
        startup = serializer.save(submitted_by=request.user, is_approved=False)
        
        # Return the created startup using the detail serializer
        response_serializer = StartupDetailSerializer(startup, context={'request': request})
        
        return Response({
            'message': 'Startup submitted successfully! It will be reviewed before being published.',
            'startup': response_serializer.data,
            'id': startup.id
        }, status=status.HTTP_201_CREATED)
    
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
            'bookmarks__user'
        ).get(pk=instance.pk)
        
        serializer = self.get_serializer(optimized_instance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured startups"""
        featured_startups = self.get_queryset().filter(is_featured=True)
        serializer = self.get_serializer(featured_startups, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def trending(self, request):
        """Get trending startups based on recent activity"""
        # Get startups with recent activity (views, ratings, comments, likes)
        trending_startups = self.get_queryset().annotate(
            recent_activity=Count('ratings', filter=Q(ratings__created_at__gte=timezone.now() - timedelta(days=7))) +
                          Count('comments', filter=Q(comments__created_at__gte=timezone.now() - timedelta(days=7))) +
                          Count('likes', filter=Q(likes__created_at__gte=timezone.now() - timedelta(days=7)))
        ).order_by('-recent_activity', '-views')[:10]
        
        serializer = self.get_serializer(trending_startups, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def filters(self, request):
        """Get available filter options"""
        # Get all industries with startup counts (only for approved startups)
        industries = Industry.objects.annotate(
            startup_count=Count('startups', filter=Q(startups__is_approved=True))
        ).filter(startup_count__gt=0).order_by('name')
        
        # Get location options (only from approved startups)
        locations = Startup.objects.filter(is_approved=True).values_list('location', flat=True).distinct().order_by('location')
        
        # Get popular tags (only from approved startups)
        from django.db.models import Count as DBCount
        popular_tags = Startup.objects.filter(is_approved=True).values_list('tags__tag', flat=True).annotate(
            count=DBCount('tags__tag')
        ).order_by('-count')[:20]
        
        # Get employee count ranges
        employee_ranges = [
            {'label': '1-10', 'min': 1, 'max': 10},
            {'label': '11-50', 'min': 11, 'max': 50},
            {'label': '51-200', 'min': 51, 'max': 200},
            {'label': '201-500', 'min': 201, 'max': 500},
            {'label': '500+', 'min': 500, 'max': None},
        ]
        
        # Get founded year range (only from approved startups)
        year_range = Startup.objects.filter(is_approved=True).aggregate(
            min_year=Min('founded_year'),
            max_year=Max('founded_year')
        )
        
        return Response({
            'industries': IndustrySerializer(industries, many=True).data,
            'locations': [loc for loc in locations if loc],
            'popular_tags': [tag for tag in popular_tags if tag],
            'employee_ranges': employee_ranges,
            'founded_year_range': year_range
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
        
        try:
            bookmark = StartupBookmark.objects.get(startup=startup, user=request.user)
            # Bookmark exists, so remove it
            bookmark.delete()
            bookmarked = False
            message = 'Bookmark removed'
        except StartupBookmark.DoesNotExist:
            # Bookmark doesn't exist, so create it
            StartupBookmark.objects.create(startup=startup, user=request.user)
            bookmarked = True
            message = 'Startup bookmarked'
        
        # Get updated bookmark count
        total_bookmarks = startup.bookmarks.count()
        
        return Response({
            'bookmarked': bookmarked,
            'message': message,
            'total_bookmarks': total_bookmarks,
            'startup_id': startup.id,
            'success': True  # Add this for consistency
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticatedOrReadOnly])
    def like(self, request, pk=None):
        """Like/unlike a startup"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        startup = self.get_object()
        
        try:
            like = StartupLike.objects.get(startup=startup, user=request.user)
            # Like exists, so remove it
            like.delete()
            liked = False
            message = 'Like removed'
        except StartupLike.DoesNotExist:
            # Like doesn't exist, so create it
            StartupLike.objects.create(startup=startup, user=request.user)
            liked = True
            message = 'Startup liked'
        
        # Get updated like count
        total_likes = startup.likes.count()
        
        return Response({
            'liked': liked,
            'message': message,
            'total_likes': total_likes,
            'startup_id': startup.id
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticatedOrReadOnly])
    def bookmarked(self, request):
        """Get user's bookmarked startups"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Get bookmarked startup IDs
        bookmarked_ids = request.user.startupbookmark_set.values_list('startup_id', flat=True)
        
        # Get the actual startup objects (only approved ones)
        bookmarked_startups = self.get_queryset().filter(id__in=bookmarked_ids).order_by('-bookmarks__created_at')
        
        # Apply pagination
        page = self.paginate_queryset(bookmarked_startups)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(bookmarked_startups, many=True)
        return Response(serializer.data)
