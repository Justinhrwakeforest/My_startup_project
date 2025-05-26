from django.contrib import admin
from .models import Industry, Startup, StartupFounder, StartupTag, StartupRating, StartupComment, StartupBookmark, StartupLike

@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon']
    search_fields = ['name']

@admin.register(Startup)
class StartupAdmin(admin.ModelAdmin):
    list_display = ['name', 'industry', 'location', 'founded_year', 'is_featured', 'employee_count']
    list_filter = ['industry', 'is_featured', 'founded_year']
    search_fields = ['name', 'description']
    readonly_fields = ['views', 'created_at', 'updated_at', 'average_rating', 'total_ratings']

@admin.register(StartupFounder)
class StartupFounderAdmin(admin.ModelAdmin):
    list_display = ['name', 'startup', 'title']
    list_filter = ['startup']

@admin.register(StartupTag)
class StartupTagAdmin(admin.ModelAdmin):
    list_display = ['tag', 'startup']
    list_filter = ['tag']

@admin.register(StartupRating)
class StartupRatingAdmin(admin.ModelAdmin):
    list_display = ['startup', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']

@admin.register(StartupComment)
class StartupCommentAdmin(admin.ModelAdmin):
    list_display = ['startup', 'user', 'text', 'likes', 'created_at']
    list_filter = ['created_at']

@admin.register(StartupBookmark)
class StartupBookmarkAdmin(admin.ModelAdmin):
    list_display = ['startup', 'user', 'created_at']
    list_filter = ['created_at']

@admin.register(StartupLike)
class StartupLikeAdmin(admin.ModelAdmin):
    list_display = ['startup', 'user', 'created_at']
    list_filter = ['created_at']
