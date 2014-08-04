# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import base64
from functools import wraps
import logging

from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from .backends import get_backend
from .models import Payment, Result, Notification

from adyen import HostedPayment, HostedPaymentResult, HostedPaymentNotification

log = logging.getLogger(__name__)


class PaymentRequestMixin(object):
    def initiate_payment(self, reference, total_in_minor_units, currency_code):
        backend = get_backend()
        skin = backend.get_skin()
        payment = HostedPayment(skin, reference, total_in_minor_units,
                                currency_code)
        self.prepare_payment_request(payment)
        if payment.res_url is None:
            payment.res_url = self.request.build_absolute_uri(
                reverse('django-adyen:payment-result'))
        Payment.objects.persist(payment)
        return HttpResponseRedirect(payment.get_redirect_url())

    def prepare_payment_request(self, payment):
        backend = get_backend()
        for name, value in backend.get_payment_params().items():
            setattr(payment, name, value)


class PaymentResultView(View):
    def get(self, request):
        payment_result = HostedPaymentResult(request.GET, get_backend())
        Result.objects.persist(payment_result)
        return self.handle_payment_result(payment_result)

    def handle_payment_result(self, payment_result):
        return HttpResponse('Payment {}.'.format(payment_result.auth_result))


def basic_auth(f):
    @wraps(f)
    def _f(self, request, *args, **kwargs):
        # adapted from
        # http://ponytech.net/blog/2014/03/25/use-http-basic-authentification-login/ # noqa
        please_authorize_response = HttpResponse(status=401)
        please_authorize_response['WWW-Authenticate'] \
            = 'Basic realm="restricted area"'

        if 'HTTP_AUTHORIZATION' not in request.META:
            return please_authorize_response

        auth = request.META['HTTP_AUTHORIZATION'].split()
        if len(auth) != 2:
            return please_authorize_response

        if auth[0].lower() != "basic":
            return please_authorize_response

        backend = get_backend()
        credentials = backend.get_notification_credentials()

        user, password = base64.b64decode(auth[1]).split(':', 1)

        if (user, password) != credentials:
            return please_authorize_response

        return f(self, request, *args, **kwargs)
    return _f


class NotificationView(View):
    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(NotificationView, self).dispatch(*args, **kwargs)

    @basic_auth
    def post(self, request):
        notification = HostedPaymentNotification(request.POST)
        notification = Notification.objects.persist(notification)
        return self.handle_notification(notification)

    def handle_notification(self, notification):
        """
        The default response is required by Adyen, be sure to always send it
        unless you want Adyen to send the notification again and warn you that
        your configured URL doesn't accept nofitications.

        Ideally, in this method you just schedule a notification processing
        task and do the actual processing in another process. Or you pick up
        and handle unhandled notifications regularly otherwise, then you don't
        have to do anything here.

        The same notification may arrive several times. notification.original
        is the first notification record for duplicates.
        """
        return HttpResponse('[accepted]')
