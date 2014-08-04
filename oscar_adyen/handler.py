# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from decimal import Decimal
import logging

from oscar.core.loading import get_model, get_class

from django_adyen.models import Notification

log = logging.getLogger(__name__)

EventHandler = get_class('order.processing', 'EventHandler')
Order = get_model('order', 'Order')
PaymentEventType = get_model('order', 'PaymentEventType')


class Handler(object):
    def handle_notifications(self):
        for notification in (Notification.objects.originals()
                             .filter(handled=False)):
            self.handle_notification(notification)

    def handle_notification(self, notification):
        log.info('Processing notification {}'.format(notification))
        try:
            order_number, payment_id \
                = map(int, notification.merchant_reference.split('-'))
            order = Order.objects.get(number=order_number)
        except (Order.DoesNotExist, ValueError):
            log.error("Couldn't find order for notification #{id} {s}"
                      .format(id=notification.pk, s=notification))
        else:
            event_type, __ = PaymentEventType.objects.get_or_create(
                name="Adyen - {}".format(notification.event_code))

            EventHandler().handle_payment_event(
                order=order,
                event_type=event_type,
                amount=Decimal(notification.value) / 100,
                lines=order.lines.all(),
                quantities=[line.quantity for line in order.lines.all()],
                reference=notification.psp_reference,
                notification=notification)
            notification.handled = True
            notification.save()
