import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from api.routing import websocket_urlpatterns
from channels.auth import AuthMiddlewareStack
from api import routing 

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mb_automation.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    )
})
