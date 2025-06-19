# startup_hub/apps/startups/admin.py - Admin interface for startup management
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    Industry, Startup, StartupFounder, StartupTag, StartupRating, 
    StartupComment, StartupBookmark, StartupLike, StartupSubmission
)

@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'startup_count', 'description']
    search_fields = ['name', 'description']
    ordering = ['name']
    
    def startup_count(self, obj):
        return obj.startups.count()
    startup_count.short_description = 'Number of Startups'

class StartupFounderInline(admin.TabularInline):
    model = StartupFounder
    extra = 1
    max_num = 5

class StartupTagInline(admin.TabularInline):
    model = StartupTag
    extra = 1
    max_num = 10

@admin.register(Startup)
class StartupAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'industry', 'location', 'employee_count', 'founded_year',
        'is_approved', 'is_featured', 'submitted_by', 'approval_status',
        'total_ratings', 'average_rating', 'views', 'created_at'
    ]
    list_filter = [
        'is_approved', 'is_featured', 'industry', 'founded_year', 
        'created_at'
    ]
    search_fields = ['name', 'description', 'location', 'founders__name']
    ordering = ['-created_at']
    readonly_fields = ['views', 'created_at', 'updated_at', 'average_rating', 'total_ratings']
    
    inlines = [StartupFounderInline, StartupTagInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'logo', 'description', 'industry', 'location', 'website')
        }),
        ('Company Details', {
            'fields': ('employee_count', 'founded_year', 'funding_amount', 'valuation')
        }),
        ('Metrics', {
            'fields': ('revenue', 'user_count', 'growth_rate', 'cover_image_url')
        }),
        ('Status', {
            'fields': ('is_approved', 'is_featured', 'submitted_by')
        }),
        ('System Info', {
            'fields': ('views', 'average_rating', 'total_ratings', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_startups', 'feature_startups', 'unfeature_startups']
    
    def approval_status(self, obj):
        if obj.is_approved:
            return format_html('<span style="color: green;">✓ Approved</span>')
        else:
            return format_html('<span style="color: red;">✗ Pending</span>')
    approval_status.short_description = 'Status'
    
    def total_ratings(self, obj):
        return obj.ratings.count()
    total_ratings.short_description = 'Total Ratings'
    
    def average_rating(self, obj):
        avg = obj.average_rating
        if avg:
            return f"{avg:.1f}/5.0"
        return "No ratings"
    average_rating.short_description = 'Avg Rating'
    
    def approve_startups(self, request, queryset):
        updated = queryset.update(is_approved=True)
        # Also update submission status if exists
        for startup in queryset:
            if hasattr(startup, 'submission'):
                startup.submission.status = 'approved'
                startup.submission.reviewed_by = request.user
                startup.submission.reviewed_at = timezone.now()
                startup.submission.save()
        
        self.message_user(request, f'{updated} startup(s) were approved.')
    approve_startups.short_description = "Approve selected startups"
    
    def feature_startups(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} startup(s) were featured.')
    feature_startups.short_description = "Feature selected startups"
    
    def unfeature_startups(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} startup(s) were unfeatured.')
    unfeature_startups.short_description = "Unfeature selected startups"

@admin.register(StartupSubmission)
class StartupSubmissionAdmin(admin.ModelAdmin):
    list_display = [
        'startup_name', 'submitted_by', 'status', 'submitted_at', 
        'reviewed_by', 'reviewed_at', 'startup_link'
    ]
    list_filter = ['status', 'submitted_at', 'reviewed_at']
    search_fields = ['startup__name', 'submitted_by__username', 'submitted_by__email']
    ordering = ['-submitted_at']
    readonly_fields = ['submitted_at', 'updated_at']
    
    fieldsets = (
        ('Submission Info', {
            'fields': ('startup', 'submitted_by', 'status', 'submitted_at')
        }),
        ('Review Info', {
            'fields': ('reviewed_by', 'reviewed_at', 'review_notes')
        }),
    )
    
    actions = ['approve_submissions', 'reject_submissions', 'request_revisions']
    
    def startup_name(self, obj):
        return obj.startup.name
    startup_name.short_description = 'Startup Name'
    
    def startup_link(self, obj):
        url = reverse('admin:startups_startup_change', args=[obj.startup.pk])
        return format_html('<a href="{}">View Startup</a>', url)
    startup_link.short_description = 'Startup'
    
    def approve_submissions(self, request, queryset):
        for submission in queryset:
            submission.status = 'approved'
            submission.reviewed_by = request.user
            submission.reviewed_at = timezone.now()
            submission.startup.is_approved = True
            submission.startup.save()
            submission.save()
        
        self.message_user(request, f'{queryset.count()} submission(s) were approved.')
    approve_submissions.short_description = "Approve selected submissions"
    
    def reject_submissions(self, request, queryset):
        for submission in queryset:
            submission.status = 'rejected'
            submission.reviewed_by = request.user
            submission.reviewed_at = timezone.now()
            submission.startup.is_approved = False
            submission.startup.save()
            submission.save()
        
        self.message_user(request, f'{queryset.count()} submission(s) were rejected.')
    reject_submissions.short_description = "Reject selected submissions"
    
    def request_revisions(self, request, queryset):
        for submission in queryset:
            submission.status = 'revision_requested'
            submission.reviewed_by = request.user
            submission.reviewed_at = timezone.now()
            submission.save()
        
        self.message_user(request, f'{queryset.count()} submission(s) marked for revision.')
    request_revisions.short_description = "Request revisions for selected submissions"

@admin.register(StartupFounder)
class StartupFounderAdmin(admin.ModelAdmin):
    list_display = ['name', 'startup', 'title', 'bio_preview']
    list_filter = ['title', 'startup__industry']
    search_fields = ['name', 'startup__name', 'bio']
    ordering = ['startup__name', 'name']
    
    def bio_preview(self, obj):
        return obj.bio[:50] + "..." if len(obj.bio) > 50 else obj.bio
    bio_preview.short_description = 'Bio Preview'

@admin.register(StartupTag)
class StartupTagAdmin(admin.ModelAdmin):
    list_display = ['tag', 'startup', 'usage_count']
    list_filter = ['startup__industry']
    search_fields = ['tag', 'startup__name']
    ordering = ['tag']
    
    def usage_count(self, obj):
        return StartupTag.objects.filter(tag=obj.tag).count()
    usage_count.short_description = 'Usage Count'

@admin.register(StartupRating)
class StartupRatingAdmin(admin.ModelAdmin):
    list_display = ['startup', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at', 'startup__industry']
    search_fields = ['startup__name', 'user__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at']

@admin.register(StartupComment)
class StartupCommentAdmin(admin.ModelAdmin):
    list_display = ['startup', 'user', 'text_preview', 'likes', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'is_flagged', 'created_at', 'startup__industry']
    search_fields = ['startup__name', 'user__username', 'text']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'likes']
    
    actions = ['approve_comments', 'flag_comments']
    
    def text_preview(self, obj):
        return obj.text[:100] + "..." if len(obj.text) > 100 else obj.text
    text_preview.short_description = 'Comment Preview'
    
    def approve_comments(self, request, queryset):
        updated = queryset.update(is_approved=True, is_flagged=False)
        self.message_user(request, f'{updated} comment(s) were approved.')
    approve_comments.short_description = "Approve selected comments"
    
    def flag_comments(self, request, queryset):
        updated = queryset.update(is_flagged=True, is_approved=False)
        self.message_user(request, f'{updated} comment(s) were flagged.')
    flag_comments.short_description = "Flag selected comments"

@admin.register(StartupBookmark)
class StartupBookmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'startup', 'created_at', 'notes_preview']
    list_filter = ['created_at', 'startup__industry']
    search_fields = ['user__username', 'startup__name', 'notes']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    
    def notes_preview(self, obj):
        if obj.notes:
            return obj.notes[:50] + "..." if len(obj.notes) > 50 else obj.notes
        return "No notes"
    notes_preview.short_description = 'Notes Preview'

@admin.register(StartupLike)
class StartupLikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'startup', 'created_at']
    list_filter = ['created_at', 'startup__industry']
    search_fields = ['user__username', 'startup__name']
    ordering = ['-created_at']
    readonly_fields = ['created_at']

# Customize admin site header and title
admin.site.site_header = "StartupHub Administration"
admin.site.site_title = "StartupHub Admin"
admin.site.index_title = "Welcome to StartupHub Administration"
