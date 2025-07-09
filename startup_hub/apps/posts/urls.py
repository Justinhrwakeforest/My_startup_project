# startup_hub/apps/posts/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TopicViewSet, PostViewSet, CommentViewSet

router = DefaultRouter()
router.register(r'topics', TopicViewSet, basename='topic')
router.register(r'posts', PostViewSet, basename='post')
router.register(r'comments', CommentViewSet, basename='comment')

urlpatterns = [
    path('', include(router.urls)),
    
    # Additional custom endpoints can be added here if needed
    # For example:
    # path('posts/<uuid:post_id>/comments/', CommentListView.as_view(), name='post-comments'),
]
