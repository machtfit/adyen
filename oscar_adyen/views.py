# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from decimal import Decimal
import logging

import six

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.utils.translation import ugettext as _

from django_adyen.models import Payment
import django_adyen.views as django_views

from oscar.apps.checkout.mixins import OrderPlacementMixin
from oscar.apps.checkout import signals
import oscar.apps.checkout.views as orig
from oscar.apps.payment.exceptions import RedirectRequired
from oscar.core.loading import get_model, get_class

log = logging.getLogger(__name__)

Source = get_model('payment', 'Source')
SourceType = get_model('payment', 'SourceType')
PaymentError = get_class('payment.exceptions', 'PaymentError')
UnableToPlaceOrder = get_class('order.exceptions', 'UnableToPlaceOrder')
EventHandler = get_class('order.processing', 'EventHandler')
Order = get_model('order', 'Order')
PaymentEventType = get_model('order', 'PaymentEventType')


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


class PaymentDetailsView(django_views.PaymentRequestMixin,
                         orig.PaymentDetailsView):
    def prepare_payment_request(self, payment):
        super(PaymentDetailsView, self).prepare_payment_request(payment)
        payment.res_url = self.request.build_absolute_uri(
            reverse('oscar-adyen:payment-result'))
        # backend.get_payment_params()

    def handle_payment(self, order_number, total, **kwargs):
        ref = "{order_number}-{{payment_id}}".format(order_number=order_number)
        # TODO: use correct subunit fraction depending on the currency
        # http://en.wikipedia.org/wiki/List_of_circulating_currencies
        response = self.initiate_payment(ref, int(total.incl_tax * 100),
                                         total.currency)
        raise RedirectRequired(response.url)


class PaymentResultView(OrderPlacementMixin, django_views.PaymentResultView):
    def handle_payment_result(self, payment_result):
        if payment_result.auth_result == 'ERROR':
            self.restore_frozen_basket()
            messages.warning(self.request, _('Payment failed'))
            return HttpResponseRedirect(reverse('checkout:preview'))

        if payment_result.auth_result == 'CANCELLED':
            self.restore_frozen_basket()
            messages.warning(self.request, _('Payment cancelled'))
            return HttpResponseRedirect(reverse('checkout:preview'))

        if payment_result.auth_result == 'REFUSED':
            self.restore_frozen_basket()
            messages.error(self.request, _('Payment refused'))
            return HttpResponseRedirect(reverse('checkout:preview'))

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

            self.add_payment_event(payment_result.auth_result, amount,
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
                return self.handle_order_placement(order_number, **kwargs)
            except UnableToPlaceOrder as e:
                # It's possible that something will go wrong while trying to
                # actually place an order.  Not a good situation to be in as a
                # payment transaction may already have taken place, but needs
                # to be handled gracefully.
                msg = six.text_type(e)
                log.error("Order #%s: unable to place order - %s",
                          order_number, msg, exc_info=True)
                self.restore_frozen_basket()
                return self.render_preview(self.request, error=msg)

            return HttpResponseRedirect(reverse('checkout:thank-you'))


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
            return HttpResponse()

        event_type, __ = PaymentEventType.objects.get_or_create(
            name="Adyen - {}".format(notification.event_code))

        EventHandler().create_payment_event(
            order=order,
            event_type=notification.event_code,
            amount=Decimal(notification.value) / 100,
            reference=notification.psp_reference)
        return super(NotificationView, self).handle_notification(notification)
