# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.apps import AppConfig
from django.conf import settings


class OscarAdyenConfig(AppConfig):
    name = 'oscar_adyen'

    def ready(self):
        if settings.ADYEN_REGISTER_CELERY_TASK:
            from . import tasks  # noqa
