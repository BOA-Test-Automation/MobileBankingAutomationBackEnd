from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt import views as jwt_views
from django.urls import path, re_path

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('', include('api.urls'))
]

# websocket_urlpatterns = [
#     re_path(r'^ws/appium/', include('api.routing')),
# ]

