# -*- coding: utf-8 -*-

"""
>>> from freezegun import freeze_time
>>> freezer = freeze_time('2015-02-14 14:45:10')
>>> freezer.start()
>>> from adyen import api, Backend
>>> backend = Backend(merchant_account='account', skin_code='abc123',
...                   skin_secret=b'secret')
>>> payment = api.create_payment(backend, merchant_reference='1', amount=4599,
...                              currency='EUR')
>>> type(payment)
<class 'adyen.HostedPayment'>
>>> payment.res_url = 'https://my-domain.com/payment-result/order-123/'
>>> url = api.pay(payment)
>>> url
u'https://test.adyen.com/hpp/pay.shtml?sessionValidity=2015-02-15T14%3A45%3A10%2B00%3A00&merchantReference=1&currencyCode=EUR&paymentAmount=4599&shipBeforeDate=2015-02-17&merchantAccount=account&resURL=https%3A%2F%2Fmy-domain.com%2Fpayment-result%2Forder-123%2F&merchantSig=dRL230J0a3Um9W6YTnBtVYHtFf0%3D&skinCode=abc123'
>>> result_params = api.mock_payment_result_params(backend, url)
>>> result_params
{u'merchantReference': u'1', u'merchantReturnData': u'',\
 u'pspReference': u'mockreference',\
 u'merchantSig': 'nnOlck0P2obLtH/F/UXce3MG750=',\
 u'authResult': u'AUTHORISED', u'skinCode': u'abc123', u'shopperLocale': u'',\
 u'paymentMethod': u'visa'}
>>> result = api.get_payment_result(backend, result_params)
>>> type(result)
<class 'adyen.HostedPaymentResult'>
>>> result.auth_result
u'AUTHORISED'
>>> result.psp_reference
u'mockreference'
"""

from __future__ import unicode_literals

from urllib import urlencode
from urlparse import urlparse, parse_qs

from adyen import (HostedPayment, HostedPaymentResult, _get_result_signature,
                   HostedPaymentNotification)


def create_payment(backend, merchant_reference, amount, currency):
    if amount <= 0:
        return

    payment = HostedPayment(
        backend=backend,
        merchant_reference=merchant_reference,
        payment_amount=amount,
        currency_code=currency)

    return payment


def pay(payment, force_multi=False):
    return payment.get_redirect_url(force_multi)


def mock_payment_result_params(backend, url):
    url = urlparse(url)
    query = parse_qs(url.query, keep_blank_values=True)
    params = {
        'authResult': 'AUTHORISED',
        'pspReference': 'mockreference',
        'merchantReference': query.get('merchantReference', [''])[0],
        'skinCode': query['skinCode'][0],
        'paymentMethod': 'visa',
        'shopperLocale': query.get('shopperLocale', [''])[0],
        'merchantReturnData': query.get('merchantReturnData', [''])[0]
    }
    skin_secret = backend.get_skin_secret(query['skinCode'][0])
    params['merchantSig'] = _get_result_signature(params, skin_secret)
    return params


def mock_payment_result_url(backend, url):
    params = mock_payment_result_params(backend, url)
    url = urlparse(url)
    query = parse_qs(url.query, keep_blank_values=True)
    return "{}?{}".format(query['resURL'][0], urlencode(params))


def get_payment_result(backend, payment_result_params):
    return HostedPaymentResult(payment_result_params, backend)


def get_payment_notification(payment_notification_params):
    return HostedPaymentNotification(payment_notification_params)
