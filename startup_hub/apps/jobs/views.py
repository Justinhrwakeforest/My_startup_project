# startup_hub/apps/jobs/views.py - Updated with job upload, edit, and admin approval

import logging
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django.db.models import Q, Count
from datetime import datetime, timedelta
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import JobType, Job, JobApplication, JobEditRequest
from .serializers import (
    JobTypeSerializer, JobListSerializer, JobDetailSerializer, 
    JobApplicationSerializer, JobCreateSerializer, JobEditSerializer,
    JobEditRequestSerializer, MyJobsSerializer
)

logger = logging.getLogger(__name__)

class JobTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = JobType.objects.all()
    serializer_class = JobTypeSerializer

class JobViewSet(viewsets.ModelViewSet):
    # Only show active, approved jobs by default
    queryset = Job.objects.filter(is_active=True, status='active').select_related('startup', 'job_type')
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'skills__skill', 'location', 'startup__name']
    ordering_fields = ['posted_at', 'title', 'salary_range', 'view_count']
    ordering = ['-posted_at']
    
    def get_queryset(self):
        # For list/retrieve, only show approved jobs
        if self.action in ['list', 'retrieve']:
            queryset = Job.objects.filter(is_active=True, status='active')
        else:
            # For other actions, show all jobs (with proper permissions)
            queryset = Job.objects.all()
            
        queryset = queryset.select_related('startup', 'job_type', 'posted_by').prefetch_related('skills', 'applications')
        
        params = self.request.query_params
        
        # Advanced search
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
        if self.action == 'create':
            return JobCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return JobEditSerializer
        elif self.action == 'retrieve':
            return JobDetailSerializer
        elif self.action == 'my_jobs':
            return MyJobsSerializer
        return JobListSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'my_jobs']:
            permission_classes = [IsAuthenticated]
        elif self.action in ['admin_list', 'admin_action', 'bulk_admin']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticatedOrReadOnly]
        
        return [permission() for permission in permission_classes]
    
    def create(self, request, *args, **kwargs):
        """Create a new job posting (requires approval)"""
        logger.info(f"Creating new job by user: {request.user}")
        
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, 
                           status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                logger.warning(f"Job creation validation errors: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            # Create the job
            job = serializer.save()
            
            # Return created job with detail serializer
            response_serializer = JobDetailSerializer(job, context={'request': request})
            
            logger.info(f"Job created successfully: {job.title} (ID: {job.id})")
            
            return Response({
                'message': 'Job posted successfully! It will be reviewed before being published.',
                'job': response_serializer.data,
                'id': job.id,
                'status': job.status,
                'is_verified': job.is_verified,
                'success': True
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating job: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response({
                'error': 'Failed to create job. Please try again.',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def retrieve(self, request, *args, **kwargs):
        """Enhanced retrieve with view tracking"""
        try:
            instance = self.get_object()
            
            # Increment view count
            instance.increment_view_count()
            
            serializer = self.get_serializer(instance)
            
            logger.info(f"Job retrieved: {instance.title} (Views: {instance.view_count})")
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error retrieving job: {str(e)}")
            return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
    
    def update(self, request, *args, **kwargs):
        """Update job posting (only allowed for draft/pending/rejected jobs)"""
        instance = self.get_object()
        
        # Check permissions
        if not instance.can_user_edit(request.user):
            return Response({
                'error': 'You do not have permission to edit this job'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if not instance.can_edit:
            return Response({
                'error': 'This job cannot be edited in its current status'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Proceed with update
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            job = serializer.save()
            
            # Re-verify email if changed
            if 'company_email' in request.data:
                job.verify_company_email()
            
            response_serializer = JobDetailSerializer(job, context={'request': request})
            
            logger.info(f"Job updated: {job.title} by {request.user}")
            
            return Response({
                'message': 'Job updated successfully',
                'job': response_serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        """Delete job posting (only poster or admin can delete)"""
        instance = self.get_object()
        
        if not (request.user == instance.posted_by or 
                request.user.is_staff or 
                request.user.is_superuser):
            return Response({
                'error': 'You do not have permission to delete this job'
            }, status=status.HTTP_403_FORBIDDEN)
        
        logger.info(f"Deleting job {instance.title} by {request.user}")
        instance.delete()
        
        return Response({
            'message': 'Job deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)
    
    # ==================== CUSTOM ACTIONS ====================
    
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
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_jobs(self, request):
        """Get jobs posted by the current user"""
        logger.info(f"My jobs requested by user: {request.user}")
        
        # Get all jobs posted by user (including pending/rejected)
        my_jobs = Job.objects.filter(posted_by=request.user).order_by('-posted_at')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            my_jobs = my_jobs.filter(status=status_filter)
        
        page = self.paginate_queryset(my_jobs)
        if page is not None:
            serializer = MyJobsSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = MyJobsSerializer(my_jobs, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def filters(self, request):
        """Get available filter options for jobs"""
        from apps.startups.models import Industry
        
        # Get all job types with job counts
        job_types = JobType.objects.annotate(
            job_count=Count('job', filter=Q(job__is_active=True, job__status='active'))
        ).filter(job_count__gt=0).order_by('name')
        
        # Get experience levels
        experience_levels = [
            {'value': 'entry', 'label': 'Entry Level', 'count': Job.objects.filter(experience_level='entry', is_active=True, status='active').count()},
            {'value': 'mid', 'label': 'Mid Level', 'count': Job.objects.filter(experience_level='mid', is_active=True, status='active').count()},
            {'value': 'senior', 'label': 'Senior Level', 'count': Job.objects.filter(experience_level='senior', is_active=True, status='active').count()},
            {'value': 'lead', 'label': 'Lead/Principal', 'count': Job.objects.filter(experience_level='lead', is_active=True, status='active').count()},
        ]
        
        # Get industries (from startups that have jobs)
        industries = Industry.objects.annotate(
            job_count=Count('startups__jobs', filter=Q(startups__jobs__is_active=True, startups__jobs__status='active'))
        ).filter(job_count__gt=0).order_by('name')
        
        # Get popular skills
        from django.db.models import Count as CountAgg
        try:
            popular_skills_qs = Job.objects.filter(is_active=True, status='active').values(
                'skills__skill'
            ).annotate(
                count=CountAgg('skills__skill')
            ).order_by('-count')[:20]
            
            popular_skills = [item['skills__skill'] for item in popular_skills_qs if item['skills__skill']]
        except:
            popular_skills = []
        
        # Get locations
        locations = Job.objects.filter(is_active=True, status='active').values_list('location', flat=True).distinct().order_by('location')
        
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
            applied_jobs = user.job_applications.values_list('job__id', flat=True)
        except:
            applied_jobs = []
        
        # Get user's liked/bookmarked startups
        try:
            liked_startups = user.startuplike_set.values_list('startup__id', flat=True)
            bookmarked_startups = user.startupbookmark_set.values_list('startup__id', flat=True)
        except:
            liked_startups = []
            bookmarked_startups = []
        
        # Recommend jobs based on liked startups and similar companies
        recommended = self.get_queryset().filter(
            Q(startup__id__in=liked_startups) |
            Q(startup__id__in=bookmarked_startups)
        ).exclude(
            id__in=applied_jobs
        ).distinct().order_by('-posted_at')[:10]
        
        serializer = self.get_serializer(recommended, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def apply(self, request, pk=None):
        """Apply to a job"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        job = self.get_object()
        cover_letter = request.data.get('cover_letter', '')
        
        # Check if job is active and approved
        if not job.is_active or job.status != 'active':
            return Response({'error': 'This job is not currently accepting applications'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Check if already applied
        if JobApplication.objects.filter(job=job, user=request.user).exists():
            return Response({'error': 'You have already applied to this job'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        application = JobApplication.objects.create(
            job=job, user=request.user, cover_letter=cover_letter
        )
        
        serializer = JobApplicationSerializer(application)
        logger.info(f"User {request.user} applied to job {job.title}")
        
        return Response({
            'message': 'Application submitted successfully',
            'application': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_applications(self, request):
        """Get user's job applications"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            applications = JobApplication.objects.filter(user=request.user).select_related('job', 'job__startup').order_by('-applied_at')
            
            page = self.paginate_queryset(applications)
            if page is not None:
                serializer = JobApplicationSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = JobApplicationSerializer(applications, many=True)
            return Response(serializer.data)
        except:
            return Response([])
    
    # ==================== ADMIN FUNCTIONALITY ====================
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='admin')
    def admin_list(self, request):
        """Get all jobs for admin panel (including pending ones)"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        logger.info(f"Admin job panel accessed by: {request.user}")
        
        filter_type = request.query_params.get('filter', 'pending')
        search = request.query_params.get('search', '')
        
        # Get all jobs without status filter for admin
        queryset = Job.objects.all().select_related('startup', 'job_type', 'posted_by', 'approved_by').prefetch_related('skills', 'applications')
        
        # Apply filters
        if filter_type == 'pending':
            queryset = queryset.filter(status='pending')
        elif filter_type == 'approved':
            queryset = queryset.filter(status='active')
        elif filter_type == 'rejected':
            queryset = queryset.filter(status='rejected')
        elif filter_type == 'unverified':
            queryset = queryset.filter(is_verified=False)
        
        # Apply search
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search) |
                Q(startup__name__icontains=search) |
                Q(posted_by__username__icontains=search)
            )
        
        # Order by most recent first
        queryset = queryset.order_by('-posted_at')
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = JobDetailSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = JobDetailSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated], url_path='admin')
    def admin_action(self, request, pk=None):
        """Admin actions: approve, reject, verify email"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        job = self.get_object()
        action_type = request.data.get('action')
        reason = request.data.get('reason', '')
        
        logger.info(f"Admin action '{action_type}' on job {job.title} by {request.user}")
        
        try:
            if action_type == 'approve':
                if not job.is_verified:
                    return Response({'error': 'Cannot approve job with unverified email'}, 
                                  status=status.HTTP_400_BAD_REQUEST)
                
                job.approve(request.user)
                return Response({'message': 'Job approved successfully'})
            
            elif action_type == 'reject':
                job.reject(request.user, reason)
                return Response({'message': 'Job rejected successfully'})
            
            elif action_type == 'verify_email':
                verification_result = job.verify_company_email()
                if verification_result:
                    return Response({'message': 'Email verified successfully'})
                else:
                    return Response({'message': 'Email could not be automatically verified'})
            
            elif action_type == 'force_verify':
                job.is_verified = True
                job.save(update_fields=['is_verified'])
                return Response({'message': 'Email force verified'})
            
            elif action_type == 'deactivate':
                job.is_active = False
                job.status = 'paused'
                job.save(update_fields=['is_active', 'status'])
                return Response({'message': 'Job deactivated'})
            
            else:
                return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error performing admin action: {str(e)}")
            return Response({'error': 'Failed to perform action'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated], url_path='bulk-admin')
    def bulk_admin(self, request):
        """Bulk admin actions"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        job_ids = request.data.get('job_ids', [])
        action_type = request.data.get('action')
        
        logger.info(f"Bulk admin action '{action_type}' on {len(job_ids)} jobs by {request.user}")
        
        if not job_ids:
            return Response({'error': 'No jobs selected'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            jobs = Job.objects.filter(id__in=job_ids)
            
            if action_type == 'approve':
                # Only approve verified jobs
                verified_jobs = jobs.filter(is_verified=True, status='pending')
                for job in verified_jobs:
                    job.approve(request.user)
                return Response({'message': f'{verified_jobs.count()} jobs approved successfully'})
            
            elif action_type == 'reject':
                pending_jobs = jobs.filter(status='pending')
                for job in pending_jobs:
                    job.reject(request.user, 'Bulk rejection')
                return Response({'message': f'{pending_jobs.count()} jobs rejected successfully'})
            
            elif action_type == 'verify_emails':
                verified_count = 0
                for job in jobs:
                    if job.verify_company_email():
                        verified_count += 1
                return Response({'message': f'{verified_count} emails verified'})
            
            else:
                return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error performing bulk admin action: {str(e)}")
            return Response({'error': 'Failed to perform bulk action'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def admin_stats(self, request):
        """Get admin statistics for jobs"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        stats = {
            'total_jobs': Job.objects.count(),
            'pending_jobs': Job.objects.filter(status='pending').count(),
            'active_jobs': Job.objects.filter(status='active').count(),
            'rejected_jobs': Job.objects.filter(status='rejected').count(),
            'unverified_emails': Job.objects.filter(is_verified=False).count(),
            'total_applications': JobApplication.objects.count(),
            'jobs_this_week': Job.objects.filter(posted_at__gte=timezone.now() - timedelta(days=7)).count(),
        }
        
        return Response(stats)
