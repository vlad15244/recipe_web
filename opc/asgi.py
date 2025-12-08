# opc/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from vars import routing  # ваш файл с маршрутами WebSocket

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'opc.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns  # маршруты из routing.py
        )
    ),
})
