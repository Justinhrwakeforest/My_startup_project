# startup_hub/apps/jobs/migrations/0002_add_approval_system.py
# Generated migration for the job approval system

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('jobs', '0001_initial'),
    ]

    operations = [
        # Add new fields to Job model
        migrations.AddField(
            model_name='job',
            name='posted_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='posted_jobs', to=settings.AUTH_USER_MODEL, default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='job',
            name='company_email',
            field=models.EmailField(help_text='Company email to verify authorization', max_length=254, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='job',
            name='is_verified',
            field=models.BooleanField(default=False, help_text='Email domain verified against company'),
        ),
        migrations.AddField(
            model_name='job',
            name='approved_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_jobs', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='job',
            name='approved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='job',
            name='rejection_reason',
            field=models.TextField(blank=True),
        ),
        
        # Update status choices
        migrations.AlterField(
            model_name='job',
            name='status',
            field=models.CharField(choices=[('draft', 'Draft'), ('pending', 'Pending Approval'), ('active', 'Active'), ('paused', 'Paused'), ('closed', 'Closed'), ('rejected', 'Rejected')], default='pending', max_length=20),
        ),
        
        # Update is_active default
        migrations.AlterField(
            model_name='job',
            name='is_active',
            field=models.BooleanField(default=False),
        ),
        
        # Add new indexes
        migrations.AddIndex(
            model_name='job',
            index=models.Index(fields=['status', 'posted_at'], name='jobs_job_status_posted_idx'),
        ),
        migrations.AddIndex(
            model_name='job',
            index=models.Index(fields=['posted_by', 'status'], name='jobs_job_posted_by_status_idx'),
        ),
        
        # Create JobEditRequest model
        migrations.CreateModel(
            name='JobEditRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending Review'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('proposed_changes', models.JSONField(help_text='JSON object of field names and new values')),
                ('original_values', models.JSONField(help_text='JSON object of field names and original values')),
                ('review_notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='edit_requests', to='jobs.job')),
                ('requested_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='job_edit_requests', to=settings.AUTH_USER_MODEL)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_job_edits', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='jobeditrequest',
            index=models.Index(fields=['status', 'created_at'], name='jobs_jobeditrequest_status_created_idx'),
        ),
        migrations.AddIndex(
            model_name='jobeditrequest',
            index=models.Index(fields=['job', 'status'], name='jobs_jobeditrequest_job_status_idx'),
        ),
    ]
