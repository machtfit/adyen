# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import base64
from datetime import date, datetime, timedelta
import gzip
import hashlib
import hmac
import logging
import StringIO
from urllib import urlencode
from urlparse import urlparse, parse_qs

import pytz

log = logging.getLogger(__name__)

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


class UnknownSkinCode(Exception):
    pass


class Backend(object):
    def get_skin(self, *args, **kwargs):
        raise NotImplementedError

    def get_skin_by_code(self, skin_code):
        raise NotImplementedError

    def get_notification_credentials(self):
        raise NotImplementedError


class Skin(object):
    def __init__(self, merchant_account, code, key, is_live=False,
                 payment_flow='onepage'):
        self.merchant_account = merchant_account
        self.code = code or ''
        self.key = key
        self.is_live = is_live
        self.payment_flow = payment_flow


class BadSignatureError(Exception):
    pass


class HostedPayment(object):
    """
    A payment session that is to be submitted to Adyen.

    All payment session fields mentioned in section 2.2 of the Integration
    Manual are accessible in underscore syntax (skinCode -> skin_code).
    Additionally the resURL field mentioned in section 2.4 of the Integration
    Manual is accessible as res_url.

    If a field has no value, it is None. This is possible only for optional
    fields. If a field is optional, has no value but is included in the
    signature calculation, it is never None. Instead it is the empty string.
    """
    def __init__(self, skin, merchant_reference, payment_amount,
                 currency_code, **kwargs):
        self._skin = skin
        self.merchant_reference = merchant_reference
        self.payment_amount = payment_amount
        self.currency_code = currency_code
        self.ship_before_date = timedelta(days=3)
        self.shopper_locale = None
        self.order_data = None
        self.session_validity = timedelta(days=1)
        self.merchant_return_data = ''
        self.country_code = None
        self.shopper_email = None
        self.shopper_reference = None
        self.recurring_contract = None
        self.allowed_methods = ''
        self.blocked_methods = ''
        self.offset = None
        self.brand_code = None
        self.issuer_id = None
        self.shopper_statement = ''
        self.offer_email = None
        self.res_url = None

        for name, value in kwargs.items():
            setattr(self, name, value)

    @property
    def skin_code(self):
        return self._skin.code

    @property
    def is_live(self):
        return self._skin.is_live

    @property
    def merchant_account(self):
        return self._skin.merchant_account

    def get_redirect_url(self):
        params = {
            'merchantReference': self.merchant_reference,
            'paymentAmount': self.payment_amount,
            'currencyCode': self.currency_code,
            'shipBeforeDate': self.ship_before_date,
            'skinCode': self.skin_code,
            'merchantAccount': self.merchant_account,
            'sessionValidity': self.session_validity,
            'resURL': self.res_url
        }
        optional_params = {
            'shopperLocale': self.shopper_locale,
            'orderData': self._encode_order_data(self.order_data),
            'merchantReturnData': self.merchant_return_data,
            'countryCode': self.country_code,
            'shopperEmail': self.shopper_email,
            'shopperReference': self.shopper_reference,
            'recurringContract': self.recurring_contract,
            'allowedMethods': self.allowed_methods,
            'blockedMethods': self.blocked_methods,
            'offset': self.offset,
            'brandCode': self.brand_code,
            'issuerId': self.issuer_id,
            'shopperStatement': self.shopper_statement,
            'offerEmail': self.offer_email
        }

        for key, value in optional_params.items():
            if value:
                params[key] = value

        if any(map(lambda x: x is None, params.values())):
            raise ValueError("The parameter(s) {} may not be None."
                             .format(", ".join([k for k, v in params.items()
                                                if v is None])))
        params = {key: str(value) for (key, value) in params.items()}
        params['merchantSig'] = self.get_setup_signature(params,
                                                         self._skin.key)
        live_or_test = 'test'
        if self._skin.is_live:
            live_or_test = 'live'

        single_or_multi = 'select'
        if self._skin.payment_flow == 'onepage':
            single_or_multi = 'pay'

        return ('https://{live_or_test}.adyen.com/'
                'hpp/{single_or_multi}.shtml?{params}'
                .format(live_or_test=live_or_test,
                        single_or_multi=single_or_multi,
                        params=urlencode(params)))

    @property
    def ship_before_date(self):
        return self._format_date(self._ship_before_date)

    @ship_before_date.setter
    def ship_before_date(self, value):
        self._ship_before_date = value

    @property
    def session_validity(self):
        return self._format_datetime(self._session_validity)

    @session_validity.setter
    def session_validity(self, value):
        self._session_validity = value

    @staticmethod
    def _format_date(value):
        if isinstance(value, timedelta):
            value = date.today() + value
        if not isinstance(value, date):
            raise ValueError("value must be timedelta or date, got {}"
                             .format(value))

        return value.isoformat()

    @staticmethod
    def _format_datetime(value):
        if isinstance(value, timedelta):
            value = datetime.utcnow() + value
        if not isinstance(value, datetime):
            raise ValueError("value must be timedelta or datetime, got {}"
                             .format(value))
        if is_naive(value):
            value = value.replace(tzinfo=pytz.utc)
        value = value.replace(microsecond=0)
        return value.isoformat()

    @staticmethod
    def _encode_order_data(value):
        out = StringIO.StringIO()
        with gzip.GzipFile(fileobj=out, mode="w") as f:
            f.write(value)
        return out.getvalue().encode('base64')

    @staticmethod
    def get_setup_signature(params, secret):
        """
        Calculate the payment setup signature in base64
        """
        keys = ['paymentAmount', 'currencyCode', 'shipBeforeDate',
                'merchantReference', 'skinCode', 'merchantAccount',
                'sessionValidity', 'shopperEmail', 'shopperReference',
                'recurringContract', 'allowedMethods', 'blockedMethods',
                'shopperStatement', 'merchantReturnData', 'billingAddressType',
                'deliveryAddressType', 'shopperType', 'offset']

        return _get_signature(keys, params, secret)


class HostedPaymentResult(object):
    def __init__(self, params, backend):

        log.debug('Received result:')
        log.debug(params)

        skin = backend.get_skin_by_code(params['skinCode'])
        if (self._get_result_signature(params, skin.key)
                != params['merchantSig']):
            raise BadSignatureError

        self.auth_result = params['authResult']
        self.psp_reference = params.get('pspReference')
        self.merchant_reference = params['merchantReference']
        self.skin_code = params['skinCode']
        self.payment_method = params.get('paymentMethod')
        self.shopper_locale = params['shopperLocale']
        self.merchant_return_data = params.get('merchantReturnData')

    @staticmethod
    def _get_result_signature(params, secret):
        """
        Calculate the payment result signature in base64
        """
        keys = ['authResult', 'pspReference', 'merchantReference', 'skinCode',
                'merchantReturnData']

        return _get_signature(keys, params, secret)

    @classmethod
    def mock(cls, backend, url):
        """
        Return the payment result url for a successful payment. Use this for
        unit tests.
        """
        url = urlparse(url)
        query = parse_qs(url.query, keep_blank_values=True)
        params = {
            'authResult': 'AUTHORISED',
            'pspReference': 'mockreference',
            'merchantReference': query['merchantReference'][0],
            'skinCode': query['skinCode'][0],
            'paymentMethod': 'visa',
            'shopperLocale': query.get('shopperLocale', '')[0],
            'merchantReturnData': query.get('merchantReturnData', '')[0]
        }
        skin = backend.get_skin_by_code(query['skinCode'][0])
        params['merchantSig'] = cls._get_result_signature(params, skin.key)
        return "{}?{}".format(query['resURL'][0], urlencode(params))


class HostedPaymentNotification(object):
    def __init__(self, params):

        log.debug('Received notification:')
        log.debug(params)

        # get a mutable copy
        params = params.dict()

        try:
            self.live = self._parse_boolean(params.pop('live'))
        except ValueError:
            raise ValueError("Invalid value for 'live': {}"
                             .format(params.pop('live')))

        self.event_code = params.pop('eventCode')
        self.psp_reference = params.pop('pspReference')
        self.original_reference = params.pop('originalReference')
        self.merchant_reference = params.pop('merchantReference')
        self.merchant_account_code = params.pop('merchantAccountCode')
        self.event_date = (datetime.strptime(params.pop('eventDate'),
                                             DATETIME_FORMAT)
                           .replace(tzinfo=pytz.utc))
        success = params.pop('success')
        try:
            self.success = self._parse_boolean(success)
        except ValueError:
            raise ValueError("Invalid value for 'success': {}".format(success))
        self.payment_method = params.pop('paymentMethod')
        self.operations = params.pop('operations')
        self.reason = params.pop('reason')
        self.value = int(params.pop('value'))
        self.currency = params.pop('currency')

        self.additional_params = None
        if params:
            self.additional_params = params

    @staticmethod
    def _parse_boolean(value):
        """
        Turn a string value of "true" or "false" into the corresponding boolean
        value. Raise ValueError if the string is something else.
        """
        if value == 'true':
            return True
        elif value == 'false':
            return False
        else:
            raise ValueError


def _get_signature(keys, params, secret):
    plaintext = "".join(map(lambda v: '' if v is None else v,
                            (params.get(key, '') for key in keys)))
    hm = hmac.new(secret, plaintext, hashlib.sha1)
    return base64.encodestring(hm.digest()).strip()


def is_naive(value):
    """
    Determines if a given datetime.datetime is naive.

    The logic is described in Python's docs:
    http://docs.python.org/library/datetime.html#datetime.tzinfo
    """
    # copied from Django
    return value.tzinfo is None or value.tzinfo.utcoffset(value) is None
