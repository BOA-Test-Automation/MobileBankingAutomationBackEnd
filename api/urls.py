from django.urls import path 
from .views import * 
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('parsesteps/', ParseStepsAPIView.as_view(), name='parse-steps'),
]

router = DefaultRouter()
router.register('testcases', TestCaseListView, basename='testcase-list')

urlpatterns += router.urls
