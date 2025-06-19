# apps/startups/views.py - Windows compatible version without emoji

import logging
from django.conf import settings
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

# Setup logging
logger = logging.getLogger(__name__)

class IndustryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for managing industries"""
    queryset = Industry.objects.all()
    serializer_class = IndustrySerializer
    
    def list(self, request, *args, **kwargs):
        logger.info(f"Industries list requested by user: {request.user}")
        return super().list(request, *args, **kwargs)

class StartupViewSet(viewsets.ModelViewSet):
    """ViewSet for managing startups with full CRUD operations"""
    
    # Base queryset - only approved startups for public viewing
    queryset = Startup.objects.filter(is_approved=True).select_related('industry').prefetch_related(
        'founders', 'tags', 'ratings', 'comments', 'likes', 'bookmarks'
    )
    
    # Permissions
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    # Filtering and search
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['industry', 'is_featured', 'founded_year', 'location']
    search_fields = ['name', 'description', 'tags__tag', 'location', 'founders__name']
    ordering_fields = ['name', 'founded_year', 'created_at', 'views', 'employee_count', 'average_rating']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get queryset based on action and filters"""
        # For admin actions, show all startups
        if self.action in ['admin_list', 'admin_action', 'bulk_admin']:
            queryset = Startup.objects.all()
        # For list/retrieve actions, only show approved startups
        elif self.action in ['list', 'retrieve']:
            queryset = Startup.objects.filter(is_approved=True)
        else:
            # For create/update/delete, show all startups (with proper permissions)
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
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return StartupCreateSerializer
        elif self.action == 'retrieve':
            return StartupDetailSerializer
        return StartupListSerializer
    
    def get_permissions(self):
        """Return appropriate permissions based on action"""
        if self.action == 'create':
            # Require authentication for creating startups
            permission_classes = [IsAuthenticated]
        elif self.action in ['admin_list', 'admin_action', 'bulk_admin']:
            # Require authentication for admin actions
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticatedOrReadOnly]
        
        return [permission() for permission in permission_classes]
    
    def create(self, request, *args, **kwargs):
        """Create a new startup submission"""
        logger.info(f"Creating new startup by user: {request.user}")
        
        # Check if user is authenticated
        if not request.user.is_authenticated:
            logger.warning(f"Unauthenticated user attempted to create startup")
            return Response({'error': 'Authentication required'}, 
                           status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            # Log the incoming data (without sensitive info)
            logger.info(f"Received data keys: {list(request.data.keys())}")
            
            # Validate data using serializer
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                logger.warning(f"Validation errors: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            # Save the startup with the current user as submitter
            # Note: is_approved=False by default (set in serializer)
            startup = serializer.save(submitted_by=request.user, is_approved=False)
            
            # Return the created startup using the detail serializer
            response_serializer = StartupDetailSerializer(startup, context={'request': request})
            
            logger.info(f"Startup created successfully: {startup.name} (ID: {startup.id})")
            
            return Response({
                'message': 'Startup submitted successfully! It will be reviewed before being published.',
                'startup': response_serializer.data,
                'id': startup.id,
                'success': True
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating startup: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response({
                'error': 'Failed to create startup. Please try again.',
                'detail': str(e) if settings.DEBUG else 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def retrieve(self, request, *args, **kwargs):
        """Enhanced retrieve method with view tracking"""
        logger.info(f"Retrieving startup {kwargs.get('pk')} for user: {request.user}")
        
        try:
            instance = self.get_object()
            
            # Increment views (basic implementation - could be improved with IP tracking)
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
            logger.info(f"Startup retrieved successfully: {instance.name}")
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error retrieving startup: {str(e)}")
            return Response({'error': 'Startup not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # ==================== CUSTOM LIST ACTIONS ====================
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured startups"""
        logger.info(f"Featured startups requested by user: {request.user}")
        featured_startups = self.get_queryset().filter(is_featured=True)
        
        page = self.paginate_queryset(featured_startups)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(featured_startups, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def trending(self, request):
        """Get trending startups based on recent activity"""
        logger.info(f"Trending startups requested by user: {request.user}")
        
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
        logger.info(f"Filter options requested by user: {request.user}")
        
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
    
    # ==================== INTERACTION ACTIONS ====================
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def rate(self, request, pk=None):
        """Rate a startup (1-5 stars)"""
        logger.info(f"Rating startup {pk} by user: {request.user}")
        
        startup = self.get_object()
        rating_value = request.data.get('rating')
        
        # Validate rating
        try:
            rating_value = int(rating_value)
            if not (1 <= rating_value <= 5):
                logger.warning(f"Invalid rating value: {rating_value}")
                return Response({'error': 'Rating must be between 1 and 5'}, 
                              status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            logger.warning(f"Invalid rating format: {rating_value}")
            return Response({'error': 'Invalid rating value'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            rating, created = StartupRating.objects.update_or_create(
                startup=startup, user=request.user,
                defaults={'rating': rating_value}
            )
            
            action_text = 'created' if created else 'updated'
            
            # Return updated startup metrics
            startup.refresh_from_db()
            
            logger.info(f"Rating {action_text} successfully: {rating_value}/5 for {startup.name}")
            
            return Response({
                'message': f'Rating {action_text} successfully',
                'rating': rating_value,
                'average_rating': startup.average_rating,
                'total_ratings': startup.total_ratings,
                'user_rating': rating_value
            })
            
        except Exception as e:
            logger.error(f"Error saving rating: {str(e)}")
            return Response({'error': 'Failed to save rating'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def comment(self, request, pk=None):
        """Add a comment to a startup"""
        logger.info(f"Adding comment to startup {pk} by user: {request.user}")
        
        startup = self.get_object()
        text = request.data.get('text', '').strip()
        
        if not text:
            logger.warning(f"Empty comment attempted by user: {request.user}")
            return Response({'error': 'Comment text is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        if len(text) > 1000:
            logger.warning(f"Comment too long: {len(text)} characters")
            return Response({'error': 'Comment too long (max 1000 characters)'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            comment = StartupComment.objects.create(
                startup=startup, user=request.user, text=text
            )
            
            serializer = StartupCommentDetailSerializer(comment)
            logger.info(f"Comment added successfully to {startup.name}")
            
            return Response({
                'message': 'Comment added successfully',
                'comment': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error saving comment: {str(e)}")
            return Response({'error': 'Failed to save comment'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def bookmark(self, request, pk=None):
        """Bookmark/unbookmark a startup"""
        logger.info(f"Toggling bookmark for startup {pk} by user: {request.user}")
        
        startup = self.get_object()
        
        try:
            bookmark = StartupBookmark.objects.get(startup=startup, user=request.user)
            # Bookmark exists, so remove it
            bookmark.delete()
            bookmarked = False
            message = 'Bookmark removed successfully'
            logger.info(f"Bookmark removed for {startup.name} by {request.user}")
        except StartupBookmark.DoesNotExist:
            # Bookmark doesn't exist, so create it
            StartupBookmark.objects.create(startup=startup, user=request.user)
            bookmarked = True
            message = 'Startup bookmarked successfully'
            logger.info(f"Bookmark added for {startup.name} by {request.user}")
        except Exception as e:
            logger.error(f"Error toggling bookmark: {str(e)}")
            return Response({'error': 'Failed to update bookmark'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Get updated bookmark count
        total_bookmarks = startup.bookmarks.count()
        
        return Response({
            'bookmarked': bookmarked,
            'message': message,
            'total_bookmarks': total_bookmarks,
            'startup_id': startup.id,
            'success': True
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        """Like/unlike a startup"""
        logger.info(f"Toggling like for startup {pk} by user: {request.user}")
        
        startup = self.get_object()
        
        try:
            like = StartupLike.objects.get(startup=startup, user=request.user)
            # Like exists, so remove it
            like.delete()
            liked = False
            message = 'Like removed successfully'
            logger.info(f"Like removed for {startup.name} by {request.user}")
        except StartupLike.DoesNotExist:
            # Like doesn't exist, so create it
            StartupLike.objects.create(startup=startup, user=request.user)
            liked = True
            message = 'Startup liked successfully'
            logger.info(f"Like added for {startup.name} by {request.user}")
        except Exception as e:
            logger.error(f"Error toggling like: {str(e)}")
            return Response({'error': 'Failed to update like'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Get updated like count
        total_likes = startup.likes.count()
        
        return Response({
            'liked': liked,
            'message': message,
            'total_likes': total_likes,
            'startup_id': startup.id
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def bookmarked(self, request):
        """Get user's bookmarked startups"""
        logger.info(f"Getting bookmarked startups for user: {request.user}")
        
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
    
    # ==================== ADMIN FUNCTIONALITY ====================
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def admin_list(self, request):
        """Get all startups for admin panel (including unapproved ones)"""
        if not (request.user.is_staff or request.user.is_superuser):
            logger.warning(f"Non-admin user {request.user} attempted to access admin panel")
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        logger.info(f"Admin panel accessed by: {request.user}")
        
        filter_type = request.query_params.get('filter', 'all')
        search = request.query_params.get('search', '')
        
        # Get all startups without approval filter for admin
        queryset = Startup.objects.all().select_related('industry', 'submitted_by').prefetch_related(
            'founders', 'tags'
        )
        
        # Apply filters
        if filter_type == 'pending':
            queryset = queryset.filter(is_approved=False)
        elif filter_type == 'approved':
            queryset = queryset.filter(is_approved=True, is_featured=False)
        elif filter_type == 'featured':
            queryset = queryset.filter(is_featured=True)
        # 'all' - no additional filter
        
        # Apply search
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        
        # Order by most recent first
        queryset = queryset.order_by('-created_at')
        
        logger.info(f"Admin panel returning {queryset.count()} startups (filter: {filter_type})")
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = StartupDetailSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = StartupDetailSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def admin_action(self, request, pk=None):
        """Admin actions: approve, reject, feature, unfeature"""
        if not (request.user.is_staff or request.user.is_superuser):
            logger.warning(f"Non-admin user {request.user} attempted admin action")
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        startup = self.get_object()
        action_type = request.data.get('action')
        
        logger.info(f"Admin action '{action_type}' on startup {startup.name} by {request.user}")
        
        try:
            if action_type == 'approve':
                startup.is_approved = True
                startup.save(update_fields=['is_approved'])
                return Response({'message': 'Startup approved successfully'})
            
            elif action_type == 'reject':
                startup.is_approved = False
                startup.is_featured = False  # Remove featured status if rejecting
                startup.save(update_fields=['is_approved', 'is_featured'])
                return Response({'message': 'Startup rejected successfully'})
            
            elif action_type == 'feature':
                startup.is_approved = True  # Auto-approve when featuring
                startup.is_featured = True
                startup.save(update_fields=['is_approved', 'is_featured'])
                return Response({'message': 'Startup featured successfully'})
            
            elif action_type == 'unfeature':
                startup.is_featured = False
                startup.save(update_fields=['is_featured'])
                return Response({'message': 'Startup unfeatured successfully'})
            
            else:
                logger.warning(f"Invalid admin action: {action_type}")
                return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error performing admin action: {str(e)}")
            return Response({'error': 'Failed to perform action'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def bulk_admin(self, request):
        """Bulk admin actions"""
        if not (request.user.is_staff or request.user.is_superuser):
            logger.warning(f"Non-admin user {request.user} attempted bulk admin action")
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        startup_ids = request.data.get('startup_ids', [])
        action_type = request.data.get('action')
        
        logger.info(f"Bulk admin action '{action_type}' on {len(startup_ids)} startups by {request.user}")
        
        if not startup_ids:
            return Response({'error': 'No startups selected'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            startups = Startup.objects.filter(id__in=startup_ids)
            
            if action_type == 'approve':
                updated_count = startups.update(is_approved=True)
                return Response({'message': f'{updated_count} startups approved successfully'})
            
            elif action_type == 'reject':
                updated_count = startups.update(is_approved=False, is_featured=False)
                return Response({'message': f'{updated_count} startups rejected successfully'})
            
            elif action_type == 'feature':
                updated_count = startups.update(is_approved=True, is_featured=True)
                return Response({'message': f'{updated_count} startups featured successfully'})
            
            else:
                logger.warning(f"Invalid bulk admin action: {action_type}")
                return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error performing bulk admin action: {str(e)}")
            return Response({'error': 'Failed to perform bulk action'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # ==================== HELPER METHODS ====================
    
    def perform_create(self, serializer):
        """Called when creating a new startup instance"""
        # This is called by the DRF create method
        # We set submitted_by to current user and is_approved to False
        serializer.save(submitted_by=self.request.user, is_approved=False)
    
    def perform_update(self, serializer):
        """Called when updating a startup instance"""
        # Only allow the submitter or admin to update
        startup = self.get_object()
        if not (self.request.user == startup.submitted_by or 
                self.request.user.is_staff or 
                self.request.user.is_superuser):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to edit this startup")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """Called when deleting a startup instance"""
        # Only allow the submitter or admin to delete
        if not (self.request.user == instance.submitted_by or 
                self.request.user.is_staff or 
                self.request.user.is_superuser):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to delete this startup")
        
        logger.info(f"Deleting startup {instance.name} by {self.request.user}")
        instance.delete()
