from django.conf import settings
from django.core.management.base import CommandError
from django.core.management.commands.runserver import Command as RunserverCommand


class Command(RunserverCommand):
    def execute(self, *args, **options):
        if settings.LAB_BOOKING_DB_MODE != "runtime":
            raise CommandError("runserver 仅允许 LAB_BOOKING_DB_MODE=runtime。")
        return super().execute(*args, **options)
