# -*- coding: utf-8 -*-

from celery import shared_task

from oscar_adyen import api


@shared_task
def handle_notifications():
    return api.handle_notifications()
