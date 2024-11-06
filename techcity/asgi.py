import os
from channels.auth import AuthMiddlewareStack 
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
import apps.inventory.routing
import apps.finance.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "techcity.settings.development")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),  
    "websocket": AuthMiddlewareStack(
        URLRouter(
            apps.inventory.routing.websocket_urlpatterns, 
            apps.finance.routing.websocket_urlpatterns, 
        )
    ),
})
