from django.urls import re_path
from . import consumers
from channels.routing import URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from .middleware import TokenAuthMiddlewareStack

websocket_urlpatterns = [
    re_path(r'ws/chat/$', consumers.ChatConsumer.as_asgi()),
]

# Note: This will be used in asgi.py, not directly here
