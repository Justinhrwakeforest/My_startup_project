# startup_hub/apps/core/management/commands/send_job_alerts.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from datetime import timedelta
from apps.jobs.models import JobAlert, Job
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send job alerts to users based on their preferences'

    def add_arguments(self, parser):
        parser.add_argument(
            '--frequency',
            type=str,
            choices=['immediate', 'daily', 'weekly'],
            help='Send alerts for specific frequency only',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending emails',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='Send alerts for a specific user only',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Limit number of alerts to process',
        )

    def handle(self, *args, **options):
        frequency = options.get('frequency')
        dry_run = options.get('dry_run', False)
        user_id = options.get('user_id')
        limit = options.get('limit', 100)
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Starting job alert processing... (dry_run: {dry_run})"
            )
        )
        
        # Get alerts that need to be sent
        alerts_queryset = JobAlert.objects.filter(is_active=True).select_related(
            'user', 'job_type', 'industry'
        )
        
        if frequency:
            alerts_queryset = alerts_queryset.filter(frequency=frequency)
        
        if user_id:
            alerts_queryset = alerts_queryset.filter(user_id=user_id)
        
        alerts_to_process = alerts_queryset[:limit]
        
        total_sent = 0
        total_errors = 0
        
        for alert in alerts_to_process:
            try:
                if alert.should_send_alert():
                    matching_jobs = self.get_new_matching_jobs(alert)
                    
                    if matching_jobs.exists():
                        if dry_run:
                            self.stdout.write(
                                f"[DRY RUN] Would send alert '{alert.title}' to {alert.user.email} "
                                f"with {matching_jobs.count()} jobs"
                            )
                            total_sent += 1
                        else:
                            success = self.send_job_alert(alert, matching_jobs)
                            if success:
                                alert.mark_as_sent()
                                total_sent += 1
                                self.stdout.write(
                                    f"Sent alert '{alert.title}' to {alert.user.email} "
                                    f"with {matching_jobs.count()} jobs"
                                )
                            else:
                                total_errors += 1
                    else:
                        self.stdout.write(
                            f"No new jobs for alert '{alert.title}' ({alert.user.email})"
                        )
            except Exception as e:
                logger.error(f"Error processing alert {alert.id}: {str(e)}")
                total_errors += 1
                self.stdout.write(
                    self.style.ERROR(f"Error processing alert {alert.id}: {str(e)}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Job alert processing completed. "
                f"Sent: {total_sent}, Errors: {total_errors}"
            )
        )

    def get_new_matching_jobs(self, alert):
        """Get jobs that match the alert criteria and are new since last sent"""
        matching_jobs = alert.get_matching_jobs()
        
        # For immediate alerts, only include jobs posted since last sent
        if alert.frequency == 'immediate' and alert.last_sent:
            matching_jobs = matching_jobs.filter(posted_at__gt=alert.last_sent)
        
        # For daily alerts, include jobs from the last day
        elif alert.frequency == 'daily':
            cutoff = timezone.now() - timedelta(days=1)
            if alert.last_sent and alert.last_sent > cutoff:
                cutoff = alert.last_sent
            matching_jobs = matching_jobs.filter(posted_at__gte=cutoff)
        
        # For weekly alerts, include jobs from the last week
        elif alert.frequency == 'weekly':
            cutoff = timezone.now() - timedelta(days=7)
            if alert.last_sent and alert.last_sent > cutoff:
                cutoff = alert.last_sent
            matching_jobs = matching_jobs.filter(posted_at__gte=cutoff)
        
        return matching_jobs.distinct()

    def send_job_alert(self, alert, jobs):
        """Send job alert email to user"""
        try:
            # Prepare email context
            context = {
                'user': alert.user,
                'alert': alert,
                'jobs': jobs[:10],  # Limit to 10 jobs per email
                'total_jobs': jobs.count(),
                'unsubscribe_url': self.get_unsubscribe_url(alert),
                'dashboard_url': f"{settings.FRONTEND_URL}/profile",
                'site_name': 'StartupHub',
            }
            
            # Render email templates
            subject = f"New Job Alert: {alert.title} - {jobs.count()} new {'job' if jobs.count() == 1 else 'jobs'}"
            
            # Plain text version
            text_content = render_to_string('emails/job_alert.txt', context)
            
            # HTML version
            html_content = render_to_string('emails/job_alert.html', context)
            
            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[alert.user.email],
                headers={
                    'List-Unsubscribe': f'<{context["unsubscribe_url"]}>',
                    'X-Alert-ID': str(alert.id),
                }
            )
            
            # Attach HTML version
            email.attach_alternative(html_content, "text/html")
            
            # Send email
            email.send()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email for alert {alert.id}: {str(e)}")
            return False

    def get_unsubscribe_url(self, alert):
        """Generate unsubscribe URL for the alert"""
        # This would typically include a signed token for security
        return f"{settings.FRONTEND_URL}/settings/alerts/unsubscribe/{alert.id}"
