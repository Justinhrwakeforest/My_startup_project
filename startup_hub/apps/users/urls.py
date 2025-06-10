# apps/users/urls.py - Updated with new endpoints
from django.urls import path
from .views import (
    UserRegistrationView, UserLoginView, UserLogoutView, UserProfileView,
    ChangePasswordView, user_interests, remove_user_interest, user_activity,
    export_user_data, user_bookmarks, user_stats
)

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('logout/', UserLogoutView.as_view(), name='user-logout'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('interests/', user_interests, name='user-interests'),
    path('interests/<int:interest_id>/', remove_user_interest, name='remove-interest'),
    path('activity/', user_activity, name='user-activity'),
    path('export-data/', export_user_data, name='export-user-data'),
    path('bookmarks/', user_bookmarks, name='user-bookmarks'),
    path('stats/', user_stats, name='user-stats'),
]
