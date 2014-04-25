# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.conf.urls import url

from django_adyen import urlpatterns

from . import views

urlpatterns = [
    url(r'^payment-done/$', views.PaymentResultView.as_view(),
        name='payment-result'),
    url(r'^notify/$', views.NotificationView.as_view(),
        name='payment-notification')
] + urlpatterns

urls = urlpatterns, 'oscar-adyen', 'oscar-adyen'
