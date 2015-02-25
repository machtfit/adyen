# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from decimal import Decimal
import logging

from django.core.urlresolvers import reverse

import django_adyen.api as django_adyen_api
from django_adyen.models import Payment

from oscar.core.loading import get_class, get_model

log = logging.getLogger(__name__)

EventHandler = get_class('order.processing', 'EventHandler')
Order = get_model('order', 'Order')
PaymentEvent = get_class('payment.api', 'PaymentEvent')
PaymentEventType = get_model('order', 'PaymentEventType')
PaymentSource = get_class('payment.api', 'PaymentSource')


PAYMENT_METHOD_NAMES = {
    'amex': 'American Express',
    'bankTransfer_DE': 'Überweisung',
    'bankTransfer_IBAN': 'SEPA-Überweisung',
    'directEbanking': 'Sofortüberweisung',
    'elv': 'Lastschrift',
    'giropay': 'GiroPay',
    'maestro': 'Maestro',
    'mc': 'MasterCard',
    'sepadirectdebit': 'SEPA-Lastschrift',
    'visa': 'VISA'
}


class PaymentFailed(StandardError):
    pass


create_payment = django_adyen_api.create_payment


def pay(payment, basket_id, build_absolute_uri=None):
    if not payment.res_url:
        if not build_absolute_uri:
            raise StandardError("Pass build_absolute_uri if you don't set "
                                "res_url on the payment yourself.")

        payment.res_url = build_absolute_uri(
            reverse('oscar-adyen:payment-result',
                    kwargs={'basket_id': basket_id}))

    return django_adyen_api.pay(payment)

mock_payment_result_params = django_adyen_api.mock_payment_result_params

mock_payment_result_url = django_adyen_api.mock_payment_result_url

get_payment_result = django_adyen_api.get_payment_result


def handle_payment_result(payment_result):
    if payment_result.auth_result not in ['AUTHORISED', 'PENDING']:
        raise PaymentFailed(payment_result)

    payment = Payment.objects.get(
        merchant_reference=payment_result.merchant_reference)

    amount = Decimal(payment.payment_amount) / 100

    payment_source = PaymentSource(
        type_code='adyen-{}'.format(payment_result.payment_method),
        type_name=PAYMENT_METHOD_NAMES.get(
            payment_result.payment_method,
            payment_result.payment_method),
        currency=payment.currency_code,
        amount_allocated=amount,
        amount_debited=amount,
        reference=payment_result.psp_reference)

    # TODO: reflect the various payment statuses (see Merchant Manual,
    # p. 4) in Source, with Transactions and maybe Events.
    payment_event = PaymentEvent(
        type_name="Adyen - {}".format(payment_result.auth_result),
        amount=amount,
        reference=payment_result.psp_reference)

    return [payment_source], [payment_event]


get_payment_notification = django_adyen_api.get_payment_notification

get_unhandled_notifications = django_adyen_api.get_unhandled_notifications


def handle_notifications():
    return len(filter(None, map(handle_notification,
                                get_unhandled_notifications())))


def handle_notification(notification):
    log.info('Processing adyen notification {}'.format(notification))

    try:
        order = Order.objects.get(number=notification.order_number)
    except Order.DoesNotExist:
        log.error("Couldn't find order '{order}' for notification #{id} {s}"
                  .format(order=notification.order_number, id=notification.pk,
                          s=notification))
        return

    event_type, __ = PaymentEventType.objects.get_or_create(
        name="Adyen - {}".format(notification.event_code))

    EventHandler().handle_payment_event(
        order=order,
        event_type=event_type,
        amount=Decimal(notification.value) / 100,
        lines=order.lines.all(),
        quantities=[line.quantity for line in order.lines.all()],
        reference=notification.psp_reference,
        notification=notification)

    notification.handled = True
    notification.save()

    return notification
