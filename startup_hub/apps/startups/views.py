from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg, Count, Case, When, IntegerField, Min, Max
from django.db import models
from datetime import datetime, timedelta
from django.utils import timezone
from .models import Industry, Startup, StartupRating, StartupComment, StartupBookmark, StartupLike
from .serializers import (
    IndustrySerializer, StartupListSerializer, StartupDetailSerializer,
    StartupRatingSerializer, StartupCommentSerializer
)

class IndustryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Industry.objects.all()
    serializer_class = IndustrySerializer

class StartupViewSet(viewsets.ModelViewSet):
    queryset = Startup.objects.all().prefetch_related('founders', 'tags', 'ratings', 'comments')
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['industry', 'is_featured', 'founded_year', 'location']
    search_fields = ['name', 'description', 'tags__tag', 'location', 'founders__name']
    ordering_fields = ['name', 'founded_year', 'created_at', 'views', 'employee_count', 'average_rating']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Advanced filtering parameters
        params = self.request.query_params
        
        # Search across multiple fields with OR logic
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
        if self.action == 'retrieve':
            return StartupDetailSerializer
        return StartupListSerializer
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Increment views
        instance.views += 1
        instance.save(update_fields=['views'])
        return super().retrieve(request, *args, **kwargs)
    
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
    def recommendations(self, request):
        """Get personalized startup recommendations"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user = request.user
        
        # Get user's interests
        user_interests = user.interests.values_list('interest', flat=True)
        
        # Get user's liked/rated startups' industries
        liked_industries = Industry.objects.filter(
            startups__in=user.startuplike_set.values_list('startup', flat=True)
        ).distinct()
        
        # Recommend startups in similar industries or matching interests
        recommended = self.get_queryset().filter(
            Q(industry__in=liked_industries) | 
            Q(tags__tag__in=user_interests)
        ).exclude(
            id__in=user.startuplike_set.values_list('startup', flat=True)
        ).annotate(
            avg_rating=Avg('ratings__rating')
        ).order_by('-avg_rating', '-views').distinct()[:10]
        
        serializer = self.get_serializer(recommended, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def filters(self, request):
        """Get available filter options"""
        # Get all industries with startup counts
        industries = Industry.objects.annotate(
            startup_count=Count('startups')
        ).filter(startup_count__gt=0).order_by('name')
        
        # Get location options
        locations = Startup.objects.values_list('location', flat=True).distinct().order_by('location')
        
        # Get popular tags (fixed - removed duplicate import)
        popular_tags = Startup.objects.values_list('tags__tag', flat=True).annotate(
            count=Count('tags__tag')
        ).order_by('-count')[:20]
        
        # Get employee count ranges
        employee_ranges = [
            {'label': '1-10', 'min': 1, 'max': 10},
            {'label': '11-50', 'min': 11, 'max': 50},
            {'label': '51-200', 'min': 51, 'max': 200},
            {'label': '201-500', 'min': 201, 'max': 500},
            {'label': '500+', 'min': 500, 'max': None},
        ]
        
        return Response({
            'industries': IndustrySerializer(industries, many=True).data,
            'locations': [loc for loc in locations if loc],
            'popular_tags': [tag for tag in popular_tags if tag],
            'employee_ranges': employee_ranges,
            'founded_year_range': {
                'min': Startup.objects.aggregate(min_year=Min('founded_year'))['min_year'],
                'max': Startup.objects.aggregate(max_year=Max('founded_year'))['max_year']
            }
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
        return Response({
            'message': f'Rating {action_text} successfully',
            'rating': rating_value,
            'average_rating': startup.average_rating
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
        
        comment = StartupComment.objects.create(
            startup=startup, user=request.user, text=text
        )
        
        serializer = StartupCommentSerializer(comment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
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
            return Response({'bookmarked': False, 'message': 'Bookmark removed'})
        
        return Response({'bookmarked': True, 'message': 'Startup bookmarked'})
    
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
            return Response({'liked': False, 'message': 'Like removed'})
        
        return Response({'liked': True, 'message': 'Startup liked'})