# Create apps/jobs/models.py - Add JobAlert model

class JobAlert(models.Model):
    ALERT_FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('immediate', 'Immediate'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_alerts')
    title = models.CharField(max_length=100)
    keywords = models.TextField(blank=True, help_text="Comma-separated keywords")
    location = models.CharField(max_length=100, blank=True)
    job_type = models.ForeignKey(JobType, on_delete=models.SET_NULL, null=True, blank=True)
    experience_level = models.CharField(max_length=20, choices=Job.EXPERIENCE_CHOICES, blank=True)
    is_remote = models.BooleanField(default=False)
    industry = models.ForeignKey('startups.Industry', on_delete=models.SET_NULL, null=True, blank=True)
    frequency = models.CharField(max_length=20, choices=ALERT_FREQUENCY_CHOICES, default='daily')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_sent = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def get_matching_jobs(self):
        """Get jobs that match this alert criteria"""
        queryset = Job.objects.filter(is_active=True)
        
        # Filter by keywords
        if self.keywords:
            keywords = [k.strip() for k in self.keywords.split(',')]
            keyword_q = Q()
            for keyword in keywords:
                keyword_q |= (
                    Q(title__icontains=keyword) |
                    Q(description__icontains=keyword) |
                    Q(skills__skill__icontains=keyword)
                )
            queryset = queryset.filter(keyword_q).distinct()
        
        # Filter by location
        if self.location:
            queryset = queryset.filter(location__icontains=self.location)
        
        # Filter by job type
        if self.job_type:
            queryset = queryset.filter(job_type=self.job_type)
        
        # Filter by experience level
        if self.experience_level:
            queryset = queryset.filter(experience_level=self.experience_level)
        
        # Filter by remote
        if self.is_remote:
            queryset = queryset.filter(is_remote=True)
        
        # Filter by industry
        if self.industry:
            queryset = queryset.filter(startup__industry=self.industry)
        
        return queryset.order_by('-posted_at')


# Create apps/jobs/serializers.py - Add JobAlert serializers

class JobAlertSerializer(serializers.ModelSerializer):
    job_type_name = serializers.CharField(source='job_type.name', read_only=True)
    industry_name = serializers.CharField(source='industry.name', read_only=True)
    matching_jobs_count = serializers.SerializerMethodField()
    
    class Meta:
        model = JobAlert
        fields = [
            'id', 'title', 'keywords', 'location', 'job_type', 'job_type_name',
            'experience_level', 'is_remote', 'industry', 'industry_name',
            'frequency', 'is_active', 'created_at', 'last_sent', 'matching_jobs_count'
        ]
        read_only_fields = ['last_sent']
    
    def get_matching_jobs_count(self, obj):
        return obj.get_matching_jobs().count()


# Create apps/jobs/views.py - Add JobAlert viewset

from rest_framework import viewsets
from .models import JobAlert
from .serializers import JobAlertSerializer

class JobAlertViewSet(viewsets.ModelViewSet):
    serializer_class = JobAlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return JobAlert.objects.filter(user=self.request.user).order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Preview jobs that match this alert"""
        alert = self.get_object()
        matching_jobs = alert.get_matching_jobs()[:10]  # Limit to 10 for preview
        
        from .serializers import JobListSerializer
        serializer = JobListSerializer(matching_jobs, many=True, context={'request': request})
        
        return Response({
            'alert': JobAlertSerializer(alert).data,
            'matching_jobs': serializer.data,
            'total_matches': alert.get_matching_jobs().count()
        })
    
    @action(detail=True, methods=['post'])
    def test_send(self, request, pk=None):
        """Test send alert email"""
        alert = self.get_object()
        matching_jobs = alert.get_matching_jobs()[:5]
        
        if matching_jobs.exists():
            # Here you would implement email sending
            # For now, just return the jobs that would be sent
            from .serializers import JobListSerializer
            serializer = JobListSerializer(matching_jobs, many=True, context={'request': request})
            
            return Response({
                'message': f'Test alert would include {len(serializer.data)} jobs',
                'jobs': serializer.data
            })
        else:
            return Response({
                'message': 'No matching jobs found for this alert'
            })


# Create apps/core/management/commands/send_job_alerts.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.jobs.models import JobAlert, Job
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

class Command(BaseCommand):
    help = 'Send job alerts to users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--frequency',
            type=str,
            choices=['immediate', 'daily', 'weekly'],
            help='Send alerts for specific frequency',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending',
        )

    def handle(self, *args, **options):
        frequency = options.get('frequency')
        dry_run = options.get('dry_run', False)
        
        # Get alerts that need to be sent
        alerts_to_send = JobAlert.objects.filter(is_active=True)
        
        if frequency:
            alerts_to_send = alerts_to_send.filter(frequency=frequency)
        
        # Filter based on when they were last sent
        now = timezone.now()
        for alert in alerts_to_send:
            should_send = False
            
            if alert.frequency == 'immediate':
                # For immediate alerts, check if there are new jobs since last sent
                if alert.last_sent:
                    new_jobs = alert.get_matching_jobs().filter(posted_at__gt=alert.last_sent)
                    should_send = new_jobs.exists()
                else:
                    should_send = True
            
            elif alert.frequency == 'daily':
                # Send daily if not sent today
                if not alert.last_sent or alert.last_sent.date() < now.date():
                    should_send = True
            
            elif alert.frequency == 'weekly':
                # Send weekly if not sent in the last 7 days
                if not alert.last_sent or alert.last_sent < now - timedelta(days=7):
                    should_send = True
            
            if should_send:
                matching_jobs = alert.get_matching_jobs()
                
                # For immediate alerts, only include new jobs
                if alert.frequency == 'immediate' and alert.last_sent:
                    matching_jobs = matching_jobs.filter(posted_at__gt=alert.last_sent)
                else:
                    # For daily/weekly, include jobs from the last period
                    if alert.frequency == 'daily':
                        cutoff = now - timedelta(days=1)
                    else:  # weekly
                        cutoff = now - timedelta(days=7)
                    matching_jobs = matching_jobs.filter(posted_at__gte=cutoff)
                
                if matching_jobs.exists():
                    if dry_run:
                        self.stdout.write(
                            f"Would send alert '{alert.title}' to {alert.user.email} "
                            f"with {matching_jobs.count()} jobs"
                        )
                    else:
                        self.send_job_alert(alert, matching_jobs)
