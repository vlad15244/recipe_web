from django.apps import AppConfig
import asyncio
import threading
import sys
import logging

logger = logging.getLogger(__name__)

class YourAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'vars'

    def ready(self):
        if 'runserver' in sys.argv:
            threading.Thread(
                target=self._start_opc_poller,
                daemon=True
            ).start()

    def _start_opc_poller(self):
        """Запуск OPC UA poller в отдельном потоке"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            logger.info("Создан новый event loop для фонового опроса PLC")

            from .consumer import OpcRuntime
            poller = OpcRuntime()

            # ЗАПУСК МЕТОДА START() ПРОИСХОДИТ ЗДЕСЬ:
            loop.run_until_complete(poller.start())
        except Exception as e:
            logger.error(f"Ошибка запуска OPC poller: {e}")


