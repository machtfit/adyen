# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.core.urlresolvers import reverse

import django_adyen.views as django_views

import oscar.apps.checkout.mixins as orig
from oscar.apps.payment.exceptions import RedirectRequired


class OrderPlacementMixin(django_views.PaymentRequestMixin,
                          orig.OrderPlacementMixin):
    def handle_payment(self, order_number, total, **kwargs):
        ref = "{order_number}-{{payment_id}}".format(order_number=order_number)
        # TODO: use correct subunit fraction depending on the currency
        # http://en.wikipedia.org/wiki/List_of_circulating_currencies
        response = self.initiate_payment(ref, int(total.incl_tax * 100),
                                         total.currency)
        raise RedirectRequired(response.url)

    def prepare_payment_request(self, payment):
        super(OrderPlacementMixin, self).prepare_payment_request(payment)
        payment.res_url = self.request.build_absolute_uri(
            reverse('oscar-adyen:payment-result'))
