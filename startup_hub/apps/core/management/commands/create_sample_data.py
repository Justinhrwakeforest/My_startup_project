# apps/core/management/commands/create_sample_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.startups.models import Industry, Startup, StartupFounder, StartupTag
from apps.jobs.models import JobType, Job, JobSkill

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample data for development'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')

        # Create industries
        industries = [
            {'name': 'FinTech', 'description': 'Financial Technology', 'icon': '💰'},
            {'name': 'HealthTech', 'description': 'Healthcare Technology', 'icon': '🏥'},
            {'name': 'EdTech', 'description': 'Education Technology', 'icon': '📚'},
            {'name': 'E-commerce', 'description': 'Electronic Commerce', 'icon': '🛒'},
            {'name': 'AI/ML', 'description': 'Artificial Intelligence & Machine Learning', 'icon': '🤖'},
            {'name': 'GreenTech', 'description': 'Green Technology', 'icon': '🌱'},
        ]

        for industry_data in industries:
            industry, created = Industry.objects.get_or_create(
                name=industry_data['name'],
                defaults=industry_data
            )
            if created:
                self.stdout.write(f'Created industry: {industry.name}')

        # Create job types
        job_types = ['Full-time', 'Part-time', 'Contract', 'Internship', 'Freelance']
        for job_type_name in job_types:
            job_type, created = JobType.objects.get_or_create(name=job_type_name)
            if created:
                self.stdout.write(f'Created job type: {job_type.name}')

        # Create sample startups
        startups_data = [
            {
                'name': 'PayFlow',
                'description': 'Revolutionary payment processing platform for modern businesses.',
                'industry': 'FinTech',
                'location': 'San Francisco, CA',
                'website': 'https://payflow.com',
                'logo': '💳',
                'funding_amount': '$5M',
                'valuation': '$50M',
                'employee_count': 25,
                'founded_year': 2020,
                'is_featured': True,
                'revenue': '$2M ARR',
                'user_count': '10K+',
                'growth_rate': '150%',
                'founders': [
                    {'name': 'Sarah Chen', 'title': 'CEO & Co-Founder', 'bio': 'Former PayPal engineer with 10 years experience'},
                    {'name': 'Mike Rodriguez', 'title': 'CTO & Co-Founder', 'bio': 'Ex-Stripe technical lead'},
                ],
                'tags': ['payments', 'fintech', 'B2B', 'SaaS'],
                'jobs': [
                    {
                        'title': 'Senior Backend Engineer',
                        'description': 'Build scalable payment processing systems.',
                        'location': 'San Francisco, CA',
                        'job_type': 'Full-time',
                        'salary_range': '$120k - $180k',
                        'is_remote': True,
                        'experience_level': 'senior',
                        'skills': ['Python', 'Django', 'PostgreSQL', 'Redis'],
                    }
                ]
            },
            {
                'name': 'HealthAI',
                'description': 'AI-powered diagnostic tools for healthcare professionals.',
                'industry': 'HealthTech',
                'location': 'Boston, MA',
                'website': 'https://healthai.com',
                'logo': '🏥',
                'funding_amount': '$15M',
                'valuation': '$100M',
                'employee_count': 45,
                'founded_year': 2019,
                'is_featured': True,
                'revenue': '$5M ARR',
                'user_count': '1K+',
                'growth_rate': '200%',
                'founders': [
                    {'name': 'Dr. James Wilson', 'title': 'CEO & Co-Founder', 'bio': 'Harvard Medical School graduate'},
                ],
                'tags': ['healthcare', 'AI', 'diagnostics', 'B2B'],
                'jobs': [
                    {
                        'title': 'Machine Learning Engineer',
                        'description': 'Develop AI models for medical diagnosis.',
                        'location': 'Boston, MA',
                        'job_type': 'Full-time',
                        'salary_range': '$130k - $200k',
                        'is_remote': False,
                        'experience_level': 'senior',
                        'skills': ['Python', 'TensorFlow', 'PyTorch', 'Medical Imaging'],
                    }
                ]
            },
            {
                'name': 'LearnSpace',
                'description': 'Virtual learning platform for remote education.',
                'industry': 'EdTech',
                'location': 'Austin, TX',
                'website': 'https://learnspace.com',
                'logo': '📚',
                'funding_amount': '$3M',
                'valuation': '$25M',
                'employee_count': 15,
                'founded_year': 2021,
                'is_featured': False,
                'revenue': '$1M ARR',
                'user_count': '50K+',
                'growth_rate': '300%',
                'founders': [
                    {'name': 'Emily Davis', 'title': 'CEO & Founder', 'bio': 'Former teacher turned entrepreneur'},
                ],
                'tags': ['education', 'virtual learning', 'B2C', 'SaaS'],
                'jobs': [
                    {
                        'title': 'Frontend Developer',
                        'description': 'Create engaging user interfaces for learning platform.',
                        'location': 'Austin, TX',
                        'job_type': 'Full-time',
                        'salary_range': '$80k - $120k',
                        'is_remote': True,
                        'experience_level': 'mid',
                        'skills': ['React', 'TypeScript', 'CSS', 'JavaScript'],
                    }
                ]
            }
        ]

        for startup_data in startups_data:
            industry = Industry.objects.get(name=startup_data['industry'])
            
            startup, created = Startup.objects.get_or_create(
                name=startup_data['name'],
                defaults={
                    'description': startup_data['description'],
                    'industry': industry,
                    'location': startup_data['location'],
                    'website': startup_data['website'],
                    'logo': startup_data['logo'],
                    'funding_amount': startup_data['funding_amount'],
                    'valuation': startup_data['valuation'],
                    'employee_count': startup_data['employee_count'],
                    'founded_year': startup_data['founded_year'],
                    'is_featured': startup_data['is_featured'],
                    'revenue': startup_data['revenue'],
                    'user_count': startup_data['user_count'],
                    'growth_rate': startup_data['growth_rate'],
                }
            )
            
            if created:
                self.stdout.write(f'Created startup: {startup.name}')
                
                # Create founders
                for founder_data in startup_data['founders']:
                    StartupFounder.objects.create(
                        startup=startup,
                        name=founder_data['name'],
                        title=founder_data['title'],
                        bio=founder_data['bio']
                    )
                
                # Create tags
                for tag_name in startup_data['tags']:
                    StartupTag.objects.create(startup=startup, tag=tag_name)
                
                # Create jobs
                for job_data in startup_data['jobs']:
                    job_type = JobType.objects.get(name=job_data['job_type'])
                    
                    job = Job.objects.create(
                        startup=startup,
                        title=job_data['title'],
                        description=job_data['description'],
                        location=job_data['location'],
                        job_type=job_type,
                        salary_range=job_data['salary_range'],
                        is_remote=job_data['is_remote'],
                        experience_level=job_data['experience_level']
                    )
                    
                    # Create job skills
                    for skill in job_data['skills']:
                        JobSkill.objects.create(job=job, skill=skill)

        # Create sample user
        if not User.objects.filter(email='demo@example.com').exists():
            user = User.objects.create_user(
                username='demouser',
                email='demo@example.com',
                password='demopass123',
                first_name='Demo',
                last_name='User',
                bio='Sample user for testing the platform',
                location='San Francisco, CA'
            )
            self.stdout.write(f'Created demo user: {user.email}')

        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))