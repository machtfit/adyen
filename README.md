# Adyen for Python

With this package you can implement [Adyen Hosted Payment
Pages](https://www.adyen.com/home/technology/integration#HPP) in Python. It
also has ready-to-use apps for [Django](https://www.djangoproject.com/) and for
[Oscar](http://tangentlabs.github.io/django-oscar/).

Go to [Django support](#django).

Go to [Oscar support](#oscar).

This README assumes that you are familiar with the [Adyen Merchant
Manual](https://www.adyen.com/dam/documentation/manuals/MerchantManual.pdf) and
the [Hosted Payment Pages Integration
Manual](https://www.adyen.com/dam/documentation/manuals/IntegrationManual.pdf).

# Python

The `adyen` package contains the convenience classes `HostedPayment`, `Skin`,
`HostedPaymentResult` and `HostedPaymentNotification`.

## Skin

A `Skin` holds all payment session configuration data that does not strictly
depend on the actual product or service that is being paid for. A `Skin`
instance is passed to a `HostedPayment` to complete the payment session data.

## HostedPayment

An `HostedPayment` object holds all payment session data, encodes and signs it
properly to submit to Adyen. In addition to a `Skin` it takes the merchant
reference, the payment amount and the currency code. All other session data can
be modified by setting the corresponding properties of the `HostedPayment`
object.

```python
from adyen import Skin, HostedPayment

merchant_account = 'MyMerchantAccount'
skin_code = 'Ege3CEv4'
key = '123'

skin = Skin(merchant_account, skin_code, key, is_live=False)

merchant_reference = 'Order 123 {payment_id}'
payment_amount = 1199  # 11.99 EUR
currency_code = 'EUR'
payment = HostedPayment(skin, merchant_reference, payment_amount,
                        currency_code)

redirect_to = payment.get_redirect_url()
```

The merchant reference can contain the string `{payment_id}`, which will
replaced with the id of the `django_adyen.models.Payment` object.

For the session validity and the ship before date you can pass a datetime
object respectively a date object or a timedelta object. If you pass a
timedelta object, both values will be calculated from now respectively today.

```python
from datetime import date, datetime, timedelta

print(date.today())
# 2014-04-29
payment.ship_before_date = timedelta(days=4)
print(payment.ship_before_date)
# 2014-05-03

print(datetime.utcnow())
# 2014-04-29 15:56:36.601674
payment.session_validity = timedelta(days=2)
print(payment.session_validity)
# 2014-05-01T15:56:50+00:00

redirect_to = payment.get_redirect_url()
```

Currently there is no explicit support for submitting the payment from a POST
form. However the code for that should be very short and straighforward. If you
implement that please consider submitting a pull request.

## Backend

A `Backend` allows other parts of the code to retrieve a skin configuration by
its code. This is needed to check the signature of an incoming payment result.

Here's an example backend that works with just one static `Skin`, the `Skin`
from above:

```python
from adyen import Backend, UnknownSkinCode


class MyBackend(Backend):
    def get_skin(self):
        return skin

    def get_skin_by_code(self, skin_code):
        if skin.code != skin_code:
            raise UnknownSkinCode
        return skin


backend = MyBackend()
```

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

On top of the functionality in the `adyen` module, the `django_adyen` module
provides a view mixin for the payment request as well as views for the payment
result and for notifications. All three persist payment information in the
three models `Payment`, `Result` and `Notification` in `django_adyen.models`.
It also includes a backend implementation that uses the Django settings.

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
    url(r'^somewhere/', include(django_adyen.urls))
# ...
]
```

```python
# views.py

import django_adyen.views


class PaymentView(View):
    def post(self, request, *args, **kwargs):
        # call this method somewhere
        # It returns a HttpResponseRedirect to Adyen
        return self.initiate_payment(reference, total_in_minor_units,
                                     currency_code)


class PaymentResultView(django_adyen.views.PaymentResultView):
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

        if payment_result.auth_result == 'REFUSED':
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

# Oscar

The `oscar_adyen` module integrates the payment process into the oscar
checkout. To plug it in override the checkout app:

```python
# apps/checkout/app.py

import oscar.apps.checkout.app as orig

import oscar_adyen.views


class CheckoutApplication(orig.CheckoutApplication):
    payment_details_view = oscar_adyen.views.PaymentDetailsView


application = CheckoutApplication()
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
received through notifications are recorded as a payment event but not
otherwise handled.
