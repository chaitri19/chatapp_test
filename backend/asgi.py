import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

# Set environment variable before importing Django-based modules
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

# Import after setting the environment variable
from chat.middleware import TokenAuthMiddlewareStack
from chat.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        TokenAuthMiddlewareStack(
            URLRouter(
                websocket_urlpatterns
            )
        )
    ),
})
