# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^payment-done/$', views.PaymentResultView.as_view(),
        name='payment-result'),
    url(r'^notify/$', views.NotificationView.as_view(),
        name='payment-notification')
]

urls = urlpatterns, 'django-adyen', 'django-adyen'
