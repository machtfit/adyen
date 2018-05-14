# -*- coding: utf-8 -*-

from django import template

from django_adyen.models import Notification, Result

register = template.Library()


@register.simple_tag()
def adyen_link(psp_reference):
    try:
        result = Result.objects.get(psp_reference=psp_reference)
        is_live = result.live
    except Result.DoesNotExist:
        try:
            notification = Notification.objects.get(
                psp_reference=psp_reference)
            is_live = notification.live
            if notification.original_reference:
                psp_reference = notification.original_reference
        except Notification.DoesNotExist:
            is_live = None

    if is_live is None:
        return ""

    return ("https://ca-{test_or_live}.adyen.com"
            "/ca/ca/accounts/showTxPayment.shtml"
            "?pspReference={psp_reference}&txType=Payment"
            .format(test_or_live=is_live and "live" or "test",
                    psp_reference=psp_reference))
