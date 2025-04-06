from urllib.parse import parse_qs
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken, TokenError
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

@database_sync_to_async
def get_user(token_key):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        # Validate token and get user
        token = AccessToken(token_key)
        user_id = token.payload.get('user_id')
        
        if user_id:
            return User.objects.get(id=user_id)
        return AnonymousUser()
    except (TokenError, User.DoesNotExist) as e:
        logger.error(f"Invalid token or user does not exist: {e}")
        return AnonymousUser()
    except Exception as e:
        logger.error(f"Token authentication error: {e}")
        return AnonymousUser()

class TokenAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Extract query params from URL
        query_string = scope.get("query_string", b"").decode()
        params = {}
        
        # Parse query string
        for param in query_string.split('&'):
            if param:
                key_value = param.split('=')
                if len(key_value) == 2:
                    params[key_value[0]] = key_value[1]
        
        # Check for token
        token = params.get("token", None)
        
        if token:
            scope["user"] = await get_user(token)
            logger.info(f"WebSocket authenticated user: {scope['user']}")
        else:
            scope["user"] = AnonymousUser()
            logger.warning("Anonymous WebSocket connection")
        
        return await self.app(scope, receive, send)

# Function to use as middleware factory
def TokenAuthMiddlewareStack(app):
    return TokenAuthMiddleware(app)
