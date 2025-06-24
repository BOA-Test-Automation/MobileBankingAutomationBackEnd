from django.urls import path 
from .views import * 
from .testsuiteandapplication_view import *
from rest_framework.routers import DefaultRouter
from .views import Loginview, LogoutView
from .testcaseteststep_view import *
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('parsesteps/', ParseStepsAPIView.as_view(), name='parse-steps'),
    path('recordtestcase/', CreateTestCaseWithStepsAPIView.as_view(), name='recordtestcase'),
    path('testconnection/', TestConnectionAPIView.as_view(), name='parse-steps'),
    # path('rerundata/', RerunDataHandler.as_view(), name='rerundata-steps'),
    path('rerundata/<int:testcase_id>/', RerunDataHandler.as_view(), name='rerundata-steps'),
    path("login/", CookieTokenObtainView.as_view(), name="cookie-login"),
    path('logout', LogoutView.as_view(), name = "logout"),
    path("testadminroute/", TestAdminView.as_view(), name="test-admin"),
    path('token/refresh/', RefreshAccessTokenView.as_view(), name='token_refresh'),
    path("checkauth/", CheckAuthView.as_view(), name="check_auth"),
    path("logout/", LogoutView.as_view(), name="logout"),
]

router = DefaultRouter()
router.register('testcases', TestCaseListView, basename='testcase-list')
router.register('users', UserViewSet, basename='user')
router.register('applications', ApplicationViewSet, basename='application')
router.register('testsuites', TestSuiteViewSet, basename='testsuite')

urlpatterns += router.urls
