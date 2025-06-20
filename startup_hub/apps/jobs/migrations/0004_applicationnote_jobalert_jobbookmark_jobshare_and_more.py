# Generated by Django 5.2.1 on 2025-06-15 05:54

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0003_initial'),
        ('startups', '0002_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ApplicationNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('note', models.TextField()),
                ('is_internal', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='JobAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('keywords', models.TextField(blank=True, help_text='Comma-separated keywords')),
                ('location', models.CharField(blank=True, max_length=100)),
                ('experience_level', models.CharField(blank=True, choices=[('entry', 'Entry Level'), ('mid', 'Mid Level'), ('senior', 'Senior Level'), ('lead', 'Lead/Principal')], max_length=20)),
                ('is_remote', models.BooleanField(default=False)),
                ('min_salary', models.CharField(blank=True, max_length=20)),
                ('max_salary', models.CharField(blank=True, max_length=20)),
                ('frequency', models.CharField(choices=[('immediate', 'Immediate'), ('daily', 'Daily'), ('weekly', 'Weekly')], default='daily', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_sent', models.DateTimeField(blank=True, null=True)),
                ('total_sent', models.PositiveIntegerField(default=0)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='JobBookmark',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('notes', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='JobShare',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('platform', models.CharField(choices=[('email', 'Email'), ('linkedin', 'LinkedIn'), ('twitter', 'Twitter'), ('facebook', 'Facebook'), ('copy_link', 'Copy Link'), ('other', 'Other')], default='copy_link', max_length=20)),
                ('shared_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='JobTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('title_template', models.CharField(max_length=100)),
                ('description_template', models.TextField()),
                ('requirements_template', models.TextField(blank=True)),
                ('benefits_template', models.TextField(blank=True)),
                ('is_default', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='JobView',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip_address', models.GenericIPAddressField()),
                ('user_agent', models.TextField(blank=True)),
                ('viewed_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AlterModelOptions(
            name='job',
            options={'ordering': ['-posted_at']},
        ),
        migrations.AlterModelOptions(
            name='jobapplication',
            options={'ordering': ['-applied_at']},
        ),
        migrations.AddField(
            model_name='job',
            name='application_deadline',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='job',
            name='benefits',
            field=models.TextField(blank=True, help_text='Benefits and perks'),
        ),
        migrations.AddField(
            model_name='job',
            name='expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='job',
            name='requirements',
            field=models.TextField(blank=True, help_text='Job requirements in detail'),
        ),
        migrations.AddField(
            model_name='job',
            name='status',
            field=models.CharField(choices=[('active', 'Active'), ('paused', 'Paused'), ('closed', 'Closed'), ('draft', 'Draft')], default='active', max_length=20),
        ),
        migrations.AddField(
            model_name='job',
            name='view_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='jobapplication',
            name='additional_info',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='jobapplication',
            name='interview_notes',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='jobapplication',
            name='interview_scheduled_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='jobapplication',
            name='review_notes',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='jobapplication',
            name='reviewed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='jobapplication',
            name='reviewed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_applications', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='jobapplication',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='jobskill',
            name='is_required',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='jobskill',
            name='proficiency_level',
            field=models.CharField(choices=[('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('advanced', 'Advanced'), ('expert', 'Expert')], default='intermediate', max_length=20),
        ),
        migrations.AlterField(
            model_name='job',
            name='salary_range',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='jobapplication',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('reviewing', 'Under Review'), ('interview', 'Interview Scheduled'), ('offer', 'Offer Extended'), ('accepted', 'Accepted'), ('rejected', 'Rejected'), ('withdrawn', 'Withdrawn')], default='pending', max_length=20),
        ),
        migrations.AlterField(
            model_name='jobapplication',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='job_applications', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddIndex(
            model_name='job',
            index=models.Index(fields=['posted_at'], name='jobs_job_posted__7edcdf_idx'),
        ),
        migrations.AddIndex(
            model_name='job',
            index=models.Index(fields=['is_active', 'status'], name='jobs_job_is_acti_74c18c_idx'),
        ),
        migrations.AddIndex(
            model_name='job',
            index=models.Index(fields=['startup', 'is_active'], name='jobs_job_startup_df8fe0_idx'),
        ),
        migrations.AddIndex(
            model_name='jobapplication',
            index=models.Index(fields=['status', 'applied_at'], name='jobs_jobapp_status_6642d6_idx'),
        ),
        migrations.AddIndex(
            model_name='jobapplication',
            index=models.Index(fields=['user', 'status'], name='jobs_jobapp_user_id_149a27_idx'),
        ),
        migrations.AddIndex(
            model_name='jobapplication',
            index=models.Index(fields=['job', 'status'], name='jobs_jobapp_job_id_08192b_idx'),
        ),
        migrations.AddIndex(
            model_name='jobskill',
            index=models.Index(fields=['skill'], name='jobs_jobski_skill_a6f1bb_idx'),
        ),
        migrations.AddField(
            model_name='applicationnote',
            name='application',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notes', to='jobs.jobapplication'),
        ),
        migrations.AddField(
            model_name='applicationnote',
            name='author',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='jobalert',
            name='industry',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='startups.industry'),
        ),
        migrations.AddField(
            model_name='jobalert',
            name='job_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='jobs.jobtype'),
        ),
        migrations.AddField(
            model_name='jobalert',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='job_alerts', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='jobbookmark',
            name='job',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bookmarks', to='jobs.job'),
        ),
        migrations.AddField(
            model_name='jobbookmark',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='job_bookmarks', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='jobshare',
            name='job',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shares', to='jobs.job'),
        ),
        migrations.AddField(
            model_name='jobshare',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='jobtemplate',
            name='startup',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='job_templates', to='startups.startup'),
        ),
        migrations.AddField(
            model_name='jobview',
            name='job',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='job_views', to='jobs.job'),
        ),
        migrations.AddField(
            model_name='jobview',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddIndex(
            model_name='applicationnote',
            index=models.Index(fields=['application', 'created_at'], name='jobs_applic_applica_fe733b_idx'),
        ),
        migrations.AddIndex(
            model_name='jobalert',
            index=models.Index(fields=['user', 'is_active'], name='jobs_jobale_user_id_82ec0d_idx'),
        ),
        migrations.AddIndex(
            model_name='jobalert',
            index=models.Index(fields=['frequency', 'is_active'], name='jobs_jobale_frequen_7e5ac0_idx'),
        ),
        migrations.AddIndex(
            model_name='jobbookmark',
            index=models.Index(fields=['user', 'created_at'], name='jobs_jobboo_user_id_d9a445_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='jobbookmark',
            unique_together={('job', 'user')},
        ),
        migrations.AddIndex(
            model_name='jobshare',
            index=models.Index(fields=['job', 'shared_at'], name='jobs_jobsha_job_id_b973ea_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='jobtemplate',
            unique_together={('startup', 'name')},
        ),
        migrations.AddIndex(
            model_name='jobview',
            index=models.Index(fields=['job', 'viewed_at'], name='jobs_jobvie_job_id_d75b29_idx'),
        ),
        migrations.AddIndex(
            model_name='jobview',
            index=models.Index(fields=['user', 'viewed_at'], name='jobs_jobvie_user_id_41593d_idx'),
        ),
    ]
