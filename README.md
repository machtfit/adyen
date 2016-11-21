# Adyen for Python

With this package you can implement [Adyen Hosted Payment
Pages](https://www.adyen.com/home/technology/integration#HPP) in Python. It
also has ready-to-use apps for [Django](https://www.djangoproject.com/) and for
[Oscar](http://oscarcommerce.com/).

# Production readiness

As of 2015-08-11 this code is in production use. However, do have a look at the
[open issues](../../issues).

# Usage

You need to read both the
[Adyen Merchant Manual](https://www.adyen.com/dam/documentation/manuals/MerchantManual.pdf)
and the
[Hosted Payment Pages Integration Manual](https://www.adyen.com/dam/documentation/manuals/IntegrationManual.pdf)
to successfully implement adyen.

Go to [Django support](#django).

Go to [Oscar support](#oscar).

# Python

The adyen module provides a simple Python API in the `api` submodule.

## Quick start

```python
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
```

Redirect the user to that URL. When they finished the payment, they will be
redirected to `res_url` with a number of query parameters.

We'll mock that part for demonstration purposes:

```python
>>> result_params = api.mock_payment_result_params(backend, url)
>>> result_params
{u'merchantReference': u'1', u'merchantReturnData': u'',\
 u'pspReference': u'mockreference',\
 u'merchantSig': 'nnOlck0P2obLtH/F/UXce3MG750=',\
 u'authResult': u'AUTHORISED', u'skinCode': u'abc123', u'shopperLocale': u'',\
 u'paymentMethod': u'visa'}
```

Pass the query parameters to the api to get a payment result:

```python
>>> result = api.get_payment_result(backend, result_params)
>>> type(result)
<class 'adyen.HostedPaymentResult'>
>>> result.auth_result
u'AUTHORISED'
>>> result.psp_reference
u'mockreference'
```

Refer to the Adyen Integration Manual (Section 2.4 "Payment Completion" as of
version 1.80) for the meaning of the various attributes of the payment result.

## HostedPayment

An `HostedPayment` object holds all payment session data, encodes and signs it
properly to submit to Adyen. Many payment parameters can be modified by setting
the corresponding properties of the `HostedPayment` object you get from
`create_payment()` before passing it to `pay()`.

For the session validity and the ship before date you can pass a datetime
object respectively a date object or a timedelta object. If you pass a
timedelta object, both values will be calculated from now respectively today.

```python
>>> from datetime import date, datetime, timedelta
>>> print(date.today())
2015-02-18
>>> payment.ship_before_date = timedelta(days=4)
>>> print(payment.ship_before_date)
2015-02-22
>>> print(datetime.utcnow())
2015-02-18 16:47:59.638420
>>> payment.session_validity = timedelta(days=2)
>>> print(payment.session_validity)
2015-02-20T16:48:08+00:00
```

Currently there is no explicit support for submitting the payment from a POST
form. However the code for that should be very short and straightforward. If
you implement that please consider submitting a pull request.

## Backend

A `Backend` provides configuration information for the payment that does not
strictly depend on the actual product or service that is being paid for.

Here is a sample static backend:

```python
from adyen import Backend

backend = Backend(merchant_account='account', skin_code='abc123',
                  skin_secret=b'secret')
```

Note that `skin_code` has to be a binary string.

## HostedPaymentResult

A `HostedPaymentResult` receives the payment result data from the final
redirect from Adyen and checks the signature.

```python
from adyen import HostedPaymentResult

try:
    result = HostedPaymentResult(request.GET, backend)
except BadSignatureError:
    # handle
    pass

print("Payment by {.payment_method} result: {.auth_result}".format(result))
```

## HostedPaymentNotification

A `HostedPaymentNotification` receives the payment notification data from
Adyen.

```python
from adyen import HostedPaymentNotification

check_http_basic_auth(request, backend.get_notification_credentials())

notification = HostedPaymentNotification(request.GET)

print("{.payment_method} payment event {.event_code} result: {.success}"
      .format(notification))
```

# Django

The `django_adyen` module contains an API that extends the pure Python API with

  1. Persisting payment requests, payment results and payment notifications
     using the Django models `Payment`, `Result` and `Notification` in
    `django_adyen.models`.
  2. a backend that uses the Django settings

`create_payment()` takes an order number instead of a merchant reference as the
first argument. The merchant reference is set to `ORDER_NUMBER-PAYMENT_ID`,
where `PAYMENT_ID` is the primary key value of the `Payment` model instance.

`pay()` takes a function to build an absolute URI from only the path part. If
you have a `Request` handy, pass `request.build_absolute_uri`.


```python
# settings.py

INSTALLED_APPS = [
# ...
    'django_adyen',
# ...
]

ADYEN_MERCHANT_ACCOUNT = 'MerchantAccount'
ADYEN_COUNTRY_CODE = 'DE'
ADYEN_SHOPPER_LOCALE = 'de_DE'
ADYEN_SKIN_CODE = 'aKhNrM6V'
ADYEN_SKIN_SECRET = 'secret'
ADYEN_NOTIFICATION_USER = 'user'
ADYEN_NOTIFICATION_PASSWORD = 'password'
```

```python
# urls.py

import django_adyen

urlpatterns = [
# ...
    url(r'^somewhere/', include(django_adyen.app.urls))
# ...
]
```

```python
# views.py

from django_adyen import views, api


class PaymentView(views.PaymentRequestMixin, View):
    def post(self, request, *args, **kwargs):
        payment = api.create_payment(order_number, total_in_minor_units,
                                     currency)
        return self.pay(payment)


class PaymentResultView(views.PaymentResultView):
    def handle_payment_result(self, payment_result):
        if payment_result.auth_result == 'ERROR':
            messages.warning(self.request, _('Payment failed'))
            # handle

        if payment_result.auth_result == 'CANCELLED':
            messages.warning(self.request, _('Payment cancelled'))
            # handle

        if payment_result.auth_result == 'REFUSED':
            messages.error(self.request, _('Payment refused'))
            # handle

        if payment_result.auth_result == 'PENDING':
            messages.info(self.request, _('Payment pending'))
            # handle

        if payment_result.auth_result == 'AUTHORISED':
            messages.success(self.request, _('Payment authorised'))
            # handle


class NotificationView(django_views.NotificationView):
    # use reverse('django-adyen:payment-notification') as the notification URL
    # in the Adyen notification configuration

    def handle_notification(self, notification):
        # notification is a django_adyen.models.Notification instance
        # notification.is_duplicate() is True for duplicate notifications

        # handle
```

You can write your own backend and configure `django_adyen` to use it like
this:

```python
# settings.py

ADYEN_BACKEND = 'mymodule.MyBackend'
```

`ADYEN_BACKEND` can be any callable that returns a `Backend` instance.

# Oscar

Warning: this module works only with the
[clerk](https://github.com/machtfit/django-oscar/tree/clerk)
([PR](https://github.com/django-oscar/django-oscar/pull/1678)) branch of oscar.

The `oscar_adyen` module integrates the payment process into the oscar
checkout. To plug it in override the checkout app and add or modify the
following files:

```python
# apps/checkout/mixins.py

from oscar_adyen.mixins import OrderPlacementMixin
```

```python
# settings.py

# for the settings do the same as in the Django instructions

# and add 'apps.checkout' to the argument list of get_core_apps

# use reverse('oscar-adyen:payment-notification') as the notification URL
# in the Adyen notification configuration
```

```python
# urls.py

import oscar_adyen

urlpatterns = [
# ...
    url(r'^checkout/adyen/', include(oscar_adyen.urls))
# ...
]
```

The oscar implementation is currently limited to placing an order when the
payment result is AUTHORISED or PENDING. Any further payment status changes
received through notifications are recorded as a payment event for the
corresponding order but not otherwise handled.
