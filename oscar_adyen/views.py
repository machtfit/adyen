# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from decimal import Decimal
import logging

import six

from django.contrib import messages
from django.utils.translation import ugettext as _

from django_adyen.models import Payment
import django_adyen.views as django_views

from oscar.apps.checkout import signals
from oscar.core.loading import get_model, get_class

log = logging.getLogger(__name__)

Source = get_model('payment', 'Source')
SourceType = get_model('payment', 'SourceType')
UnableToPlaceOrder = get_class('order.exceptions', 'UnableToPlaceOrder')
EventHandler = get_class('order.processing', 'EventHandler')
Order = get_model('order', 'Order')
PaymentEventType = get_model('order', 'PaymentEventType')
CheckoutFlow = get_class('checkout.flow', 'CheckoutFlow')


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


class PaymentResultView(CheckoutFlow, django_views.PaymentResultView):
    def handle_payment_result(self, payment_result):
        if payment_result.auth_result == 'ERROR':
            self.restore_frozen_basket()
            messages.warning(self.request, _('Payment failed'))
            return self.checkout_failed()

        if payment_result.auth_result == 'CANCELLED':
            self.restore_frozen_basket()
            messages.warning(self.request, _('Payment cancelled'))
            return self.checkout_failed()

        if payment_result.auth_result == 'REFUSED':
            self.restore_frozen_basket()
            messages.error(self.request, _('Payment refused'))
            return self.checkout_failed()

        if payment_result.auth_result in ['AUTHORISED', 'PENDING']:
            self.restore_frozen_basket()

            payment = Payment.objects.get(
                merchant_reference=payment_result.merchant_reference)

            # Record payment source and event
            source_type, _created = SourceType.objects.get_or_create(
                code='adyen-{}'.format(payment_result.payment_method),
                defaults={'name': PAYMENT_METHOD_NAMES.get(
                    payment_result.payment_method,
                    payment_result.payment_method)})
            amount = Decimal(payment.payment_amount)/100

            # TODO: reflect the various payment statuses (see Merchant Manual,
            # p. 4) in Source, with Transactions and maybe Events.
            source = Source(source_type=source_type,
                            currency=payment.currency_code,
                            amount_allocated=amount,
                            amount_debited=amount,
                            reference=payment_result.psp_reference)
            self.add_payment_source(source)

            event_type_name = "Adyen - {}".format(payment_result.auth_result)
            self.add_payment_event(event_type_name, amount,
                                   reference=payment_result.psp_reference)

            messages.success(self.request, _('Payment accepted'))

            order_number = self.checkout_session.get_order_number()

            signals.post_payment.send_robust(sender=self, view=self)

            # If all is ok with payment, try and place order
            log.info("Order #%s: payment successful, placing order",
                     order_number)

            try:
                kwargs = self.build_submission()
                del kwargs['payment_kwargs']
                order_kwargs = kwargs.pop('order_kwargs')
                kwargs.update(order_kwargs)
                self.handle_order_placement(order_number, **kwargs)
                return self.checkout_successful()
            except UnableToPlaceOrder as e:
                # It's possible that something will go wrong while trying to
                # actually place an order.  Not a good situation to be in as a
                # payment transaction may already have taken place, but needs
                # to be handled gracefully.
                msg = six.text_type(e)
                log.error("Order #%s: unable to place order - %s",
                          order_number, msg, exc_info=True)
                self.restore_frozen_basket()
                messages.error(self.request, msg)
                return self.checkout_failed()


payment_result = PaymentResultView.as_view()


class NotificationView(django_views.NotificationView):
    def handle_notification(self, notification):
        try:
            order_number, payment_id \
                = map(int, notification.merchant_reference.split('-'))
            order = Order.objects.get(number=order_number)
        except (Order.DoesNotExist, ValueError):
            # Don't send accepted response to have the notification be sent
            # again. This should really be handled on our side with a deferred
            # task runner or something similar.
            log.error("Couldn't find order for notification #{id} {s}"
                      .format(id=notification.pk, s=notification))
        else:
            event_type, __ = PaymentEventType.objects.get_or_create(
                name="Adyen - {}".format(notification.event_code))

            EventHandler().create_payment_event(
                order=order,
                event_type=event_type,
                amount=Decimal(notification.value) / 100,
                reference=notification.psp_reference)
        return super(NotificationView, self).handle_notification(notification)


notification = NotificationView.as_view()
