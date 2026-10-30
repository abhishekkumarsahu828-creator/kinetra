"""KINETRA settings. PostgreSQL required for deployed instances."""
from pathlib import Path
import os
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


DEBUG = os.getenv('DJANGO_DEBUG', 'false').lower() == 'true'
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = '#(px=f1)n!18c3m3#dsyprz(i@p5(ch@8zpqqa9_oe46(&@k(k'
    else:
        raise ImproperlyConfigured('DJANGO_SECRET_KEY must be set in production')
if not DEBUG and (len(SECRET_KEY) < 32 or SECRET_KEY.startswith('REPLACE_')):
    raise ImproperlyConfigured('Set a unique strong DJANGO_SECRET_KEY before deployment')
ALLOWED_HOSTS = [h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if h.strip()]
CSRF_TRUSTED_ORIGINS = [v.strip() for v in os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS','').split(',') if v.strip()]
INSTALLED_APPS = [
    'django.contrib.admin','django.contrib.auth','django.contrib.contenttypes',
    'django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles',
    'exchange',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'kinetra.urls'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],
             'APP_DIRS':True,'OPTIONS':{'context_processors':[
                 'django.template.context_processors.debug','django.template.context_processors.request',
                 'django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages',
                 'exchange.context.site_context',
             ]}}]
WSGI_APPLICATION = 'kinetra.wsgi.application'

if os.getenv('DATABASE_URL'):
    # Optional DATABASE_URL: postgresql://user:password@host:5432/database
    from urllib.parse import urlparse, unquote
    url = urlparse(os.environ['DATABASE_URL'])
    if url.scheme not in ('postgres', 'postgresql'):
        raise ImproperlyConfigured('DATABASE_URL must be PostgreSQL')
    DATABASES = {'default': {'ENGINE':'django.db.backends.postgresql',
        'NAME':unquote(url.path.lstrip('/')), 'USER':unquote(url.username or ''),
        'PASSWORD':unquote(url.password or ''), 'HOST':url.hostname, 'PORT':url.port or 5432,
        'CONN_MAX_AGE':60, 'OPTIONS':{'connect_timeout':10}}}
elif DEBUG and os.getenv('ALLOW_SQLITE_DEV') == '1':
    # Dev-only smoke tests: does not demonstrate PostgreSQL transaction behaviour.
    DATABASES = {'default':{'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'dev.sqlite3'}}
else:
    DATABASES = {'default':{'ENGINE':'django.db.backends.postgresql',
        'NAME':os.getenv('POSTGRES_DB','kinetra'), 'USER':os.getenv('POSTGRES_USER','kinetra'),
        'PASSWORD':os.getenv('POSTGRES_PASSWORD',''), 'HOST':os.getenv('POSTGRES_HOST','localhost'),
        'PORT':os.getenv('POSTGRES_PORT','5432'), 'CONN_MAX_AGE':60}}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':10}},
    {'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LOGIN_URL='login'
LOGIN_REDIRECT_URL='dashboard'
LOGOUT_REDIRECT_URL='home'
LANGUAGE_CODE='en-us'
TIME_ZONE='Asia/Kolkata'
USE_I18N=True
USE_TZ=True
STATIC_URL='static/'
STATIC_ROOT=BASE_DIR/'staticfiles'
STATICFILES_DIRS=[BASE_DIR/'static']
STORAGES={'staticfiles':{'BACKEND':'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
MEDIA_URL='media/'
MEDIA_ROOT=BASE_DIR/'media'
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
EMAIL_BACKEND=os.getenv('EMAIL_BACKEND','django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL=os.getenv('DEFAULT_FROM_EMAIL','KINETRA <no-reply@example.invalid>')
EMAIL_HOST=os.getenv('EMAIL_HOST','')
EMAIL_PORT=int(os.getenv('EMAIL_PORT','587'))
EMAIL_HOST_USER=os.getenv('EMAIL_HOST_USER','')
EMAIL_HOST_PASSWORD=os.getenv('EMAIL_HOST_PASSWORD','')
EMAIL_USE_TLS=os.getenv('EMAIL_USE_TLS','true').lower() == 'true'
SECURE_SSL_REDIRECT=not DEBUG and os.getenv('SECURE_SSL_REDIRECT','true').lower() == 'true'
SESSION_COOKIE_SECURE=not DEBUG
CSRF_COOKIE_SECURE=not DEBUG
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE='Lax'
CSRF_COOKIE_SAMESITE='Lax'
SECURE_HSTS_SECONDS=31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS=not DEBUG and os.getenv('HSTS_INCLUDE_SUBDOMAINS','false').lower()=='true'
SECURE_HSTS_PRELOAD=False
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_REFERRER_POLICY='strict-origin-when-cross-origin'
X_FRAME_OPTIONS='DENY'
SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https') if os.getenv('TRUST_PROXY_SSL_HEADER')=='true' else None
FILE_UPLOAD_MAX_MEMORY_SIZE=5*1024*1024
DATA_UPLOAD_MAX_MEMORY_SIZE=12*1024*1024
SESSION_COOKIE_AGE=60*60*12

# Private evidence files are served only via role-checked views, never by nginx /media/.
LOGGING={'version':1,'disable_existing_loggers':False,'handlers':{'console':{'class':'logging.StreamHandler'}},
         'root':{'handlers':['console'],'level':os.getenv('LOG_LEVEL','INFO')}}
