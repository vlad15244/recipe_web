from django.apps import AppConfig
import asyncio
import threading
import sys
import logging

logger = logging.getLogger(__name__)

class YourAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'vars'



