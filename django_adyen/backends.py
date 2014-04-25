# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from zope.dottedname.resolve import resolve

from adyen import Skin, Backend, UnknownSkinCode

from django.conf import settings


def get_backend():
    try:
        backend_class = settings.ADYEN_BACKEND
    except AttributeError:
        backend_class = 'django_adyen.backends.SimpleSettingsBackend'
    return resolve(backend_class)()


class SimpleSettingsBackend(Backend):
    def get_skin(self):
        is_live = getattr(settings, 'ADYEN_IS_LIVE', False)
        payment_flow = getattr(settings, 'ADYEN_PAYMENT_FLOW', 'onepage')
        return Skin(settings.ADYEN_MERCHANT_ACCOUNT,
                    settings.ADYEN_SKIN_CODE,
                    settings.ADYEN_SKIN_SECRET,
                    is_live=is_live,
                    payment_flow=payment_flow)

    def get_skin_by_code(self, skin_code):
        if settings.ADYEN_SKIN_CODE != skin_code:
            raise UnknownSkinCode
        return self.get_skin()

    def get_notification_credentials(self):
        return (settings.ADYEN_NOTIFICATION_USER,
                settings.ADYEN_NOTIFICATION_PASSWORD)

    def get_payment_params(self):
        params = {}
        if hasattr(settings, 'ADYEN_COUNTRY_CODE'):
            params['country_code'] = settings.ADYEN_COUNTRY_CODE
        if hasattr(settings, 'ADYEN_SHOPPER_LOCALE'):
            params['shopper_locale'] = settings.ADYEN_SHOPPER_LOCALE

        return params
