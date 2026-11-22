import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


def required_setting(name):
    value = os.environ.get(name)
    if not value or not value.strip():
        raise ImproperlyConfigured(f"缺少环境变量 {name}。请按 README 配置本机环境。")
    return value


DATABASE_TARGETS = {
    "runtime": ("lab_booking", "lab_booking_app"),
    "migration": ("lab_booking", "lab_booking_migrator"),
    "test": ("test_lab_booking", "lab_booking_test"),
}
LAB_BOOKING_DB_MODE = required_setting("LAB_BOOKING_DB_MODE")
if LAB_BOOKING_DB_MODE not in DATABASE_TARGETS:
    raise ImproperlyConfigured("LAB_BOOKING_DB_MODE 必须为 runtime、migration 或 test。")

database_name, database_user = DATABASE_TARGETS[LAB_BOOKING_DB_MODE]
passfile = Path(required_setting("PGPASSFILE"))
if not passfile.is_absolute() or not passfile.is_file():
    raise ImproperlyConfigured("PGPASSFILE 必须指向本机受保护密码文件的绝对路径。")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": database_name,
        "USER": database_user,
        "HOST": "127.0.0.1",
        "PORT": "5433",
        "OPTIONS": {"passfile": str(passfile)},
        "TEST": {"NAME": "test_lab_booking"},
    },
}

SECRET_KEY = required_setting("LAB_BOOKING_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "accounts",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
    },
]
ROOT_URLCONF = "lab_booking.urls"
WSGI_APPLICATION = "lab_booking.wsgi.application"

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]
SESSION_ENGINE = "django.contrib.sessions.backends.db"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "identity"
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
