from django.urls import path 
from .views import * 
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('parsesteps/', ParseStepsAPIView.as_view(), name='parse-steps'),
    # path('rerundata/', RerunDataHandler.as_view(), name='rerundata-steps'),
    path('rerundata/<int:testcase_id>/', RerunDataHandler.as_view(), name='rerundata-steps'),
]

router = DefaultRouter()
router.register('testcases', TestCaseListView, basename='testcase-list')

urlpatterns += router.urls
