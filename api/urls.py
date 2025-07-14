from django.urls import path 
from .views import * 
from .testsuiteandapplication_view import *
from rest_framework.routers import DefaultRouter
from .views import Loginview, LogoutView
from .test_results_views import *
from .task_views import *
from .testcaseteststep_view import *
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .appiumview import (
    get_devices, 
    start_session, 
    execute_step, 
    end_session, 
    session_info
)
from django.views.decorators.http import require_http_methods

urlpatterns = [
    path('parsesteps/', ParseStepsAPIView.as_view(), name='parse-steps'),
    path('recordtestcase/', CreateTestCaseWithStepsAPIView.as_view(), name='recordtestcase'),
    path('testconnection/', TestConnectionAPIView.as_view(), name='parse-steps'),
    # path('rerundata/', RerunDataHandler.as_view(), name='rerundata-steps'),
    path('rerun/<int:testcase_id>/', RerunDataHandler.as_view(), name='rerundata-steps'),
    path("login/", CookieTokenObtainView.as_view(), name="cookie-login"),
    path('logout', LogoutView.as_view(), name = "logout"),
    path("testadminroute/", TestAdminView.as_view(), name="test-admin"),
    path('token/refresh/', RefreshAccessTokenView.as_view(), name='token_refresh'),
    path('assign-test/', TaskAssignmentView.as_view(), name='assign-test'),
    path('my_assignments/', TesterAssignmentsView.as_view(), name='my-assignments'),
    path('create_execution/', StartTestExecution.as_view(), name='start-test-execution'),
    path('save_test_result/', SaveTestResultView.as_view(), name='save-test-result'),
    path('test-results/<int:test_execution_id>/', TestResultsListView.as_view(), name='test-results-list'),
    path('test-result/<int:result_id>/', TestResultDetailView.as_view(), name='test-result-detail'),
    path("checkauth/", CheckAuthView.as_view(), name="check_auth"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path('api/devices/', get_devices, name='get_devices'),
    path('api/start-session/', start_session, name='start_session'),
    path('api/execute-step/', execute_step, name='execute_step'),
    path('api/end-session/', end_session, name='end_session'),
    path('api/session-info/', session_info, name='session_info'),
]


router = DefaultRouter()
router.register('testcases', TestCaseListView, basename='testcase-list')
router.register('users', UserViewSet, basename='user')
router.register('applications', ApplicationViewSet, basename='application')
router.register('testsuites', TestSuiteViewSet, basename='testsuite')
router.register('applications-with-suites', ApplicationWithSuitesViewSet, basename='application-with-suites')

urlpatterns += router.urls

# adb shell

# dumpsys window displays | grep -E “mCurrentFocus"
