# startup_hub/apps/posts/admin.py
from django.contrib import admin
from django.utils.html import format_html, strip_tags
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count
from .models import (
    Topic, Post, PostImage, PostLink, Comment, PostReaction,
    CommentReaction, PostBookmark, PostView, PostShare, Mention,
    PostReport
)

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'post_count', 'follower_count', 'created_at']
    search_fields = ['name', 'slug']
    readonly_fields = ['post_count', 'follower_count', 'created_at']
    ordering = ['-post_count']
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of topics with posts
        if obj and obj.post_count > 0:
            return False
        return super().has_delete_permission(request, obj)

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = [
        'title_preview', 'author_display', 'post_type', 'status_display',
        'engagement_metrics', 'created_at', 'is_pinned', 'actions_display'
    ]
    list_filter = [
        'post_type', 'is_approved', 'is_pinned', 'is_locked', 
        'is_anonymous', 'created_at'
    ]
    search_fields = ['title', 'content', 'author__username', 'author__email']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'edited_at', 'edit_count',
        'view_count', 'like_count', 'comment_count', 'share_count',
        'bookmark_count', 'content_preview'
    ]
    filter_horizontal = ['topics']
    actions = ['approve_posts', 'reject_posts', 'pin_posts', 'unpin_posts', 'lock_posts', 'unlock_posts']
    
    fieldsets = (
        ('Post Information', {
            'fields': ('id', 'author', 'title', 'content', 'post_type', 'topics')
        }),
        ('Privacy & Moderation', {
            'fields': ('is_anonymous', 'is_approved', 'is_pinned', 'is_locked', 'is_draft')
        }),
        ('Related Content', {
            'fields': ('related_startup', 'related_job'),
            'classes': ('collapse',)
        }),
        ('Metrics', {
            'fields': (
                'view_count', 'like_count', 'comment_count', 
                'share_count', 'bookmark_count'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'edited_at', 'edit_count'),
            'classes': ('collapse',)
        }),
        ('SEO', {
            'fields': ('slug', 'meta_description'),
            'classes': ('collapse',)
        })
    )
    
    def title_preview(self, obj):
        title = obj.title or strip_tags(obj.content)[:50]
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            f"/posts/{obj.id}",
            title[:50] + '...' if len(title) > 50 else title
        )
    title_preview.short_description = 'Post'
    
    def author_display(self, obj):
        if obj.is_anonymous:
            return format_html('<em>Anonymous</em>')
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:users_user_change', args=[obj.author.pk]),
            obj.author.username
        )
    author_display.short_description = 'Author'
    
    def status_display(self, obj):
        if not obj.is_approved:
            return format_html('<span style="color: orange;">⏳ Pending</span>')
        elif obj.is_draft:
            return format_html('<span style="color: gray;">📝 Draft</span>')
        elif obj.is_locked:
            return format_html('<span style="color: red;">🔒 Locked</span>')
        else:
            return format_html('<span style="color: green;">✓ Active</span>')
    status_display.short_description = 'Status'
    
    def engagement_metrics(self, obj):
        return format_html(
            '<small>👁 {} | 👍 {} | 💬 {} | 🔗 {}</small>',
            obj.view_count, obj.like_count, obj.comment_count, obj.share_count
        )
    engagement_metrics.short_description = 'Engagement'
    
    def actions_display(self, obj):
        return format_html(
            '<a href="{}" class="button" target="_blank">View</a>',
            f"/posts/{obj.id}"
        )
    actions_display.short_description = 'Actions'
    
    def content_preview(self, obj):
        return strip_tags(obj.content)[:500] + '...' if len(obj.content) > 500 else strip_tags(obj.content)
    content_preview.short_description = 'Content Preview'
    
    # Admin Actions
    def approve_posts(self, request, queryset):
        count = queryset.filter(is_approved=False).update(is_approved=True)
        self.message_user(request, f'{count} posts approved.')
    approve_posts.short_description = "Approve selected posts"
    
    def reject_posts(self, request, queryset):
        count = queryset.update(is_approved=False)
        self.message_user(request, f'{count} posts rejected.')
    reject_posts.short_description = "Reject selected posts"
    
    def pin_posts(self, request, queryset):
        count = queryset.update(is_pinned=True)
        self.message_user(request, f'{count} posts pinned.')
    pin_posts.short_description = "Pin selected posts"
    
    def unpin_posts(self, request, queryset):
        count = queryset.update(is_pinned=False)
        self.message_user(request, f'{count} posts unpinned.')
    unpin_posts.short_description = "Unpin selected posts"
    
    def lock_posts(self, request, queryset):
        count = queryset.update(is_locked=True)
        self.message_user(request, f'{count} posts locked.')
    lock_posts.short_description = "Lock selected posts"
    
    def unlock_posts(self, request, queryset):
        count = queryset.update(is_locked=False)
        self.message_user(request, f'{count} posts unlocked.')
    unlock_posts.short_description = "Unlock selected posts"

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = [
        'content_preview', 'author_display', 'post_link', 
        'status_display', 'created_at', 'like_count'
    ]
    list_filter = ['is_approved', 'is_flagged', 'is_anonymous', 'created_at']
    search_fields = ['content', 'author__username', 'post__title']
    readonly_fields = ['created_at', 'updated_at', 'edited_at', 'like_count', 'reply_count']
    actions = ['approve_comments', 'flag_comments', 'unflag_comments']
    
    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Comment'
    
    def author_display(self, obj):
        if obj.is_anonymous:
            return format_html('<em>Anonymous</em>')
        return obj.author.username
    author_display.short_description = 'Author'
    
    def post_link(self, obj):
        post_title = obj.post.title or f"Post by {obj.post.author.username}"
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            f"/posts/{obj.post.id}",
            post_title[:30] + '...' if len(post_title) > 30 else post_title
        )
    post_link.short_description = 'Post'
    
    def status_display(self, obj):
        if obj.is_flagged:
            return format_html('<span style="color: red;">🚩 Flagged</span>')
        elif not obj.is_approved:
            return format_html('<span style="color: orange;">⏳ Pending</span>')
        else:
            return format_html('<span style="color: green;">✓ Approved</span>')
    status_display.short_description = 'Status'
    
    def approve_comments(self, request, queryset):
        count = queryset.update(is_approved=True, is_flagged=False)
        self.message_user(request, f'{count} comments approved.')
    approve_comments.short_description = "Approve selected comments"
    
    def flag_comments(self, request, queryset):
        count = queryset.update(is_flagged=True)
        self.message_user(request, f'{count} comments flagged.')
    flag_comments.short_description = "Flag selected comments"
    
    def unflag_comments(self, request, queryset):
        count = queryset.update(is_flagged=False)
        self.message_user(request, f'{count} comments unflagged.')
    unflag_comments.short_description = "Unflag selected comments"

@admin.register(PostReport)
class PostReportAdmin(admin.ModelAdmin):
    list_display = [
        'post_link', 'reported_by', 'reason', 'status_display', 
        'created_at', 'resolved_by'
    ]
    list_filter = ['reason', 'is_resolved', 'created_at']
    search_fields = ['post__title', 'reported_by__username', 'description']
    readonly_fields = ['created_at', 'resolved_at']
    actions = ['resolve_reports', 'delete_reported_posts']
    
    def post_link(self, obj):
        post_title = obj.post.title or f"Post by {obj.post.author.username}"
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            f"/posts/{obj.post.id}",
            post_title[:30] + '...' if len(post_title) > 30 else post_title
        )
    post_link.short_description = 'Reported Post'
    
    def status_display(self, obj):
        if obj.is_resolved:
            return format_html('<span style="color: green;">✓ Resolved</span>')
        return format_html('<span style="color: orange;">⏳ Pending</span>')
    status_display.short_description = 'Status'
    
    def resolve_reports(self, request, queryset):
        count = queryset.filter(is_resolved=False).update(
            is_resolved=True,
            resolved_by=request.user,
            resolved_at=timezone.now()
        )
        self.message_user(request, f'{count} reports resolved.')
    resolve_reports.short_description = "Mark as resolved"
    
    def delete_reported_posts(self, request, queryset):
        posts = set()
        for report in queryset:
            posts.add(report.post)
            report.is_resolved = True
            report.resolved_by = request.user
            report.resolved_at = timezone.now()
            report.save()
        
        for post in posts:
            post.delete()
        
        self.message_user(request, f'{len(posts)} posts deleted.')
    delete_reported_posts.short_description = "Delete reported posts"

# Inline admins
class PostImageInline(admin.TabularInline):
    model = PostImage
    extra = 0

class PostLinkInline(admin.TabularInline):
    model = PostLink
    extra = 0
    readonly_fields = ['title', 'description', 'image_url', 'domain']
