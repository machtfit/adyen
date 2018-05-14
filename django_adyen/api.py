# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.conf import settings
from django.core.urlresolvers import reverse

import adyen.api as adyen_api

from .backends import get_backend
from .models import Notification, Payment, Result


def create_payment(order_number, *args, **kwargs):
    merchant_reference = ("{order_number}-{{payment_id}}"
                          .format(order_number=order_number))

    payment = adyen_api.create_payment(get_backend(), merchant_reference,
                                       *args, **kwargs)

    if not payment:
        return

    if hasattr(settings, 'ADYEN_COUNTRY_CODE'):
        payment.country_code = settings.ADYEN_COUNTRY_CODE
    if hasattr(settings, 'ADYEN_SHOPPER_LOCALE'):
        payment.shopper_locale = settings.ADYEN_SHOPPER_LOCALE

    return payment


def pay(payment, build_absolute_uri=None, force_multi=False):
    if not payment.res_url:
        if not build_absolute_uri:
            raise Exception("Pass build_absolute_uri if you don't set "
                                "res_url on the payment yourself.")

        payment.res_url = build_absolute_uri(
            reverse('django-adyen:payment-result'))

    Payment.objects.persist(payment)

    return adyen_api.pay(payment, force_multi=force_multi)


def mock_payment_result_params(*args, **kwargs):
    return adyen_api.mock_payment_result_params(get_backend(), *args, **kwargs)


def mock_payment_result_url(*args, **kwargs):
    return adyen_api.mock_payment_result_url(get_backend(), *args, **kwargs)


def get_payment_result(*args, **kwargs):
    payment_result = adyen_api.get_payment_result(get_backend(),
                                                  *args, **kwargs)
    Result.objects.persist(payment_result)
    return payment_result


def get_payment_notification(*args, **kwargs):
    notification = adyen_api.get_payment_notification(*args, **kwargs)
    return Notification.objects.persist(notification)


def get_unhandled_notifications():
    return Notification.objects.originals().filter(handled=False)
