# startup_hub/apps/posts/permissions.py
from rest_framework import permissions

class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow authors of a post/comment to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the author
        return obj.author == request.user

class CanModeratePost(permissions.BasePermission):
    """
    Permission for moderators and admins
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_staff or 
            request.user.is_superuser or
            getattr(request.user, 'is_moderator', False)
        )

class CanEditPost(permissions.BasePermission):
    """
    Permission to check if user can edit post (within time limit)
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return obj.can_edit(request.user)

class IsNotLocked(permissions.BasePermission):
    """
    Permission to check if post is not locked for comments
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # For comment creation, check if post is locked
        if view.action == 'create' and 'post' in request.data:
            try:
                from .models import Post
                post = Post.objects.get(id=request.data['post'])
                return not post.is_locked
            except Post.DoesNotExist:
                return True
        
        return True
