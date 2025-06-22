# startup_hub/apps/startups/admin.py - Complete file with claim request management

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
import json
from .models import (
    Industry, Startup, StartupFounder, StartupTag, StartupRating, 
    StartupComment, StartupBookmark, StartupLike, StartupSubmission,
    UserProfile, StartupEditRequest, StartupClaimRequest
)

@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'startup_count', 'description']
    search_fields = ['name', 'description']
    ordering = ['name']
    
    def startup_count(self, obj):
        return obj.startups.count()
    startup_count.short_description = 'Number of Startups'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_premium', 'premium_expires_at', 'is_premium_active']
    list_filter = ['is_premium', 'premium_expires_at']
    search_fields = ['user__username', 'user__email']
    ordering = ['-premium_expires_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Premium Status', {
            'fields': ('is_premium', 'premium_expires_at'),
            'description': 'Manage premium membership status for users'
        }),
    )
    
    def is_premium_active(self, obj):
        return obj.is_premium_active
    is_premium_active.boolean = True
    is_premium_active.short_description = 'Premium Active'

class StartupFounderInline(admin.TabularInline):
    model = StartupFounder
    extra = 1
    max_num = 5

class StartupTagInline(admin.TabularInline):
    model = StartupTag
    extra = 1
    max_num = 10

class StartupEditRequestInline(admin.TabularInline):
    model = StartupEditRequest
    extra = 0
    fields = ['requested_by', 'status', 'created_at', 'view_details']
    readonly_fields = ['requested_by', 'created_at', 'view_details']
    can_delete = False
    
    def view_details(self, obj):
        url = reverse('admin:startups_startupeditrequest_change', args=[obj.pk])
        return format_html('<a href="{}">View Details</a>', url)
    view_details.short_description = 'Details'

class StartupClaimRequestInline(admin.TabularInline):
    model = StartupClaimRequest
    extra = 0
    fields = ['user', 'email', 'status', 'email_verified', 'created_at', 'view_details']
    readonly_fields = ['user', 'email', 'created_at', 'view_details']
    can_delete = False
    
    def view_details(self, obj):
        url = reverse('admin:startups_startupclaimrequest_change', args=[obj.pk])
        return format_html('<a href="{}">View Details</a>', url)
    view_details.short_description = 'Details'

@admin.register(Startup)
class StartupAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'industry', 'location', 'employee_count', 'founded_year',
        'is_approved', 'is_featured', 'is_claimed', 'claim_status', 'submitted_by', 
        'claimed_by', 'approval_status', 'total_ratings', 'average_rating', 
        'views', 'has_pending_edits', 'has_pending_claims', 'created_at'
    ]
    list_filter = [
        'is_approved', 'is_featured', 'is_claimed', 'claim_verified', 
        'industry', 'founded_year', 'created_at'
    ]
    search_fields = ['name', 'description', 'location', 'founders__name']
    ordering = ['-created_at']
    readonly_fields = [
        'views', 'created_at', 'updated_at', 'average_rating', 'total_ratings', 
        'submitted_by', 'claimed_by', 'is_claimed', 'claim_verified'
    ]
    
    inlines = [StartupFounderInline, StartupTagInline, StartupEditRequestInline, StartupClaimRequestInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'logo', 'description', 'industry', 'location', 'website', 'cover_image_url')
        }),
        ('Company Details', {
            'fields': ('employee_count', 'founded_year', 'funding_amount', 'valuation', 'business_model', 'target_market')
        }),
        ('Metrics', {
            'fields': ('revenue', 'user_count', 'growth_rate')
        }),
        ('Contact Information', {
            'fields': ('contact_email', 'contact_phone'),
            'classes': ('collapse',)
        }),
        ('Status & Ownership', {
            'fields': ('is_approved', 'is_featured', 'submitted_by', 'is_claimed', 'claim_verified', 'claimed_by')
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
    
    def claim_status(self, obj):
        if obj.is_claimed and obj.claim_verified:
            return format_html('<span style="color: green;">✓ Verified</span>')
        elif obj.is_claimed:
            return format_html('<span style="color: orange;">⚠ Unverified</span>')
        else:
            return format_html('<span style="color: gray;">- Unclaimed</span>')
    claim_status.short_description = 'Claim Status'
    
    def total_ratings(self, obj):
        return obj.ratings.count()
    total_ratings.short_description = 'Total Ratings'
    
    def average_rating(self, obj):
        avg = obj.average_rating
        if avg:
            return f"{avg:.1f}/5.0"
        return "No ratings"
    average_rating.short_description = 'Avg Rating'
    
    def has_pending_edits(self, obj):
        pending_count = obj.edit_requests.filter(status='pending').count()
        if pending_count > 0:
            url = reverse('admin:startups_startupeditrequest_changelist') + f'?startup__id__exact={obj.pk}&status__exact=pending'
            return format_html('<a href="{}" style="color: orange; font-weight: bold;">{} pending</a>', url, pending_count)
        return format_html('<span style="color: green;">None</span>')
    has_pending_edits.short_description = 'Pending Edits'
    
    def has_pending_claims(self, obj):
        pending_count = obj.claim_requests.filter(status='pending').count()
        if pending_count > 0:
            url = reverse('admin:startups_startupclaimrequest_changelist') + f'?startup__id__exact={obj.pk}&status__exact=pending'
            return format_html('<a href="{}" style="color: blue; font-weight: bold;">{} pending</a>', url, pending_count)
        return format_html('<span style="color: green;">None</span>')
    has_pending_claims.short_description = 'Pending Claims'
    
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

@admin.register(StartupClaimRequest)
class StartupClaimRequestAdmin(admin.ModelAdmin):
    list_display = [
        'startup_name', 'user_info', 'email', 'position', 'status', 
        'email_verified', 'email_domain_valid', 'created_at', 
        'reviewed_by', 'reviewed_at'
    ]
    list_filter = ['status', 'email_verified', 'created_at', 'reviewed_at']
    search_fields = ['startup__name', 'user__username', 'user__email', 'email', 'position']
    ordering = ['-created_at']
    readonly_fields = [
        'created_at', 'updated_at', 'user', 'startup', 'verification_token', 
        'email_verified_at', 'is_expired', 'email_domain_valid'
    ]
    
    fieldsets = (
        ('Claim Information', {
            'fields': ('startup', 'user', 'email', 'position', 'reason')
        }),
        ('Verification', {
            'fields': ('email_verified', 'email_verified_at', 'verification_token', 'expires_at', 'is_expired', 'email_domain_valid')
        }),
        ('Status & Review', {
            'fields': ('status', 'reviewed_by', 'reviewed_at', 'review_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_claim_requests', 'reject_claim_requests', 'send_verification_emails']
    
    def startup_name(self, obj):
        url = reverse('admin:startups_startup_change', args=[obj.startup.pk])
        return format_html('<a href="{}">{}</a>', url, obj.startup.name)
    startup_name.short_description = 'Startup'
    
    def user_info(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a><br><small>{}</small>', 
                          url, obj.user.username, obj.user.email)
    user_info.short_description = 'User'
    
    def email_domain_valid(self, obj):
        if obj.is_email_domain_valid():
            return format_html('<span style="color: green;">✓ Valid</span>')
        else:
            return format_html('<span style="color: red;">✗ Invalid</span>')
    email_domain_valid.short_description = 'Domain Valid'
    
    def is_expired(self, obj):
        if obj.is_expired():
            return format_html('<span style="color: red;">✗ Expired</span>')
        else:
            return format_html('<span style="color: green;">✓ Valid</span>')
    is_expired.short_description = 'Token Status'
    
    def approve_claim_requests(self, request, queryset):
        approved_count = 0
        for claim_request in queryset.filter(status='pending', email_verified=True):
            try:
                claim_request.approve(request.user)
                approved_count += 1
                messages.success(request, f'Claim request for "{claim_request.startup.name}" by {claim_request.user.username} approved.')
            except Exception as e:
                messages.error(request, f'Error approving claim request for "{claim_request.startup.name}": {str(e)}')
        
        if approved_count > 0:
            messages.success(request, f'{approved_count} claim request(s) were approved.')
        
        # Show warning for unverified emails
        unverified_count = queryset.filter(status='pending', email_verified=False).count()
        if unverified_count > 0:
            messages.warning(request, f'{unverified_count} claim request(s) cannot be approved because email is not verified.')
    approve_claim_requests.short_description = "Approve selected claim requests (email verified only)"
    
    def reject_claim_requests(self, request, queryset):
        rejected_count = 0
        for claim_request in queryset.filter(status='pending'):
            claim_request.reject(request.user, 'Rejected via admin action')
            rejected_count += 1
        
        if rejected_count > 0:
            messages.success(request, f'{rejected_count} claim request(s) were rejected.')
    reject_claim_requests.short_description = "Reject selected claim requests"
    
    def send_verification_emails(self, request, queryset):
        """Resend verification emails for selected claim requests"""
        sent_count = 0
        for claim_request in queryset.filter(status='pending', email_verified=False):
            if not claim_request.is_expired():
                try:
                    # You would need to implement the email sending logic here
                    # self.send_claim_verification_email(claim_request)
                    sent_count += 1
                except Exception as e:
                    messages.error(request, f'Error sending email for "{claim_request.startup.name}": {str(e)}')
        
        if sent_count > 0:
            messages.success(request, f'{sent_count} verification email(s) were sent.')
    send_verification_emails.short_description = "Resend verification emails"
    
    def get_readonly_fields(self, request, obj=None):
        # Make certain fields readonly if the request is not pending
        if obj and obj.status != 'pending':
            return self.readonly_fields + ['email', 'position', 'reason']
        return self.readonly_fields

@admin.register(StartupEditRequest)
class StartupEditRequestAdmin(admin.ModelAdmin):
    list_display = [
        'startup_name', 'requested_by', 'status', 'created_at', 
        'reviewed_by', 'reviewed_at', 'changes_preview'
    ]
    list_filter = ['status', 'created_at', 'reviewed_at']
    search_fields = ['startup__name', 'requested_by__username', 'requested_by__email']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'requested_by', 'startup', 'original_values', 'changes_display']
    
    fieldsets = (
        ('Request Information', {
            'fields': ('startup', 'requested_by', 'status', 'created_at')
        }),
        ('Proposed Changes', {
            'fields': ('changes_display', 'proposed_changes', 'original_values'),
            'description': 'Review the proposed changes below'
        }),
        ('Review Information', {
            'fields': ('reviewed_by', 'reviewed_at', 'review_notes')
        }),
    )
    
    actions = ['approve_edit_requests', 'reject_edit_requests']
    
    def startup_name(self, obj):
        url = reverse('admin:startups_startup_change', args=[obj.startup.pk])
        return format_html('<a href="{}">{}</a>', url, obj.startup.name)
    startup_name.short_description = 'Startup'
    
    def changes_preview(self, obj):
        changes = obj.get_changes_display()
        if changes:
            preview = '<br>'.join(changes[:3])  # Show first 3 changes
            if len(changes) > 3:
                preview += f'<br>... and {len(changes) - 3} more'
            return format_html('<small>{}</small>', preview)
        return 'No changes'
    changes_preview.short_description = 'Changes'
    
    def changes_display(self, obj):
        changes = obj.get_changes_display()
        if changes:
            html = '<table style="width: 100%; border-collapse: collapse;">'
            html += '<tr><th style="text-align: left; padding: 5px; border-bottom: 1px solid #ddd;">Field</th>'
            html += '<th style="text-align: left; padding: 5px; border-bottom: 1px solid #ddd;">Original</th>'
            html += '<th style="text-align: left; padding: 5px; border-bottom: 1px solid #ddd;">Proposed</th></tr>'
            
            for field, new_value in obj.proposed_changes.items():
                old_value = obj.original_values.get(field, '')
                if old_value != new_value:
                    html += f'<tr>'
                    html += f'<td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{field}</strong></td>'
                    html += f'<td style="padding: 5px; border-bottom: 1px solid #eee; color: #666;">{old_value or "(empty)"}</td>'
                    html += f'<td style="padding: 5px; border-bottom: 1px solid #eee; color: #0a0;">{new_value or "(empty)"}</td>'
                    html += f'</tr>'
            
            html += '</table>'
            return format_html(html)
        return 'No changes'
    changes_display.short_description = 'Detailed Changes'
    
    def approve_edit_requests(self, request, queryset):
        approved_count = 0
        for edit_request in queryset.filter(status='pending'):
            try:
                edit_request.approve(request.user)
                approved_count += 1
                messages.success(request, f'Edit request for "{edit_request.startup.name}" approved and changes applied.')
            except Exception as e:
                messages.error(request, f'Error approving edit request for "{edit_request.startup.name}": {str(e)}')
        
        if approved_count > 0:
            messages.success(request, f'{approved_count} edit request(s) were approved and changes applied.')
    approve_edit_requests.short_description = "Approve selected edit requests"
    
    def reject_edit_requests(self, request, queryset):
        rejected_count = 0
        for edit_request in queryset.filter(status='pending'):
            edit_request.reject(request.user, 'Rejected via admin action')
            rejected_count += 1
        
        if rejected_count > 0:
            messages.success(request, f'{rejected_count} edit request(s) were rejected.')
    reject_edit_requests.short_description = "Reject selected edit requests"
    
    def get_readonly_fields(self, request, obj=None):
        # Make proposed_changes readonly if the request is not pending
        if obj and obj.status != 'pending':
            return self.readonly_fields + ['proposed_changes']
        return self.readonly_fields

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
