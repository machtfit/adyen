# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import logging

from oscar_adyen.handler import Handler

log = logging.getLogger(__name__)


class HandleNotificationMiddleware(object):
    def process_request(self, request):
        log.info('Processing notifications')
        Handler().handle_notifications()
