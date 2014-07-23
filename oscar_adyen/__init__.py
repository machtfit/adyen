# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.conf.urls import url

from django_adyen import urlpatterns

urlpatterns = [
    url(r'^payment-done/$', 'oscar_adyen.views.payment_result',
        name='payment-result'),
    url(r'^notify/$', 'oscar_adyen.views.notification',
        name='payment-notification')
] + urlpatterns

urls = urlpatterns, 'oscar-adyen', 'oscar-adyen'
