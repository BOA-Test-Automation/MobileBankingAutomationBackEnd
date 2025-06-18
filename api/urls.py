from django.urls import path 
from .views import * 
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('api/testcases/', TestCaseListView.as_view(), name='testcase-list'),
    path('api/parsesteps/', ParseStepsAPIView.as_view(), name='parse-steps'),
]
