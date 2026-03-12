from django.apps import AppConfig
import asyncio
import logging
import threading
import sys

logger = logging.getLogger(__name__)

class VarsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'vars'