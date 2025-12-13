# opc/asgi.py
import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "opc.settings")  # БЕЗ ПРОБЕЛОВ!

django.setup()

from vars import routing  # ваш файл с маршрутами WebSocket
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns  # маршруты из routing.py
        )
    ),
})
