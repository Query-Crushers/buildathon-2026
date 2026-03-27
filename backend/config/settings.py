"""
Django settings for the project.
"""
import mimetypes
from pathlib import Path

import environ

# Ensure correct MIME types for static files (WhiteNoise needs this on some systems)
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("text/html", ".html")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize environ
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
    CORS_ALLOWED_ORIGINS=(list, ['http://localhost:5173', 'http://localhost:8081']),
)

# Read .env file from project root (parent of backend/)
environ.Env.read_env(BASE_DIR.parent / '.env')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('DJANGO_SECRET_KEY', default='django-insecure-change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DJANGO_DEBUG', default=True)

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[
    "brave-star-1493.sandbox.cayu.app",
    "*.sandbox.cayu.app",
    "*.nip.io",
    "localhost",
    "127.0.0.1",
])

# Application definition
INSTALLED_APPS = [
    # Local apps (must come first for custom User)
    'apps.users',
    'apps.accounts',
    'apps.switchguard',
    # Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
]

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Authentication backends (enable Cayu OAuth)
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'apps.accounts.backends.CayuOAuthBackend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'apps.monitoring.middleware.CayuExceptionReporterMiddleware',
]
# Note: XFrameOptionsMiddleware omitted - Cayu apps are designed for iframe embedding

ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database
DATABASES = {
    'default': env.db('DATABASE_URL', default='postgresql://postgres:postgres@localhost:5433/app_dev')
}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# =============================================================================
# File Storage (S3 for production, local for development)
# =============================================================================
USE_S3 = env.bool('USE_S3', default=False)

if USE_S3:
    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }
    AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
else:
    MEDIA_ROOT = BASE_DIR / 'media'
    MEDIA_URL = '/media/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS
CORS_ALLOWED_ORIGINS = env('CORS_ALLOWED_ORIGINS')
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^https://[\w-]+\.cloudfront\.net$',  # CloudFront distributions
    r'^https://[\w-]+\.nip\.io$',  # nip.io for IP-based access
]

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
}

# JWT settings
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Interswitch credentials
INTERSWITCH_CLIENT_ID = env('INTERSWITCH_CLIENT_ID', default='IKIAED8B08389627550ED24650DA254F13B8165402F7')
INTERSWITCH_SECRET_KEY = env('INTERSWITCH_SECRET_KEY', default='8C4883943D3213B7B2EB2A8A7EBA0070C6D6014D')

# SendGrid
SENDGRID_API_KEY = env('SENDGRID_API_KEY', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@switchguard.com')
COMPLIANCE_EMAIL = env('COMPLIANCE_EMAIL', default='')

# drf-spectacular settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'API',
    'DESCRIPTION': 'API documentation',
    'VERSION': '1.0.0',
}

# Logging - write Django logs to backend/logs/ directory
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# =============================================================================
# Cayu OAuth Configuration ("Login with Cayu")
# =============================================================================
# These are auto-provisioned by Cayu when a project is created
CAYU_OAUTH_CLIENT_ID = env('CAYU_OAUTH_CLIENT_ID', default='')
CAYU_OAUTH_CLIENT_SECRET = env('CAYU_OAUTH_CLIENT_SECRET', default='')
CAYU_OAUTH_AUTHORIZE_URL = env('CAYU_OAUTH_AUTHORIZE_URL', default='')
CAYU_OAUTH_TOKEN_URL = env('CAYU_OAUTH_TOKEN_URL', default='')
CAYU_OAUTH_USERINFO_URL = env('CAYU_OAUTH_USERINFO_URL', default='')
APP_DOMAIN = env('APP_DOMAIN', default='')

# Exception reporting (live only — env vars set in ECS task definition)
CAYU_ERROR_REPORTING_URL = env('CAYU_ERROR_REPORTING_URL', default='')
CAYU_ERROR_REPORTING_TOKEN = env('CAYU_ERROR_REPORTING_TOKEN', default='')

# =============================================================================
# Cookie Settings for Cayu iframe embedding
# =============================================================================
# When running in Cayu's sandbox (embedded in iframe on cayu.ai), cookies need
# SameSite=None to work in the third-party iframe context.
# For standalone deployments, Django's default SameSite=Lax is more secure.
if CAYU_OAUTH_CLIENT_ID:
    SESSION_COOKIE_SAMESITE = 'None'
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SAMESITE = 'None'
    CSRF_COOKIE_SECURE = True

# =============================================================================
# Celery Configuration (Redis broker)
# =============================================================================
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default=CELERY_BROKER_URL)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# =============================================================================
# Development CSRF Settings (Vite dev server)
# =============================================================================
if DEBUG:
    CSRF_TRUSTED_ORIGINS = [
        'http://localhost:5173',
        'http://127.0.0.1:5173',
    ]


# =============================================================================
# Production Security Settings (ECS Fargate / AWS)
# =============================================================================
if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=False)
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    CSRF_TRUSTED_ORIGINS = [
        'https://*.sandbox.cayu.app',  # Sandbox dev instances
        'https://*.cloudfront.net',
        'https://*.amazonaws.com',
    ]
