import os

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.wsgi import get_wsgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lab_booking.settings")
if settings.LAB_BOOKING_DB_MODE != "runtime":
    raise ImproperlyConfigured("WSGI 仅允许 LAB_BOOKING_DB_MODE=runtime。")
application = get_wsgi_application()
