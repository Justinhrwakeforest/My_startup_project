# apps/jobs/views.py - Fixed version without problematic filters
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.db.models import Q, Count
from datetime import datetime, timedelta
from django.utils import timezone
from .models import JobType, Job, JobApplication
from .serializers import JobTypeSerializer, JobListSerializer, JobDetailSerializer, JobApplicationSerializer

class JobTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = JobType.objects.all()
    serializer_class = JobTypeSerializer

class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.filter(is_active=True).select_related('startup', 'job_type')
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'skills__skill', 'location', 'startup__name']
    ordering_fields = ['posted_at', 'title', 'salary_range']
    ordering = ['-posted_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        
        # Advanced search across multiple fields
        search_query = params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(skills__skill__icontains=search_query) |
                Q(location__icontains=search_query) |
                Q(startup__name__icontains=search_query) |
                Q(startup__industry__name__icontains=search_query)
            ).distinct()
        
        # Job type filtering
        job_type = params.get('job_type')
        if job_type:
            try:
                queryset = queryset.filter(job_type__id=int(job_type))
            except (ValueError, TypeError):
                pass
        
        # Experience level filtering
        experience_level = params.get('experience_level')
        if experience_level:
            queryset = queryset.filter(experience_level=experience_level)
        
        # Location filtering
        location = params.get('location')
        if location:
            queryset = queryset.filter(location__icontains=location)
        
        # Remote work filtering
        is_remote = params.get('is_remote')
        if is_remote == 'true':
            queryset = queryset.filter(is_remote=True)
        elif is_remote == 'false':
            queryset = queryset.filter(is_remote=False)
        
        # Urgent jobs filtering
        is_urgent = params.get('is_urgent')
        if is_urgent == 'true':
            queryset = queryset.filter(is_urgent=True)
        
        # Industry filtering
        industry = params.get('industry')
        if industry:
            try:
                queryset = queryset.filter(startup__industry__id=int(industry))
            except (ValueError, TypeError):
                pass
        
        # Company size filtering
        min_employees = params.get('min_employees')
        max_employees = params.get('max_employees')
        if min_employees:
            try:
                queryset = queryset.filter(startup__employee_count__gte=int(min_employees))
            except (ValueError, TypeError):
                pass
        if max_employees:
            try:
                queryset = queryset.filter(startup__employee_count__lte=int(max_employees))
            except (ValueError, TypeError):
                pass
        
        # Posted date filtering
        posted_since = params.get('posted_since')  # days ago
        if posted_since:
            try:
                since_date = timezone.now() - timedelta(days=int(posted_since))
                queryset = queryset.filter(posted_at__gte=since_date)
            except (ValueError, TypeError):
                pass
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return JobDetailSerializer
        return JobListSerializer
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recently posted jobs"""
        recent_jobs = self.get_queryset().filter(
            posted_at__gte=timezone.now() - timedelta(days=7)
        ).order_by('-posted_at')[:10]
        
        serializer = self.get_serializer(recent_jobs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def urgent(self, request):
        """Get urgent job postings"""
        urgent_jobs = self.get_queryset().filter(is_urgent=True).order_by('-posted_at')
        serializer = self.get_serializer(urgent_jobs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def remote(self, request):
        """Get remote job opportunities"""
        remote_jobs = self.get_queryset().filter(is_remote=True).order_by('-posted_at')
        serializer = self.get_serializer(remote_jobs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def filters(self, request):
        """Get available filter options for jobs"""
        from apps.startups.models import Industry
        
        # Get all job types with job counts
        job_types = JobType.objects.annotate(
            job_count=Count('job', filter=Q(job__is_active=True))
        ).filter(job_count__gt=0).order_by('name')
        
        # Get experience levels
        experience_levels = [
            {'value': 'entry', 'label': 'Entry Level', 'count': Job.objects.filter(experience_level='entry', is_active=True).count()},
            {'value': 'mid', 'label': 'Mid Level', 'count': Job.objects.filter(experience_level='mid', is_active=True).count()},
            {'value': 'senior', 'label': 'Senior Level', 'count': Job.objects.filter(experience_level='senior', is_active=True).count()},
            {'value': 'lead', 'label': 'Lead/Principal', 'count': Job.objects.filter(experience_level='lead', is_active=True).count()},
        ]
        
        # Get industries (from startups that have jobs)
        industries = Industry.objects.annotate(
            job_count=Count('startups__jobs', filter=Q(startups__jobs__is_active=True))
        ).filter(job_count__gt=0).order_by('name')
        
        # Get popular skills
        from django.db.models import Count as CountAgg
        try:
            popular_skills_qs = Job.objects.filter(is_active=True).values(
                'skills__skill'
            ).annotate(
                count=CountAgg('skills__skill')
            ).order_by('-count')[:20]
            
            popular_skills = [item['skills__skill'] for item in popular_skills_qs if item['skills__skill']]
        except:
            popular_skills = []
        
        # Get locations
        locations = Job.objects.filter(is_active=True).values_list('location', flat=True).distinct().order_by('location')
        
        return Response({
            'job_types': JobTypeSerializer(job_types, many=True).data,
            'experience_levels': [level for level in experience_levels if level['count'] > 0],
            'industries': [{'id': ind.id, 'name': ind.name, 'job_count': ind.job_count} for ind in industries],
            'popular_skills': popular_skills,
            'locations': [loc for loc in locations if loc],
            'posted_since_options': [
                {'value': 1, 'label': 'Last 24 hours'},
                {'value': 3, 'label': 'Last 3 days'},
                {'value': 7, 'label': 'Last week'},
                {'value': 30, 'label': 'Last month'},
            ]
        })
    
    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        """Get personalized job recommendations"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user = request.user
        
        # Get user's interests and application history
        try:
            user_interests = user.interests.values_list('interest', flat=True)
            applied_jobs = user.jobapplication_set.values_list('job__id', flat=True)
        except:
            user_interests = []
            applied_jobs = []
        
        # Get user's liked/bookmarked startups
        try:
            liked_startups = user.startuplike_set.values_list('startup__id', flat=True)
            bookmarked_startups = user.startupbookmark_set.values_list('startup__id', flat=True)
        except:
            liked_startups = []
            bookmarked_startups = []
        
        # Recommend jobs based on interests, liked startups, and similar companies
        recommended = self.get_queryset().filter(
            Q(skills__skill__in=user_interests) |
            Q(startup__id__in=liked_startups) |
            Q(startup__id__in=bookmarked_startups) |
            Q(startup__tags__tag__in=user_interests)
        ).exclude(
            id__in=applied_jobs
        ).distinct().order_by('-posted_at')[:10]
        
        serializer = self.get_serializer(recommended, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticatedOrReadOnly])
    def apply(self, request, pk=None):
        """Apply to a job"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        job = self.get_object()
        cover_letter = request.data.get('cover_letter', '')
        
        # Check if already applied
        if JobApplication.objects.filter(job=job, user=request.user).exists():
            return Response({'error': 'You have already applied to this job'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        application = JobApplication.objects.create(
            job=job, user=request.user, cover_letter=cover_letter
        )
        
        serializer = JobApplicationSerializer(application)
        return Response({
            'message': 'Application submitted successfully',
            'application': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticatedOrReadOnly])
    def my_applications(self, request):
        """Get user's job applications"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            applications = JobApplication.objects.filter(user=request.user).select_related('job', 'job__startup').order_by('-applied_at')
            serializer = JobApplicationSerializer(applications, many=True)
            return Response(serializer.data)
        except:
            return Response([])  # Return empty list if model doesn't exist
