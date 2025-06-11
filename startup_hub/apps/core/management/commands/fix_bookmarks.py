# Create apps/core/management/commands/fix_bookmarks.py
from django.core.management.base import BaseCommand
from apps.startups.models import StartupBookmark

class Command(BaseCommand):
    help = 'Fix bookmark data inconsistencies'

    def handle(self, *args, **options):
        # Remove any duplicate bookmarks
        duplicates = StartupBookmark.objects.values('user', 'startup').annotate(
            count=models.Count('id')
        ).filter(count__gt=1)
        
        for duplicate in duplicates:
            bookmarks = StartupBookmark.objects.filter(
                user_id=duplicate['user'],
                startup_id=duplicate['startup']
            ).order_by('created_at')
            
            # Keep the first one, delete the rest
            for bookmark in bookmarks[1:]:
                bookmark.delete()
                
        self.stdout.write(
            self.style.SUCCESS('Successfully fixed bookmark duplicates')
        )
