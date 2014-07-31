# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import json

from django.db import models


class PaymentManager(models.Manager):
    def persist(self, hosted_payment):
        payment = self.create(
            live=hosted_payment.is_live,
            payment_amount=hosted_payment.payment_amount,
            currency_code=hosted_payment.currency_code,
            ship_before_date=hosted_payment.ship_before_date,
            skin_code=hosted_payment.skin_code,
            merchant_account=hosted_payment.merchant_account,
            shopper_locale=hosted_payment.shopper_locale,
            order_data=hosted_payment.order_data,
            session_validity=hosted_payment.session_validity,
            merchant_return_data=hosted_payment.merchant_return_data,
            country_code=hosted_payment.country_code,
            shopper_email=hosted_payment.shopper_email,
            shopper_reference=hosted_payment.shopper_reference,
            allowed_methods=hosted_payment.allowed_methods,
            blocked_methods=hosted_payment.blocked_methods,
            offset=hosted_payment.offset,
            brand_code=hosted_payment.brand_code,
            issuer_id=hosted_payment.issuer_id,
            shopper_statement=hosted_payment.shopper_statement,
            offer_email=hosted_payment.offer_email,
            res_url=hosted_payment.res_url)

        ref = hosted_payment.merchant_reference.format(**{'payment_id':
                                                          payment.id})
        hosted_payment.merchant_reference = ref
        payment.merchant_reference = ref
        payment.save()

        return payment


class Payment(models.Model):
    """
    All information that goes in a payment session according to section 2.2 of
    the Integration Manual. resURL, which is mentioned only in section 2.4 is
    included as well.

    - required fields have null=False (the default)

    - optional fields that are required for the signature have blank=True but
    remain null=False like the required fields.

    - optional fields that aren't required for the signature have null=True and
    blank=True.

    - if maximum length information was available from either Adyen
    documentation or other sources, max_length is specified.
    """
    created_datetime = models.DateTimeField(auto_now_add=True)
    live = models.BooleanField()
    merchant_reference = models.CharField(max_length=80)
    payment_amount = models.IntegerField()
    currency_code = models.CharField(max_length=3)
    ship_before_date = models.DateField()
    skin_code = models.CharField(max_length=8)
    # no max length information found
    merchant_account = models.CharField(max_length=128)
    # http://tools.ietf.org/html/bcp47#section-4.4.1
    shopper_locale = models.CharField(max_length=35, blank=True, null=True)
    order_data = models.TextField(blank=True, null=True)
    session_validity = models.DateTimeField()
    merchant_return_data = models.CharField(max_length=128)
    country_code = models.CharField(max_length=2, blank=True, null=True)
    # http://stackoverflow.com/questions/386294/what-is-the-maximum-length-of-a-valid-email-address # noqa
    shopper_email = models.CharField(max_length=254, blank=True, null=True)
    # no max length information found
    shopper_reference = models.CharField(max_length=128, blank=True, null=True)
    allowed_methods = models.TextField(blank=True)
    blocked_methods = models.TextField(blank=True)
    offset = models.IntegerField(null=True)
    # Actual longest payment method brand code in our settings has 17
    # characters. Since we don't have all payment methods, max_length was
    # guessed.
    brand_code = models.CharField(max_length=40, blank=True, null=True)
    # No information other than examples found on issuerId. In the examples
    # the issuer id is a four figure number, but that's just a lower bound for
    # max_length.
    issuer_id = models.CharField(max_length=40, blank=True, null=True)
    shopper_statement = models.CharField(max_length=135, blank=True)
    offer_email = models.TextField(blank=True, null=True)
    res_url = models.CharField(max_length=2083, blank=True, null=True)

    objects = PaymentManager()


class ResultManager(models.Manager):
    def persist(self, hosted_payment_result):
        try:
            payment = Payment.objects.get(
                merchant_reference=hosted_payment_result.merchant_reference)
        except Payment.DoesNotExist:
            is_live = None
        else:
            is_live = payment.live

        return self.create(
            live=is_live,
            auth_result=hosted_payment_result.auth_result,
            psp_reference=hosted_payment_result.psp_reference,
            merchant_reference=hosted_payment_result.merchant_reference,
            skin_code=hosted_payment_result.skin_code,
            payment_method=hosted_payment_result.payment_method,
            shopper_locale=hosted_payment_result.shopper_locale,
            merchant_return_data=hosted_payment_result.merchant_return_data)


class Result(models.Model):
    """
    All information that is returned to the application by the final redirect
    from Adyen.
    """
    created_datetime = models.DateTimeField(auto_now_add=True)

    # We can't tell by the payment result whether it is from the live or test
    # system. We try to find a matching payment to determine live or test.
    # However if we can't find the payment, instead of not persisting the
    # result, we store None for this field.
    live = models.NullBooleanField()

    auth_result = models.CharField(max_length=10)
    # no max length info found
    psp_reference = models.CharField(max_length=100, blank=True, null=True)
    merchant_reference = models.CharField(max_length=80)
    skin_code = models.CharField(max_length=8)
    # see Payment.brand_code, which is the same
    payment_method = models.CharField(max_length=40, blank=True, null=True)
    shopper_locale = models.CharField(max_length=35)
    merchant_return_data = models.CharField(max_length=128, blank=True,
                                            null=True)

    objects = ResultManager()


class NotificationManager(models.Manager):
    def persist(self, hosted_payment_notification):
        return self.create(
            live=hosted_payment_notification.live,
            event_code=hosted_payment_notification.event_code,
            psp_reference=hosted_payment_notification.psp_reference,
            original_reference=hosted_payment_notification.original_reference,
            merchant_reference=hosted_payment_notification.merchant_reference,
            merchant_account_code=hosted_payment_notification
            .merchant_account_code,
            event_date=hosted_payment_notification.event_date,
            success=hosted_payment_notification.success,
            payment_method=hosted_payment_notification.payment_method,
            operations=hosted_payment_notification.operations,
            reason=hosted_payment_notification.reason,
            value=hosted_payment_notification.value,
            currency=hosted_payment_notification.currency,
            additional_params=json
            .dumps(hosted_payment_notification.additional_params))


class Notification(models.Model):
    created_datetime = models.DateTimeField(auto_now_add=True)

    live = models.BooleanField()
    event_code = models.CharField(max_length=100)
    # no max length info found
    psp_reference = models.CharField(max_length=100)
    # no max length info found
    original_reference = models.CharField(max_length=100)
    merchant_reference = models.CharField(max_length=80)
    # no max length information found
    merchant_account_code = models.CharField(max_length=128)
    event_date = models.DateTimeField()
    success = models.BooleanField()
    # see Payment.brand_code, which is the same
    payment_method = models.CharField(max_length=40, blank=True, null=True)
    operations = models.TextField()
    reason = models.TextField()
    value = models.IntegerField(null=True)
    currency = models.CharField(max_length=3, blank=True, null=True)
    additional_params = models.TextField(blank=True, null=True)

    objects = NotificationManager()

    def __unicode__(self):
        return "{event_code} {psp_reference}".format(**self.__dict__)

    def is_duplicate(self):
        objects = self._meta.model.objects
        return (objects.filter(event_code=self.event_code,
                               psp_reference=self.psp_reference,
                               created_datetime__lt=self.created_datetime)
                .exists())
