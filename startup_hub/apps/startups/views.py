# apps/startups/views.py - Complete Working Version with Startup Claiming Feature

import logging
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg, Count, Case, When, IntegerField, Min, Max
from django.db import models, transaction
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import (
    Industry, Startup, StartupRating, StartupComment, StartupBookmark, StartupLike,
    UserProfile, StartupEditRequest, StartupClaimRequest
)
from .serializers import (
    IndustrySerializer, StartupListSerializer, StartupDetailSerializer,
    StartupRatingDetailSerializer, StartupCommentDetailSerializer, StartupCreateSerializer,
    StartupEditRequestSerializer, StartupEditRequestDetailSerializer,
    StartupClaimRequestSerializer, StartupClaimRequestDetailSerializer
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
    """ViewSet for managing startups with full CRUD operations and claiming"""
    
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
        # For list/retrieve actions, only show approved startups
        if self.action in ['list', 'retrieve']:
            queryset = Startup.objects.filter(is_approved=True)
        else:
            # For create/update/delete, show all startups (with proper permissions)
            queryset = Startup.objects.all()
            
        queryset = queryset.select_related('industry', 'claimed_by').prefetch_related(
            'founders', 'tags', 'ratings', 'comments', 'likes', 'bookmarks', 'claim_requests'
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
        
        # Claimed filter
        claimed_only = params.get('claimed')
        if claimed_only == 'true':
            queryset = queryset.filter(is_claimed=True, claim_verified=True)
        elif claimed_only == 'false':
            queryset = queryset.filter(Q(is_claimed=False) | Q(claim_verified=False))
        
        return queryset
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return StartupCreateSerializer
        elif self.action == 'retrieve':
            return StartupDetailSerializer
        elif self.action in ['edit_request', 'submit_edit']:
            return StartupEditRequestSerializer
        elif self.action in ['claim_startup', 'verify_claim']:
            return StartupClaimRequestSerializer
        return StartupListSerializer
    
    def get_permissions(self):
        """Return appropriate permissions based on action"""
        if self.action == 'create':
            # Require authentication for creating startups
            permission_classes = [IsAuthenticated]
        elif self.action in ['admin_list', 'admin_action', 'bulk_admin']:
            # Require authentication for admin actions
            permission_classes = [IsAuthenticated]
        elif self.action in ['submit_edit', 'edit_request', 'upload_cover_image', 'test_edit']:
            # Require authentication for edit requests
            permission_classes = [IsAuthenticated]
        elif self.action in ['claim_startup', 'verify_claim', 'my_claims']:
            # Require authentication for claiming
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
            optimized_instance = Startup.objects.select_related(
                'industry', 'claimed_by', 'submitted_by'
            ).prefetch_related(
                'founders',
                'tags',
                'ratings__user',
                'comments__user',
                'likes__user',
                'bookmarks__user',
                'claim_requests__user'
            ).get(pk=instance.pk)
            
            serializer = self.get_serializer(optimized_instance)
            
            # Add edit permissions info
            response_data = serializer.data
            response_data['can_edit'] = optimized_instance.can_edit(request.user)
            response_data['can_claim'] = optimized_instance.can_claim(request.user)
            response_data['has_pending_edits'] = optimized_instance.has_pending_edits()
            response_data['has_pending_claims'] = optimized_instance.has_pending_claims()
            
            logger.info(f"Startup retrieved successfully: {instance.name}")
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"Error retrieving startup: {str(e)}")
            return Response({'error': 'Startup not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # ==================== STARTUP CLAIMING ACTIONS ====================
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def claim_startup(self, request, pk=None):
        """Submit a claim request for a startup"""
        logger.info(f"Claim request for startup {pk} by user: {request.user}")
        
        try:
            startup = self.get_object()
            
            # Check if user can claim this startup
            if not startup.can_claim(request.user):
                reasons = []
                if startup.is_claimed and startup.claim_verified:
                    reasons.append("This startup is already claimed and verified")
                if startup.claim_requests.filter(user=request.user, status='pending').exists():
                    reasons.append("You already have a pending claim request for this startup")
                
                return Response({
                    'error': 'Cannot claim this startup',
                    'reasons': reasons
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate request data
            serializer = StartupClaimRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            # Create claim request
            claim_request = serializer.save(
                startup=startup,
                user=request.user
            )
            
            # Send verification email
            try:
                self.send_claim_verification_email(claim_request)
                logger.info(f"Verification email sent for claim request {claim_request.id}")
            except Exception as email_error:
                logger.error(f"Failed to send verification email: {str(email_error)}")
                # Don't fail the request if email fails
            
            return Response({
                'message': 'Claim request submitted successfully! Please check your email to verify your company email address.',
                'claim_request_id': claim_request.id,
                'verification_required': True,
                'email_sent_to': claim_request.email
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error processing claim request: {str(e)}")
            return Response({
                'error': 'Failed to process claim request',
                'detail': str(e) if settings.DEBUG else 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], permission_classes=[])
    def verify_claim(self, request):
        """Verify email for claim request"""
        logger.info(f"Email verification attempt")
        
        verification_token = request.data.get('token')
        if not verification_token:
            return Response({
                'error': 'Verification token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            claim_request = StartupClaimRequest.objects.get(
                verification_token=verification_token,
                email_verified=False
            )
            
            # Check if token has expired
            if claim_request.is_expired():
                claim_request.mark_expired()
                return Response({
                    'error': 'Verification link has expired. Please submit a new claim request.',
                    'expired': True
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify email
            claim_request.verify_email()
            
            logger.info(f"Email verified for claim request {claim_request.id}")
            
            return Response({
                'message': 'Email verified successfully! Your claim request is now pending admin review.',
                'verified': True,
                'claim_request_id': claim_request.id,
                'startup_name': claim_request.startup.name
            })
            
        except StartupClaimRequest.DoesNotExist:
            return Response({
                'error': 'Invalid or already used verification token'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error verifying claim: {str(e)}")
            return Response({
                'error': 'Failed to verify claim request'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_claims(self, request):
        """Get current user's claim requests"""
        logger.info(f"Getting claim requests for user: {request.user}")
        
        claim_requests = StartupClaimRequest.objects.filter(
            user=request.user
        ).select_related('startup').order_by('-created_at')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            claim_requests = claim_requests.filter(status=status_filter)
        
        # Paginate
        page = self.paginate_queryset(claim_requests)
        if page is not None:
            serializer = StartupClaimRequestDetailSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = StartupClaimRequestDetailSerializer(claim_requests, many=True)
        return Response(serializer.data)
    
    def send_claim_verification_email(self, claim_request):
        """Send verification email for claim request"""
        verification_url = f"{settings.FRONTEND_URL}/verify-claim?token={claim_request.verification_token}"
        
        context = {
            'user_name': claim_request.user.get_full_name() or claim_request.user.username,
            'startup_name': claim_request.startup.name,
            'verification_url': verification_url,
            'position': claim_request.position,
            'expires_at': claim_request.expires_at,
        }
        
        subject = f'Verify your claim for {claim_request.startup.name} on StartupHub'
        
        # Render HTML and text versions
        html_message = render_to_string('emails/verify_claim.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[claim_request.email],
            html_message=html_message,
            fail_silently=False,
        )
    
    # ==================== EDIT REQUEST ACTIONS ====================
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def submit_edit(self, request, pk=None):
        """Submit an edit request for a startup - FIXED VERSION"""
        logger.info(f"Edit request for startup {pk} by user: {request.user}")
        
        try:
            startup = self.get_object()
            
            # Debug logging
            print(f"DEBUG: Edit request for startup {pk}")
            print(f"DEBUG: User: {request.user}")
            print(f"DEBUG: Request data: {request.data}")
            print(f"DEBUG: User can edit: {startup.can_edit(request.user)}")
            
            # Check if user can edit this startup
            if not startup.can_edit(request.user):
                logger.warning(f"User {request.user} cannot edit startup {startup.name}")
                return Response({
                    'error': 'You do not have permission to edit this startup. Only verified company representatives, premium members who submitted the startup, or admins can edit.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Check if user is admin/staff or verified company rep
            is_admin = request.user.is_staff or request.user.is_superuser
            is_verified_rep = (startup.is_claimed and startup.claim_verified and 
                             startup.claimed_by == request.user)
            
            # Get the proposed changes
            proposed_changes = request.data.get('changes', {})
            
            if not proposed_changes:
                return Response({'error': 'No changes provided'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Remove fields that shouldn't be edited
            protected_fields = ['id', 'created_at', 'updated_at', 'views', 'submitted_by', 'is_approved']
            for field in protected_fields:
                proposed_changes.pop(field, None)
            
            # Handle special fields that need processing
            if 'founders' in proposed_changes:
                # Process founders data
                founders_data = proposed_changes['founders']
                if isinstance(founders_data, list):
                    # Clear existing founders and recreate
                    startup.founders.all().delete()
                    for founder_data in founders_data:
                        if founder_data.get('name'):
                            startup.founders.create(
                                name=founder_data.get('name', ''),
                                title=founder_data.get('title', 'Founder'),
                                bio=founder_data.get('bio', ''),
                                linkedin_url=founder_data.get('linkedin_url', ''),
                                twitter_url=founder_data.get('twitter_url', '')
                            )
                proposed_changes.pop('founders')  # Remove from regular field updates
            
            if 'tags' in proposed_changes:
                # Process tags data
                tags_data = proposed_changes['tags']
                if isinstance(tags_data, list):
                    # Clear existing tags and recreate
                    startup.tags.all().delete()
                    for tag in tags_data:
                        if tag.strip():
                            startup.tags.create(tag=tag.strip())
                proposed_changes.pop('tags')  # Remove from regular field updates
            
            if 'social_media' in proposed_changes:
                # Handle social media data
                social_media_data = proposed_changes['social_media']
                if isinstance(social_media_data, dict):
                    startup.social_media = social_media_data
                    startup.save(update_fields=['social_media'])
                proposed_changes.pop('social_media')

            with transaction.atomic():
                if is_admin or is_verified_rep:
                    # Admin or verified company rep can directly update the startup
                    logger.info(f"{'Admin' if is_admin else 'Verified company rep'} {request.user} directly updating startup {startup.name}")
                    
                    for field, value in proposed_changes.items():
                        if hasattr(startup, field):
                            # FIXED: Handle ForeignKey fields properly
                            if field == 'industry':
                                # Convert industry ID to Industry instance
                                try:
                                    industry = Industry.objects.get(id=int(value))
                                    setattr(startup, field, industry)
                                    print(f"DEBUG: Successfully set industry to {industry.name} (ID: {industry.id})")
                                except (Industry.DoesNotExist, ValueError, TypeError) as e:
                                    logger.error(f"Invalid industry ID: {value}, error: {str(e)}")
                                    return Response({
                                        'error': f'Invalid industry ID: {value}. Please select a valid industry.'
                                    }, status=status.HTTP_400_BAD_REQUEST)
                            else:
                                # For regular fields, set directly
                                setattr(startup, field, value)
                                print(f"DEBUG: Set {field} to {value}")
                    
                    startup.save()
                    print(f"DEBUG: Startup saved successfully")
                    
                    # Return updated startup
                    serializer = StartupDetailSerializer(startup, context={'request': request})
                    
                    return Response({
                        'message': 'Startup updated successfully',
                        'startup': serializer.data,
                        'direct_update': True
                    })
                    
                else:
                    # Premium member - create edit request
                    logger.info(f"Creating edit request for startup {startup.name} by premium user {request.user}")
                    
                    # Check if user already has a pending edit request
                    existing_pending = StartupEditRequest.objects.filter(
                        startup=startup,
                        requested_by=request.user,
                        status='pending'
                    ).first()
                    
                    if existing_pending:
                        return Response({
                            'error': 'You already have a pending edit request for this startup. Please wait for it to be reviewed.'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    # Create original values dict
                    original_values = {}
                    for field in proposed_changes.keys():
                        if hasattr(startup, field):
                            if field == 'industry':
                                # Store industry ID for edit requests
                                original_values[field] = startup.industry.id if startup.industry else None
                            else:
                                original_values[field] = getattr(startup, field)
                    
                    # Create edit request
                    edit_request = StartupEditRequest.objects.create(
                        startup=startup,
                        requested_by=request.user,
                        proposed_changes=proposed_changes,
                        original_values=original_values
                    )
                    
                    logger.info(f"Edit request created successfully (ID: {edit_request.id})")
                    
                    return Response({
                        'message': 'Edit request submitted successfully. It will be reviewed by an admin.',
                        'edit_request_id': edit_request.id,
                        'status': 'pending'
                    }, status=status.HTTP_201_CREATED)
                    
        except Exception as e:
            logger.error(f"Error processing edit request: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response({
                'error': 'Failed to process edit request',
                'detail': str(e) if settings.DEBUG else 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def upload_cover_image(self, request, pk=None):
        """Upload cover image for a startup"""
        logger.info(f"Uploading cover image for startup {pk} by user: {request.user}")
        
        startup = self.get_object()
        
        # Check if user can edit this startup
        if not startup.can_edit(request.user):
            logger.warning(f"User {request.user} cannot upload image for startup {startup.name}")
            return Response({
                'error': 'You do not have permission to edit this startup'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if image file is provided
        cover_image = request.FILES.get('cover_image')
        if not cover_image:
            return Response({
                'error': 'No image file provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate file type
        if not cover_image.content_type.startswith('image/'):
            return Response({
                'error': 'File must be an image (PNG, JPG, GIF)'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate file size (5MB limit)
        if cover_image.size > 5 * 1024 * 1024:
            return Response({
                'error': 'Image file too large (max 5MB)'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            import os
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            import uuid
            
            # Generate unique filename
            file_extension = os.path.splitext(cover_image.name)[1].lower()
            unique_filename = f"startup_covers/{startup.id}_{uuid.uuid4().hex}{file_extension}"
            
            # Save the file
            if hasattr(settings, 'MEDIA_ROOT') and settings.MEDIA_ROOT:
                # Save to local media directory
                file_path = default_storage.save(unique_filename, ContentFile(cover_image.read()))
                
                # Build the full URL
                if hasattr(request, 'build_absolute_uri'):
                    cover_image_url = request.build_absolute_uri(settings.MEDIA_URL + file_path)
                else:
                    cover_image_url = settings.MEDIA_URL + file_path
                    
            else:
                # Fallback: create a data URL (base64 encoded) - not recommended for production
                import base64
                encoded_image = base64.b64encode(cover_image.read()).decode('utf-8')
                cover_image_url = f"data:{cover_image.content_type};base64,{encoded_image}"
            
            # Update the startup's cover image URL
            startup.cover_image_url = cover_image_url
            startup.save(update_fields=['cover_image_url'])
            
            logger.info(f"Cover image uploaded successfully for {startup.name}")
            
            return Response({
                'message': 'Cover image uploaded successfully',
                'cover_image_url': cover_image_url,
                'filename': cover_image.name,
                'size': cover_image.size
            })
            
        except Exception as e:
            logger.error(f"Error uploading cover image: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response({
                'error': 'Failed to upload image',
                'detail': str(e) if settings.DEBUG else 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def edit_requests(self, request, pk=None):
        """Get edit requests for a startup"""
        startup = self.get_object()
        
        # Check permissions - only admins, the startup submitter, or verified company rep can view edit requests
        if not (request.user.is_staff or request.user.is_superuser or 
                request.user == startup.submitted_by or request.user == startup.claimed_by):
            return Response({
                'error': 'You do not have permission to view edit requests for this startup'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get edit requests
        edit_requests = startup.edit_requests.all().order_by('-created_at')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            edit_requests = edit_requests.filter(status=status_filter)
        
        # Paginate
        page = self.paginate_queryset(edit_requests)
        if page is not None:
            serializer = StartupEditRequestDetailSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = StartupEditRequestDetailSerializer(edit_requests, many=True)
        return Response(serializer.data)
    
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
    def my_startups(self, request):
        """Get startups submitted by the current user"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        logger.info(f"My startups requested by user: {request.user}")
        
        # Get all startups submitted by user (including unapproved ones)
        my_startups = Startup.objects.filter(submitted_by=request.user).order_by('-created_at')
        
        # Apply pagination
        page = self.paginate_queryset(my_startups)
        if page is not None:
            serializer = StartupDetailSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = StartupDetailSerializer(my_startups, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_claimed_startups(self, request):
        """Get startups claimed by the current user"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        logger.info(f"My claimed startups requested by user: {request.user}")
        
        # Get all startups claimed by user
        claimed_startups = Startup.objects.filter(
            claimed_by=request.user, 
            claim_verified=True
        ).order_by('-created_at')
        
        # Apply pagination
        page = self.paginate_queryset(claimed_startups)
        if page is not None:
            serializer = StartupDetailSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = StartupDetailSerializer(claimed_startups, many=True, context={'request': request})
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
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='admin')
    def admin_list(self, request):
        """Get all startups for admin panel (including unapproved ones)"""
        if not (request.user.is_staff or request.user.is_superuser):
            logger.warning(f"Non-admin user {request.user} attempted to access admin panel")
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        logger.info(f"Admin panel accessed by: {request.user}")
        
        filter_type = request.query_params.get('filter', 'all')
        search = request.query_params.get('search', '')
        
        # Get all startups without approval filter for admin
        queryset = Startup.objects.all().select_related(
            'industry', 'submitted_by', 'claimed_by'
        ).prefetch_related(
            'founders', 'tags', 'claim_requests'
        )
        
        # Apply filters
        if filter_type == 'pending':
            queryset = queryset.filter(is_approved=False)
        elif filter_type == 'approved':
            queryset = queryset.filter(is_approved=True, is_featured=False)
        elif filter_type == 'featured':
            queryset = queryset.filter(is_featured=True)
        elif filter_type == 'claimed':
            queryset = queryset.filter(is_claimed=True, claim_verified=True)
        elif filter_type == 'pending_claims':
            queryset = queryset.filter(claim_requests__status='pending').distinct()
        
        # Apply search
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        
        # Order by most recent first
        queryset = queryset.order_by('-created_at')
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = StartupDetailSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = StartupDetailSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated], url_path='admin')
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
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated], url_path='bulk-admin')
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
    
    # ==================== ADMIN CLAIM REQUEST ACTIONS ====================
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='admin/claim-requests')
    def admin_claim_requests(self, request):
        """Get all claim requests for admin review"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        logger.info(f"Admin viewing all claim requests")
        
        # Get filter parameters
        status_filter = request.query_params.get('status', 'pending')
        startup_id = request.query_params.get('startup')
        
        # Base queryset
        queryset = StartupClaimRequest.objects.select_related('startup', 'user', 'reviewed_by')
        
        # Apply filters
        if status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        
        if startup_id:
            queryset = queryset.filter(startup_id=startup_id)
        
        # Order by most recent first
        queryset = queryset.order_by('-created_at')
        
        # Paginate
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = StartupClaimRequestDetailSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = StartupClaimRequestDetailSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated], url_path='admin/claim-requests/(?P<request_id>[^/.]+)/approve')
    def approve_claim_request(self, request, request_id=None):
        """Approve a claim request"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            claim_request = get_object_or_404(
                StartupClaimRequest, 
                id=request_id, 
                status='pending',
                email_verified=True
            )
            
            logger.info(f"Admin {request.user} approving claim request {request_id}")
            
            # Get approval notes
            notes = request.data.get('notes', '')
            
            # Approve the claim
            claim_request.approve(request.user, notes)
            
            # Return updated startup
            serializer = StartupDetailSerializer(claim_request.startup, context={'request': request})
            
            return Response({
                'message': 'Claim request approved successfully',
                'startup': serializer.data,
                'claimed_by': claim_request.user.username
            })
            
        except StartupClaimRequest.DoesNotExist:
            return Response({'error': 'Claim request not found, already processed, or email not verified'}, 
                          status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error approving claim request: {str(e)}")
            return Response({'error': 'Failed to approve claim request'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated], url_path='admin/claim-requests/(?P<request_id>[^/.]+)/reject')
    def reject_claim_request(self, request, request_id=None):
        """Reject a claim request"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            claim_request = get_object_or_404(StartupClaimRequest, id=request_id, status='pending')
            
            logger.info(f"Admin {request.user} rejecting claim request {request_id}")
            
            # Get rejection notes
            notes = request.data.get('notes', '')
            
            # Reject the request
            claim_request.reject(request.user, notes)
            
            return Response({
                'message': 'Claim request rejected successfully',
                'claim_request_id': claim_request.id
            })
            
        except StartupClaimRequest.DoesNotExist:
            return Response({'error': 'Claim request not found or already processed'}, 
                          status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error rejecting claim request: {str(e)}")
            return Response({'error': 'Failed to reject claim request'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # ==================== ADMIN EDIT REQUEST ACTIONS ====================
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='edit-requests')
    def admin_edit_requests(self, request):
        """Get all edit requests for admin review"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        logger.info(f"Admin viewing all edit requests")
        
        # Get filter parameters
        status_filter = request.query_params.get('status', 'pending')
        startup_id = request.query_params.get('startup')
        
        # Base queryset
        queryset = StartupEditRequest.objects.select_related('startup', 'requested_by', 'reviewed_by')
        
        # Apply filters
        if status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        
        if startup_id:
            queryset = queryset.filter(startup_id=startup_id)
        
        # Order by most recent first
        queryset = queryset.order_by('-created_at')
        
        # Paginate
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = StartupEditRequestDetailSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = StartupEditRequestDetailSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated], url_path='edit-requests/(?P<request_id>[^/.]+)/approve')
    def approve_edit_request(self, request, request_id=None):
        """Approve an edit request and apply changes"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            edit_request = get_object_or_404(StartupEditRequest, id=request_id, status='pending')
            
            logger.info(f"Admin {request.user} approving edit request {request_id}")
            
            # Approve and apply changes
            edit_request.approve(request.user)
            
            # Return updated startup
            serializer = StartupDetailSerializer(edit_request.startup, context={'request': request})
            
            return Response({
                'message': 'Edit request approved and changes applied successfully',
                'startup': serializer.data
            })
            
        except StartupEditRequest.DoesNotExist:
            return Response({'error': 'Edit request not found or already processed'}, 
                          status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error approving edit request: {str(e)}")
            return Response({'error': 'Failed to approve edit request'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated], url_path='edit-requests/(?P<request_id>[^/.]+)/reject')
    def reject_edit_request(self, request, request_id=None):
        """Reject an edit request"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            edit_request = get_object_or_404(StartupEditRequest, id=request_id, status='pending')
            
            logger.info(f"Admin {request.user} rejecting edit request {request_id}")
            
            # Get rejection notes
            notes = request.data.get('notes', '')
            
            # Reject the request
            edit_request.reject(request.user, notes)
            
            return Response({
                'message': 'Edit request rejected successfully',
                'edit_request_id': edit_request.id
            })
            
        except StartupEditRequest.DoesNotExist:
            return Response({'error': 'Edit request not found or already processed'}, 
                          status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error rejecting edit request: {str(e)}")
            return Response({'error': 'Failed to reject edit request'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # ==================== HELPER METHODS ====================
    
    def perform_create(self, serializer):
        """Called when creating a new startup instance"""
        # This is called by the DRF create method
        # We set submitted_by to current user and is_approved to False
        serializer.save(submitted_by=self.request.user, is_approved=False)
    
    def perform_update(self, serializer):
        """Called when updating a startup instance"""
        # Only allow the submitter, verified company rep, or admin to update
        startup = self.get_object()
        if not (self.request.user == startup.submitted_by or 
                self.request.user == startup.claimed_by or
                self.request.user.is_staff or 
                self.request.user.is_superuser):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to edit this startup")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """Called when deleting a startup instance"""
        # Only allow the submitter, verified company rep, or admin to delete
        if not (self.request.user == instance.submitted_by or 
                self.request.user == instance.claimed_by or
                self.request.user.is_staff or 
                self.request.user.is_superuser):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to delete this startup")
        
        logger.info(f"Deleting startup {instance.name} by {self.request.user}")
        instance.delete()


class StartupEditRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing edit requests (read-only for non-admins)"""
    queryset = StartupEditRequest.objects.all()
    serializer_class = StartupEditRequestDetailSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on user permissions"""
        queryset = super().get_queryset()
        
        if self.request.user.is_staff or self.request.user.is_superuser:
            # Admins can see all edit requests
            return queryset
        else:
            # Regular users can only see their own edit requests
            return queryset.filter(requested_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """Get edit requests submitted by the current user"""
        my_requests = self.get_queryset().filter(requested_by=request.user).order_by('-created_at')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            my_requests = my_requests.filter(status=status_filter)
        
        page = self.paginate_queryset(my_requests)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(my_requests, many=True)
        return Response(serializer.data)


class StartupClaimRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing claim requests (read-only for non-admins)"""
    queryset = StartupClaimRequest.objects.all()
    serializer_class = StartupClaimRequestDetailSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on user permissions"""
        queryset = super().get_queryset()
        
        if self.request.user.is_staff or self.request.user.is_superuser:
            # Admins can see all claim requests
            return queryset
        else:
            # Regular users can only see their own claim requests
            return queryset.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """Get claim requests submitted by the current user"""
        my_requests = self.get_queryset().filter(user=request.user).order_by('-created_at')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            my_requests = my_requests.filter(status=status_filter)
        
        page = self.paginate_queryset(my_requests)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(my_requests, many=True)
        return Response(serializer.data)
