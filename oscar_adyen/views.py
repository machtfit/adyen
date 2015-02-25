# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.utils.translation import ugettext as _

import django_adyen.views as django_views
import oscar_adyen.api as oscar_adyen_api

from oscar.core.loading import get_class

CheckoutFlow = get_class('checkout.flow', 'CheckoutFlow')


class PaymentResultView(CheckoutFlow, django_views.PaymentResultView):
    def get(self, request, basket_id):
        self.basket_id = basket_id
        return super(PaymentResultView, self).get(request)

    def handle_payment_result(self, payment_result):
        try:
            payment_sources, payment_events = (
                oscar_adyen_api.handle_payment_result(payment_result))
        except oscar_adyen_api.PaymentFailed as e:
            payment_result = e.args[0]

            return self.handle_payment_failed(
                {'ERROR': _('Payment failed'),
                 'CANCELLED': _('Payment cancelled'),
                 'REFUSED': _('Payment refused')}
                .get(payment_result.auth_result,
                     _("Payment error: {}")
                     .format(payment_result.auth_result)))

        return self.handle_payment_successful(
            self.basket_id, payment_sources, payment_events)


payment_result = PaymentResultView.as_view()
