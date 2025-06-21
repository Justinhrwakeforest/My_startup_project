# startup_hub/startup_hub/settings.py - Updated with startup upload features and image support
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-your-secret-key-for-development-only'
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_filters',  # Add this for filtering support
    # Local apps
    'apps.core',
    'apps.users',
    'apps.startups',
    'apps.jobs',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Must be first
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'startup_hub.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Use SQLite for now (no PostgreSQL needed)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files configuration
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files configuration for file uploads
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Create media directory if it doesn't exist
os.makedirs(MEDIA_ROOT, exist_ok=True)
os.makedirs(MEDIA_ROOT / 'startup_covers', exist_ok=True)

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_PERMISSIONS = 0o644

# Image processing settings (requires Pillow)
# Install with: pip install Pillow
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS settings for frontend integration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

CORS_ALLOW_CREDENTIALS = True

# For development only (remove in production)
CORS_ALLOW_ALL_ORIGINS = True

# CSRF settings
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# REST Framework configuration - Updated with django-filter support
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',  # Required for file uploads
    ],
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}

# Make sure you have this
AUTH_USER_MODEL = 'users.User'

# Email Configuration
# For development, use console backend to see emails in console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# For production, uncomment and configure SMTP:
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'your-email@gmail.com'
# EMAIL_HOST_PASSWORD = 'your-app-password'

# Email addresses
DEFAULT_FROM_EMAIL = 'StartupHub <noreply@startuphub.com>'
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Frontend URL for email links
FRONTEND_URL = 'http://localhost:3000'

# Startup submission settings
STARTUP_SUBMISSION_SETTINGS = {
    'AUTO_APPROVE': False,  # Set to True to auto-approve submissions
    'REQUIRE_REVIEW': True,  # Require admin review before publishing
    'MAX_FOUNDERS_PER_STARTUP': 5,
    'MAX_TAGS_PER_STARTUP': 10,
    'MAX_DESCRIPTION_LENGTH': 2000,
    'MIN_DESCRIPTION_LENGTH': 50,
    'FEATURED_REQUIRES_APPROVAL': True,  # Featured status requires admin approval
    'SEND_EMAIL_NOTIFICATIONS': True,  # Send email notifications to admins
    'ALLOW_COVER_IMAGE_UPLOAD': True,  # Allow cover image uploads
    'MAX_COVER_IMAGE_SIZE': 5 * 1024 * 1024,  # 5MB max file size
    'ALLOWED_IMAGE_FORMATS': ['JPEG', 'PNG', 'GIF', 'WEBP'],
}

# Image processing settings
IMAGE_UPLOAD_SETTINGS = {
    'STARTUP_COVER_MAX_SIZE': (1200, 400),  # Max dimensions for cover images
    'STARTUP_COVER_QUALITY': 85,  # JPEG quality (1-100)
    'RESIZE_UPLOADED_IMAGES': True,  # Automatically resize large images
    'GENERATE_THUMBNAILS': False,  # Generate thumbnails (implement if needed)
}

# Caching configuration (optional, for better performance)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 300,  # 5 minutes
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}

# Session configuration
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
SESSION_SAVE_EVERY_REQUEST = True

# Add this to your settings.py LOGGING configuration to fix Unicode issues on Windows

# Update your LOGGING configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'console_safe': {
            # Use ASCII-safe format for Windows console
            'format': '[{levelname}] {asctime} {module} - {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'console_safe',  # Use ASCII-safe formatter
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
            'encoding': 'utf-8',  # Explicitly set UTF-8 encoding for files
        },
        'startup_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'startups.log',
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console', 'file'] if os.path.exists(BASE_DIR / 'logs') else ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'apps.startups': {
            'handlers': ['console', 'startup_file'] if os.path.exists(BASE_DIR / 'logs') else ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# Job Alert Settings
JOB_ALERT_FROM_EMAIL = DEFAULT_FROM_EMAIL
JOB_ALERT_BATCH_SIZE = 100
JOB_ALERT_MAX_JOBS_PER_EMAIL = 10

# API Rate Limiting
API_RATE_LIMITS = {
    'STARTUP_CREATION': '10/hour',  # Max 10 startup submissions per hour per user
    'EDIT_REQUESTS': '20/hour',     # Max 20 edit requests per hour per user
    'IMAGE_UPLOADS': '50/hour',     # Max 50 image uploads per hour per user
    'COMMENTS': '100/hour',         # Max 100 comments per hour per user
}

# Edit Request Settings
EDIT_REQUEST_SETTINGS = {
    'MAX_PENDING_PER_STARTUP': 1,     # Max pending edit requests per startup per user
    'AUTO_APPROVE_ADMIN_EDITS': True,  # Automatically approve edits from admin users
    'NOTIFY_ADMINS_ON_REQUEST': True,  # Send email to admins when edit request is submitted
    'NOTIFY_USER_ON_APPROVAL': True,   # Send email to user when edit is approved/rejected
    'RETENTION_DAYS': 90,              # Keep edit request history for 90 days
}

# Performance settings
DATABASE_CONNECTION_SETTINGS = {
    'CONN_MAX_AGE': 60,  # Database connection timeout
}

# Apply database connection settings
for db_config in DATABASES.values():
    db_config.update(DATABASE_CONNECTION_SETTINGS)

# Security settings for production (commented out for development)
# SECURE_BROWSER_XSS_FILTER = True
# SECURE_CONTENT_TYPE_NOSNIFF = True
# SECURE_HSTS_SECONDS = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True
# X_FRAME_OPTIONS = 'DENY'
# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True

# Development-specific settings
if DEBUG:
    # Enable Django Debug Toolbar if installed
    try:
        import debug_toolbar
        INSTALLED_APPS.append('debug_toolbar')
        MIDDLEWARE.insert(1, 'debug_toolbar.middleware.DebugToolbarMiddleware')
        
        # Configure Debug Toolbar
        DEBUG_TOOLBAR_CONFIG = {
            'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
            'SHOW_COLLAPSED': True,
        }
        
        INTERNAL_IPS = [
            '127.0.0.1',
            'localhost',
        ]
    except ImportError:
        pass

# Environment-specific overrides
try:
    from .local_settings import *
except ImportError:
    pass

# Ensure required directories exist
for directory in [MEDIA_ROOT, STATIC_ROOT, BASE_DIR / 'logs']:
    os.makedirs(directory, exist_ok=True)
