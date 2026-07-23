from pathlib import Path
import os
import cloudinary
from decouple import config, Csv

# BASE_DIR → Ruta raíz del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Clave secreta (se lee de la variable de entorno SECRET_KEY, ver .env.example)
SECRET_KEY = config('SECRET_KEY')

# Debug solo para desarrollo (en producción debe ser False)
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# -------------------------
# APLICACIONES INSTALADAS
# -------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary_storage',  # <-- AÑADIR ESTO (antes de staticfiles)
    'cloudinary',          # <-- AÑADIR ESTO
    'webApp',  # 👈 Registramos nuestra app principal
]

# -------------------------
# MIDDLEWARE
# -------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'IngSoftware.urls'

# -------------------------
# TEMPLATES
# -------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'webApp', 'templates')],  # 👈 Carpeta templates
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.static',
                
                # --- LÍNEA AÑADIDA ---
                'webApp.context_processors.global_notificaciones', # 👈 Activa las notificaciones globales
                # ---------------------
            ],
        },
    },
]

WSGI_APPLICATION = 'IngSoftware.wsgi.application'

# -------------------------
# BASE DE DATOS
# -------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='3306'),
    }
}

# -------------------------
# VALIDADORES DE PASSWORD
# -------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# -------------------------
# IDIOMA Y ZONA HORARIA
# -------------------------
LANGUAGE_CODE = 'es'   # 👈 Español
TIME_ZONE = 'America/Lima'  # 👈 Perú

USE_I18N = True
USE_TZ = True


# -------------------------
# CONFIGURACIÓN DE CLOUDINARY
# -------------------------
# (Se leen de variables de entorno, ver .env.example)
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': config('CLOUDINARY_API_KEY'),
    'API_SECRET': config('CLOUDINARY_API_SECRET'),
}

# === AÑADE ESTE BLOQUE ADICIONAL ===
# Configuración directa de la librería base de Cloudinary
cloudinary.config(
    cloud_name = CLOUDINARY_STORAGE['CLOUD_NAME'],
    api_key = CLOUDINARY_STORAGE['API_KEY'],
    api_secret = CLOUDINARY_STORAGE['API_SECRET'],
    secure = True
)
# ===================================

# Configura Django para usar Cloudinary para archivos subidos (media)
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# -------------------------
# ARCHIVOS ESTÁTICOS
# -------------------------
STATIC_URL = '/static/'  # URL para acceder a los archivos estáticos

# 👇 Indicamos dónde están nuestros archivos estáticos
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'webApp', 'static')]

# Carpeta donde Django recopila todos los archivos estáticos al hacer collectstatic
# (en producción se define vía variable de entorno; en local usa una carpeta del proyecto)
STATIC_ROOT = config('STATIC_ROOT', default=os.path.join(BASE_DIR, 'static_collected'))

# -------------------------
# LOGIN
# -------------------------
LOGIN_URL = '/'  # Cuando implementemos login, redirige aquí

# -------------------------
# CLAVE PARA IDs AUTOMÁTICOS
# -------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

