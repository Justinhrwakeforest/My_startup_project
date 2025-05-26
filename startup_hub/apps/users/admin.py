from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserInterest

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'is_staff', 'is_premium')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_premium')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('bio', 'location', 'is_premium')}),
    )

@admin.register(UserInterest)
class UserInterestAdmin(admin.ModelAdmin):
    list_display = ('user', 'interest')
    list_filter = ('interest',) 
