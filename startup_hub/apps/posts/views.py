# startup_hub/apps/posts/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, F, Count, Exists, OuterRef
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction
import logging

from .models import (
    Topic, Post, Comment, PostReaction, CommentReaction,
    PostBookmark, PostView, PostShare, PostReport
)
from .serializers import (
    TopicSerializer, PostListSerializer, PostDetailSerializer,
    PostCreateSerializer, CommentSerializer, CommentCreateSerializer,
    PostBookmarkSerializer, PostReportSerializer
)
from .permissions import IsAuthorOrReadOnly, CanModeratePost

logger = logging.getLogger(__name__)

class TopicViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for topics/hashtags"""
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer
    lookup_field = 'slug'
    
    @action(detail=False, methods=['get'])
    def trending(self, request):
        """Get trending topics"""
        trending = self.queryset.order_by('-post_count')[:20]
        serializer = self.get_serializer(trending, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search topics"""
        query = request.query_params.get('q', '')
        if len(query) < 2:
            return Response({'error': 'Query must be at least 2 characters'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        topics = self.queryset.filter(name__icontains=query)[:10]
        serializer = self.get_serializer(topics, many=True)
        return Response(serializer.data)

class PostViewSet(viewsets.ModelViewSet):
    """ViewSet for posts"""
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    
    def get_queryset(self):
        queryset = Post.objects.filter(is_approved=True, is_draft=False)
        
        # Annotate with user-specific data if authenticated
        if self.request.user.is_authenticated:
            queryset = queryset.annotate(
                is_liked=Exists(
                    PostReaction.objects.filter(
                        post=OuterRef('pk'),
                        user=self.request.user
                    )
                ),
                is_bookmarked=Exists(
                    PostBookmark.objects.filter(
                        post=OuterRef('pk'),
                        user=self.request.user
                    )
                )
            )
        
        # Filtering
        params = self.request.query_params
        
        # Filter by post type
        post_type = params.get('type')
        if post_type:
            queryset = queryset.filter(post_type=post_type)
        
        # Filter by topic
        topic = params.get('topic')
        if topic:
            queryset = queryset.filter(topics__slug=topic)
        
        # Filter by author
        author = params.get('author')
        if author:
            queryset = queryset.filter(author__username=author)
        
        # Search
        search = params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(content__icontains=search) |
                Q(topics__name__icontains=search)
            ).distinct()
        
        # Sorting
        sort = params.get('sort', 'new')
        if sort == 'new':
            queryset = queryset.order_by('-created_at')
        elif sort == 'top':
            queryset = queryset.order_by('-like_count', '-created_at')
        elif sort == 'hot':
            # Hot algorithm: recent posts with high engagement
            queryset = queryset.annotate(
                engagement_score=F('like_count') + F('comment_count') * 2
            ).order_by('-engagement_score', '-created_at')
        elif sort == 'discussed':
            queryset = queryset.order_by('-comment_count', '-created_at')
        
        return queryset.select_related('author').prefetch_related('topics', 'images')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PostCreateSerializer
        elif self.action == 'retrieve':
            return PostDetailSerializer
        return PostListSerializer
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        """Get post details and track view"""
        instance = self.get_object()
        
        # Track view
        if request.user.is_authenticated:
            PostView.objects.get_or_create(
                post=instance,
                user=request.user,
                ip_address=self.get_client_ip(request)
            )
        else:
            PostView.objects.create(
                post=instance,
                ip_address=self.get_client_ip(request)
            )
        
        # Increment view count
        instance.view_count = F('view_count') + 1
        instance.save(update_fields=['view_count'])
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """Update post with edit tracking"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Check if can edit
        if not instance.can_edit(request.user):
            return Response(
                {'error': 'Cannot edit post after 30 minutes'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Track edit
        instance.edited_at = timezone.now()
        instance.edit_count = F('edit_count') + 1
        
        self.perform_update(serializer)
        
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        """Add/update reaction to post"""
        post = self.get_object()
        reaction_type = request.data.get('reaction_type', 'like')
        
        # Validate reaction type
        valid_types = [rt[0] for rt in PostReaction.REACTION_TYPES]
        if reaction_type not in valid_types:
            return Response(
                {'error': f'Invalid reaction type. Must be one of: {valid_types}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            reaction, created = PostReaction.objects.update_or_create(
                post=post,
                user=request.user,
                defaults={'reaction_type': reaction_type}
            )
            
            # Update like count (only count 'like' reactions)
            post.like_count = post.reactions.filter(reaction_type='like').count()
            post.save(update_fields=['like_count'])
        
        return Response({
            'success': True,
            'reaction_type': reaction_type,
            'created': created
        })
    
    @action(detail=True, methods=['delete'])
    def unreact(self, request, pk=None):
        """Remove reaction from post"""
        post = self.get_object()
        
        try:
            reaction = PostReaction.objects.get(post=post, user=request.user)
            reaction.delete()
            
            # Update like count
            post.like_count = post.reactions.filter(reaction_type='like').count()
            post.save(update_fields=['like_count'])
            
            return Response({'success': True})
        except PostReaction.DoesNotExist:
            return Response(
                {'error': 'Reaction not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def bookmark(self, request, pk=None):
        """Bookmark/unbookmark post"""
        post = self.get_object()
        
        bookmark, created = PostBookmark.objects.get_or_create(
            post=post,
            user=request.user
        )
        
        if not created:
            bookmark.delete()
            post.bookmark_count = F('bookmark_count') - 1
            message = 'Bookmark removed'
        else:
            post.bookmark_count = F('bookmark_count') + 1
            message = 'Post bookmarked'
        
        post.save(update_fields=['bookmark_count'])
        
        return Response({
            'success': True,
            'bookmarked': created,
            'message': message
        })
    
    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        """Track post share"""
        post = self.get_object()
        platform = request.data.get('platform', 'copy_link')
        
        # Validate platform
        valid_platforms = [p[0] for p in PostShare.PLATFORMS]
        if platform not in valid_platforms:
            return Response(
                {'error': f'Invalid platform. Must be one of: {valid_platforms}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        PostShare.objects.create(
            post=post,
            user=request.user if request.user.is_authenticated else None,
            platform=platform
        )
        
        post.share_count = F('share_count') + 1
        post.save(update_fields=['share_count'])
        
        return Response({'success': True})
    
    @action(detail=True, methods=['post'])
    def report(self, request, pk=None):
        """Report post"""
        post = self.get_object()
        
        serializer = PostReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            serializer.save(
                post=post,
                reported_by=request.user
            )
            return Response({
                'success': True,
                'message': 'Post reported successfully'
            })
        except Exception as e:
            if 'unique constraint' in str(e).lower():
                return Response(
                    {'error': 'You have already reported this post'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            raise
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def pin(self, request, pk=None):
        """Pin/unpin post"""
        post = self.get_object()
        post.is_pinned = not post.is_pinned
        post.save(update_fields=['is_pinned'])
        
        return Response({
            'success': True,
            'is_pinned': post.is_pinned
        })
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def lock(self, request, pk=None):
        """Lock/unlock post comments"""
        post = self.get_object()
        post.is_locked = not post.is_locked
        post.save(update_fields=['is_locked'])
        
        return Response({
            'success': True,
            'is_locked': post.is_locked
        })
    
    @action(detail=False, methods=['get'])
    def trending(self, request):
        """Get trending posts"""
        # Posts from last 24 hours with high engagement
        since = timezone.now() - timezone.timedelta(days=1)
        
        trending = self.get_queryset().filter(
            created_at__gte=since
        ).annotate(
            engagement_score=F('like_count') + F('comment_count') * 2 + F('share_count') * 3
        ).order_by('-engagement_score')[:20]
        
        serializer = self.get_serializer(trending, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def following(self, request):
        """Get posts from users/topics the user follows"""
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # This would need a follow system implementation
        # For now, return recent posts
        posts = self.get_queryset()[:20]
        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_posts(self, request):
        """Get user's own posts"""
        posts = Post.objects.filter(
            author=request.user
        ).order_by('-created_at')
        
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def bookmarked(self, request):
        """Get user's bookmarked posts"""
        bookmarks = PostBookmark.objects.filter(
            user=request.user
        ).select_related('post').order_by('-created_at')
        
        posts = [bookmark.post for bookmark in bookmarks]
        
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class CommentViewSet(viewsets.ModelViewSet):
    """ViewSet for comments"""
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    serializer_class = CommentSerializer
    
    def get_queryset(self):
        queryset = Comment.objects.filter(is_approved=True)
        
        # Filter by post if provided
        post_id = self.request.query_params.get('post')
        if post_id:
            queryset = queryset.filter(post_id=post_id)
        
        return queryset.select_related('author', 'parent').order_by('created_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CommentCreateSerializer
        return CommentSerializer
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
    
    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        """Like/unlike comment"""
        comment = self.get_object()
        
        reaction, created = CommentReaction.objects.get_or_create(
            comment=comment,
            user=request.user,
            defaults={'is_like': True}
        )
        
        if not created:
            # Toggle like
            reaction.is_like = not reaction.is_like
            reaction.save()
            
            if not reaction.is_like:
                reaction.delete()
                created = False
        
        # Update like count
        comment.like_count = comment.reactions.filter(is_like=True).count()
        comment.save(update_fields=['like_count'])
        
        return Response({
            'success': True,
            'liked': created or reaction.is_like if not created else True
        })
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        """Approve comment"""
        comment = self.get_object()
        comment.is_approved = True
        comment.save(update_fields=['is_approved'])
        
        return Response({'success': True})
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def flag(self, request, pk=None):
        """Flag comment for review"""
        comment = self.get_object()
        comment.is_flagged = True
        comment.save(update_fields=['is_flagged'])
        
        return Response({'success': True})
