# -*- coding: utf-8 -

from django.conf import settings as global_settings
from djangosocket.utils.settings import AppSettings


class DjangoSocketSettings(AppSettings):
    ACCEPT_ALL = False
    MIDDLEWARE_INSTALLED = 'djangosocket.middleware.DjangoSocketMiddleware' in global_settings.MIDDLEWARE_CLASSES
    SERVER_NAME = 'gunicorn'

settings = DjangoSocketSettings(prefix="DJANGOSOCKET")