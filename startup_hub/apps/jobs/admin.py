# startup_hub/apps/jobs/admin.py - Updated without email verification

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from .models import JobType, Job, JobSkill, JobApplication, JobEditRequest

@admin.register(JobType)
class JobTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'job_count']
    search_fields = ['name']
    
    def job_count(self, obj):
        return obj.job_set.count()
    job_count.short_description = 'Total Jobs'

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'startup', 'posted_by', 'company_email', 
        'status', 'approval_status', 'location', 'job_type', 'is_remote', 
        'is_urgent', 'posted_at', 'application_count'
    ]
    list_filter = [
        'status', 'job_type', 'is_remote', 'is_urgent', 
        'experience_level', 'posted_at', 'approved_at'
    ]
    search_fields = ['title', 'description', 'startup__name', 'posted_by__username', 'company_email']
    readonly_fields = [
        'posted_at', 'updated_at', 'view_count', 'posted_by', 'approved_by', 
        'approved_at'
    ]
    
    fieldsets = (
        ('Job Information', {
            'fields': ('title', 'description', 'startup', 'job_type', 'location', 'salary_range')
        }),
        ('Requirements', {
            'fields': ('experience_level', 'requirements', 'benefits')
        }),
        ('Work Options', {
            'fields': ('is_remote', 'is_urgent', 'application_deadline', 'expires_at')
        }),
        ('Posting Information', {
            'fields': ('posted_by', 'company_email')
        }),
        ('Status & Approval', {
            'fields': ('status', 'is_active', 'approved_by', 'approved_at', 'rejection_reason')
        }),
        ('Metrics', {
            'fields': ('view_count', 'posted_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_jobs', 'reject_jobs', 'deactivate_jobs']
    
    def approval_status(self, obj):
        """Display approval status with colors"""
        status_colors = {
            'pending': 'orange',
            'active': 'green', 
            'rejected': 'red',
            'draft': 'gray',
            'paused': 'blue',
            'closed': 'gray'
        }
        color = status_colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>', 
            color, 
            obj.get_status_display()
        )
    approval_status.short_description = 'Status'
    
    def application_count(self, obj):
        """Show number of applications"""
        count = obj.applications.count()
        if count > 0:
            url = reverse('admin:jobs_jobapplication_changelist') + f'?job__id__exact={obj.pk}'
            return format_html('<a href="{}">{} applications</a>', url, count)
        return "0 applications"
    application_count.short_description = 'Applications'
    
    def approve_jobs(self, request, queryset):
        """Approve selected job postings"""
        pending_jobs = queryset.filter(status='pending')
        approved_count = 0
        
        for job in pending_jobs:
            job.approve(request.user)
            approved_count += 1
            messages.success(request, f'Approved job: {job.title}')
        
        if approved_count > 0:
            messages.success(request, f'{approved_count} job(s) approved successfully.')
    approve_jobs.short_description = "Approve selected jobs"
    
    def reject_jobs(self, request, queryset):
        """Reject selected job postings"""
        pending_jobs = queryset.filter(status='pending')
        rejected_count = 0
        
        for job in pending_jobs:
            job.reject(request.user, 'Rejected via admin action')
            rejected_count += 1
        
        if rejected_count > 0:
            messages.success(request, f'{rejected_count} job(s) rejected.')
    reject_jobs.short_description = "Reject selected jobs"
    
    def deactivate_jobs(self, request, queryset):
        """Deactivate selected jobs"""
        updated = queryset.update(is_active=False, status='paused')
        messages.success(request, f'{updated} job(s) deactivated.')
    deactivate_jobs.short_description = "Deactivate selected jobs"
    
    def get_queryset(self, request):
        """Optimize queryset with related data"""
        return super().get_queryset(request).select_related(
            'startup', 'job_type', 'posted_by', 'approved_by'
        ).prefetch_related('applications')

@admin.register(JobEditRequest)
class JobEditRequestAdmin(admin.ModelAdmin):
    list_display = [
        'job_title', 'job_startup', 'requested_by', 'status', 'created_at', 
        'reviewed_by', 'reviewed_at', 'changes_preview'
    ]
    list_filter = ['status', 'created_at', 'reviewed_at']
    search_fields = ['job__title', 'job__startup__name', 'requested_by__username']
    readonly_fields = ['created_at', 'updated_at', 'job', 'requested_by', 'changes_display']
    
    fieldsets = (
        ('Request Information', {
            'fields': ('job', 'requested_by', 'status', 'created_at')
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
    
    def job_title(self, obj):
        """Link to job admin page"""
        url = reverse('admin:jobs_job_change', args=[obj.job.pk])
        return format_html('<a href="{}">{}</a>', url, obj.job.title)
    job_title.short_description = 'Job'
    
    def job_startup(self, obj):
        """Show startup name"""
        return obj.job.startup.name if obj.job.startup else 'Independent'
    job_startup.short_description = 'Startup'
    
    def changes_preview(self, obj):
        """Show a preview of changes"""
        changes = []
        for field, new_value in obj.proposed_changes.items():
            old_value = obj.original_values.get(field, '')
            if old_value != new_value:
                changes.append(f"{field}: '{str(old_value)[:30]}...' → '{str(new_value)[:30]}...'")
        
        preview = '<br>'.join(changes[:3])
        if len(changes) > 3:
            preview += f'<br>... and {len(changes) - 3} more'
        
        return format_html('<small>{}</small>', preview) if changes else 'No changes'
    changes_preview.short_description = 'Changes'
    
    def changes_display(self, obj):
        """Detailed changes display"""
        changes_html = '<table style="width: 100%; border-collapse: collapse;">'
        changes_html += '<tr><th style="text-align: left; padding: 5px; border-bottom: 1px solid #ddd;">Field</th>'
        changes_html += '<th style="text-align: left; padding: 5px; border-bottom: 1px solid #ddd;">Original</th>'
        changes_html += '<th style="text-align: left; padding: 5px; border-bottom: 1px solid #ddd;">Proposed</th></tr>'
        
        for field, new_value in obj.proposed_changes.items():
            old_value = obj.original_values.get(field, '')
            if old_value != new_value:
                changes_html += f'<tr>'
                changes_html += f'<td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{field}</strong></td>'
                changes_html += f'<td style="padding: 5px; border-bottom: 1px solid #eee; color: #666;">{old_value or "(empty)"}</td>'
                changes_html += f'<td style="padding: 5px; border-bottom: 1px solid #eee; color: #0a0;">{new_value or "(empty)"}</td>'
                changes_html += f'</tr>'
        
        changes_html += '</table>'
        return format_html(changes_html)
    changes_display.short_description = 'Detailed Changes'
    
    def approve_edit_requests(self, request, queryset):
        """Approve selected edit requests"""
        approved_count = 0
        for edit_request in queryset.filter(status='pending'):
            try:
                # Apply changes to the job
                job = edit_request.job
                for field, value in edit_request.proposed_changes.items():
                    if hasattr(job, field):
                        setattr(job, field, value)
                job.save()
                
                # Mark request as approved
                edit_request.status = 'approved'
                edit_request.reviewed_by = request.user
                edit_request.reviewed_at = timezone.now()
                edit_request.save()
                
                approved_count += 1
                messages.success(request, f'Edit request for "{job.title}" approved and applied.')
            except Exception as e:
                messages.error(request, f'Error approving edit request: {str(e)}')
        
        if approved_count > 0:
            messages.success(request, f'{approved_count} edit request(s) approved.')
    approve_edit_requests.short_description = "Approve selected edit requests"
    
    def reject_edit_requests(self, request, queryset):
        """Reject selected edit requests"""
        rejected_count = 0
        for edit_request in queryset.filter(status='pending'):
            edit_request.status = 'rejected'
            edit_request.reviewed_by = request.user
            edit_request.reviewed_at = timezone.now()
            edit_request.review_notes = 'Rejected via admin action'
            edit_request.save()
            rejected_count += 1
        
        if rejected_count > 0:
            messages.success(request, f'{rejected_count} edit request(s) rejected.')
    reject_edit_requests.short_description = "Reject selected edit requests"

@admin.register(JobSkill)
class JobSkillAdmin(admin.ModelAdmin):
    list_display = ['skill', 'job', 'is_required', 'proficiency_level']
    list_filter = ['is_required', 'proficiency_level', 'skill']
    search_fields = ['skill', 'job__title']

@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ['job_title', 'user', 'status', 'applied_at', 'days_since_applied']
    list_filter = ['status', 'applied_at', 'job__startup']
    search_fields = ['job__title', 'user__username', 'user__email']
    readonly_fields = ['applied_at', 'days_since_applied']
    
    def job_title(self, obj):
        return obj.job.title
    job_title.short_description = 'Job Title'
    
    def days_since_applied(self, obj):
        return obj.days_since_applied
    days_since_applied.short_description = 'Days Since Applied'

# Customize admin site
admin.site.site_header = "StartupHub Job Management"
admin.site.site_title = "Job Admin"
admin.site.index_title = "Job Administration Panel"
