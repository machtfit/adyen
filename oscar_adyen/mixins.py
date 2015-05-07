# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from . import api as oscar_adyen_api
from adyen import is_old_browser

import oscar.apps.checkout.mixins as orig
from oscar.apps.payment.exceptions import RedirectRequired


class OrderPlacementMixin(orig.OrderPlacementMixin):
    def get_adyen_payment(self, order_number, total):
        # TODO: use correct subunit fraction depending on the currency
        # http://en.wikipedia.org/wiki/List_of_circulating_currencies
        return oscar_adyen_api.create_payment(order_number,
                                              int(total.incl_tax * 100),
                                              total.currency)

    def handle_payment(self, basket_id, order_number, total, **kwargs):
        payment = self.get_adyen_payment(order_number, total)

        if not payment:
            # no payment necessary
            return [], []

        user_agent = self.request.META.get('HTTP_USER_AGENT')
        raise RedirectRequired(oscar_adyen_api.pay(
            payment, basket_id,
            build_absolute_uri=self.request.build_absolute_uri,
            force_multi=is_old_browser(user_agent)))
