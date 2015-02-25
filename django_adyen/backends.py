# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from zope.dottedname.resolve import resolve

from adyen import Backend

from django.conf import settings


def get_backend():
    try:
        backend_class = settings.ADYEN_BACKEND
    except AttributeError:
        backend_class = 'django_adyen.backends.SimpleSettingsBackend'
    return resolve(backend_class)()


class SimpleSettingsBackend(Backend):
    def __init__(self):
        super(SimpleSettingsBackend, self).__init__(
            settings.ADYEN_MERCHANT_ACCOUNT,
            settings.ADYEN_SKIN_CODE,
            settings.ADYEN_SKIN_SECRET)
        self.is_live = getattr(settings, 'ADYEN_IS_LIVE', False)
        self.payment_flow = getattr(settings, 'ADYEN_PAYMENT_FLOW', 'onepage')

    def get_notification_credentials(self):
        return (settings.ADYEN_NOTIFICATION_USER,
                settings.ADYEN_NOTIFICATION_PASSWORD)
