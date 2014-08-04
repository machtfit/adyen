# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.conf.urls import url

from django_adyen import urlpatterns

urlpatterns = [
    url(r'^payment-done/$', 'oscar_adyen.views.payment_result',
        name='payment-result')
] + urlpatterns

urls = urlpatterns, 'oscar-adyen', 'oscar-adyen'
