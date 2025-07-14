from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/appium/$', consumers.AppiumConsumer.as_asgi()),
]