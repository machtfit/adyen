# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import base64
import logging
from functools import wraps

from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from adyen import is_old_browser

from . import api as django_adyen_api
from .backends import get_backend

log = logging.getLogger(__name__)


class PaymentRequestMixin(object):
    def pay(self, payment):
        user_agent = self.request.META.get('HTTP_USER_AGENT')
        url = django_adyen_api.pay(
            payment, self.request.build_absolute_uri,
            force_multi=is_old_browser(user_agent))
        return HttpResponseRedirect(url)


class PaymentResultView(View):
    def get(self, request):
        payment_result = django_adyen_api.get_payment_result(request.GET)
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
        notification = django_adyen_api.get_payment_notification(
            request.POST)
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
