# apps/users/admin.py - Fixed version
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserInterest

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'is_staff', 'is_premium', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_premium', 'date_joined')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    # Define custom fieldsets instead of extending UserAdmin.fieldsets
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'bio', 'location')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_premium', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    # Make date_joined readonly
    readonly_fields = ('date_joined',)
    
    # For adding new users
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
        ('Additional Info', {
            'fields': ('first_name', 'last_name', 'bio', 'location', 'is_premium'),
        }),
    )

@admin.register(UserInterest)
class UserInterestAdmin(admin.ModelAdmin):
    list_display = ('user', 'interest')
    list_filter = ('interest',)
    search_fields = ('user__username', 'user__email', 'interest')
