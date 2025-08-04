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
from .suite_application_views import *  # Added import


urlpatterns = [
    path('parsesteps/', ParseStepsAPIView.as_view(), name='parse-steps'),
    path('recordtestcase/', CreateTestCaseWithStepsAPIView.as_view(), name='recordtestcase'),
    path('testconnection/', TestConnectionAPIView.as_view(), name='parse-steps'),
    path('rerun/<int:testcase_id>/', RerunDataHandler.as_view(), name='rerundata-steps'),
    path('auth/user/', AuthUserView.as_view(), name='auth-user'),
    path("login/", BearerTokenObtainView.as_view(), name="cookie-login"),
    path('logout', LogoutView.as_view(), name = "logout"),
    path("testadminroute/", TestAdminView.as_view(), name="test-admin"),
    path('token/refresh/', RefreshAccessTokenView.as_view(), name='token_refresh'),
    path('assign-test/', TaskAssignmentView.as_view(), name='assign-test'),
    path('my_assignments/', TesterAssignmentsView.as_view(), name='my-assignments'),
    path('manager_pending_assignments/', ManagerAssignmentsView.as_view(), name='manager-assignments'),
    path('create_execution/', StartTestExecution.as_view(), name='start-test-execution'),
    path('start-batch-test-execution/', StartBatchTestExecution.as_view(), name='start-batch-test-execution'),
    path('save-batch-test-results/', SaveBatchTestResultsView.as_view(), name='save-batch-test-results'),
    path('save_test_result/', SaveTestResultView.as_view(), name='save-test-result'),
    path('test-results/<int:test_execution_id>/', TestResultsListView.as_view(), name='test-results-list'),
    path('test-result/<int:result_id>/', TestResultDetailView.as_view(), name='test-result-detail'),
    path('get-my-testresults/', TesterAssignedTestsView.as_view(), name='tester-test-results'), 
    path('get-manager-testresults/', ManagerAssignedTestsView.as_view(), name='manager-test-results'),
    path('get-my-batch-testresults/', TesterExecutedBatchTestsView.as_view(), name='executed-batch-tests'),
    path('get-manager-pending-batch/', ManagerExecutedBatchTestsView.as_view(), name='executed-batch-tests'),
    path('testsuitetestcase/<int:suite_id>/', TestSuiteResultView.as_view(), name='test-suite-testcase'),
    path("checkauth/", CheckAuthView.as_view(), name="check_auth"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path('api/devices/', get_devices, name='get_devices'),
    path('api/start-session/', start_session, name='start_session'),
    path('api/execute-step/', execute_step, name='execute_step'),
    path('api/end-session/', end_session, name='end_session'),
    path('api/session-info/', session_info, name='session_info'),
    path('getapptestcase/<int:application_id>/', TestcaseApplicationViewSet.as_view(), name='application'),
    path('getSuiteApplications/<int:application_id>/', SuiteApplicationsView.as_view(), name='suite-applications'),
    path('setCustomGroup/', SetCustomGroupView.as_view({'post': 'post'}), name='set-custom-group'), 
    path('getUserCustomGroups/', SetCustomGroupView.as_view({'get': 'get_user_custom_groups'}), name='user-custom-groups'),
    path('getCustomGroupTestCases/<int:group_id>/', SetCustomGroupView.as_view({'get': 'get_custom_group_test_cases'}), name='custom-group-test-cases'),
    path('get_edit_custom_group_data/<int:group_id>/', SetCustomGroupView.as_view({'get': 'get_edit_custom_group_data'}), name='get-edit-custom-group-test-cases'),
    path('update_custom_group/<int:group_id>/', SetCustomGroupView.as_view({'put': 'update_custom_group'}), name='edit-custom-group-test-cases'),
    path('assignbatchtest/', AssignBatchToTesterView.as_view(), name='custom-group-test-cases'),
    path('getmyassignedbatchtests/', TesterAssignedBatchTestsView.as_view(), name='tester-assigned-batch-tests'),
    path('getmyassignedbatchtestsmanager/', ManagerAssignedBatchTestsView.as_view(), name='manager-assigned-batch-tests'),
    path('getbatchtestcases/<int:batch_id>/', BatchTestCasesView.as_view(), name='batch-test-cases'),
    path('getcustomgrouptype/', GetCustomGroupTypeView.as_view(), name='set-custom-group'), 
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