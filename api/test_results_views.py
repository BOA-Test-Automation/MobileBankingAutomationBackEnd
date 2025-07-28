from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated
from .permissions import IsTester
from .models import *
from django.shortcuts import get_object_or_404
from django.shortcuts import get_object_or_404
import json
from rest_framework.exceptions import PermissionDenied

class SaveTestResultView(APIView):

    """
      {
        "test_execution_id": 1,
        "overall_status": "pass",
        "step_results": [
            {
            "test_step_id": 229,
            "actual_id": "cn.tydic.ethiopay:id/inputEditText",
            "actual_input": null,
            "status": "passed",
            "duration": 1.23,
            "time_start": "2023-05-20T10:00:00.000Z",
            "time_end": "2023-05-20T10:00:01.230Z",
            "log_message": "Step 1: click completed",
            "error": null
            },
            {
            "test_step_id": 230,
            "actual_id": "new UiSelector().className('android.view.View').instance(3)",
            "actual_input": "test@example.com",
            "status": "passed",
            "duration": 2.45,
            "time_start": "2023-05-20T10:00:02.000Z",
            "time_end": "2023-05-20T10:00:04.450Z",
            "log_message": "Step 2: send_keys completed",
            "error": null
            },
            {
            "test_step_id": 231,
            "actual_id": "new UiSelector().text('Payment')",
            "actual_input": "secure123",
            "status": "passed",
            "duration": 1.87,
            "time_start": "2023-05-20T10:00:05.000Z",
            "time_end": "2023-05-20T10:00:06.870Z",
            "log_message": "Step 3: send_keys completed",
            "error": null
            },
            {
            "test_step_id": 232,
            "actual_id": "new UiSelector().className('android.Edit').instance(1)",
            "actual_input": null,
            "status": "pass",
            "duration": 5.00,
            "time_start": "2023-05-20T10:00:07.000Z",
            "time_end": "2023-05-20T10:00:12.000Z",
            "log_message": "CRITICAL: Element 'btnSubmit' not found",
            "error": "Element 'btnSubmit' not found"
            }
        ]
       }
    """
    # permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Get test execution and update its status
            print(request.data.get('test_execution_id'))
            print(request.data.get('overall_status'))
            print(request.data.get('step_results'))
            test_execution = get_object_or_404(TestExecution, id=request.data.get('test_execution_id'))
            test_execution.overallstatus = request.data['overall_status']
            test_execution.save()

            try:
                assignment = TestAssignment.objects.get(execution=test_execution)
                assignment.status = 'completed_pass' if request.data['overall_status'] == 'passed' else 'completed_fail'
                assignment.save()
            except TestAssignment.DoesNotExist:
                return Response(
                    {"error": "No test assignment found for this execution"},
                    status=http_status.HTTP_400_BAD_REQUEST
                )

            step_results_data = request.data.get('step_results')
            print(step_results_data)
            created_results = []
            step_results = []
            
            for step_data in step_results_data:
                # Get test step
                test_step = get_object_or_404(TestStepTest, id=step_data.get('test_step'))
                
                step_result, created = StepResult.objects.update_or_create(
                    test_execution=test_execution,
                    test_step=test_step,
                    defaults={
                        'actual_id': step_data.get('actual_id'),
                        'actual_input': step_data.get('actual_input'),
                        'status': step_data.get('status'),
                        'duration': step_data.get('duration'),
                        'time_start': step_data.get('time_start'),
                        'time_end': step_data.get('time_end'),
                        'log_message': step_data.get('log_message'),
                        'error': step_data.get('error'),
                    }
                )

                created_results.append({
                    "result_id": step_result.id,
                    "test_step_id": test_step.id,
                    "created": created,
                    "status": step_result.status,
                    "actual_id": step_result.actual_id,
                    "actual_input": step_result.actual_input,
                    "log_message": step_result.log_message,
                    "error": step_result.error,
                })
            
            return Response({
                "message": "Test results saved successfully",
                "test_execution_id": test_execution.id,
                "overall_status": test_execution.overallstatus,
                "results": created_results,
                "total_steps": len(created_results)
            }, status=200)
            
        except Exception as e:
            print(str(e))
            return Response(
                {"error": str(e)},
                status=http_status.HTTP_400_BAD_REQUEST
            )
# class AllTestResultsListView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         """
#         Get all step results for the tester
#         """
#         try:
#             test_execution = get_object_or_404(TestExecution, id=test_execution_id)
            
#             # Verify the requesting user has permission (either assigned tester or manager)
#             if request.user != test_execution.executed_by and request.user.role != 'manager':
#                 return Response(
#                     {"error": "You don't have permission to view these results"},
#                     status=http_status.HTTP_403_FORBIDDEN
#                 )
            
#             results = StepResult.objects.filter(
#                 test_execution=test_execution
#             ).select_related('test_step').order_by('test_step__step_order')

#             data = []
#             for result in results:
#                 data.append({
#                     "id": result.id,
#                     "step_order": result.test_step.step_order,
#                     "expected_action": result.test_step.action,
#                     "expected_element": result.test_step.element_id,
#                     "expected_input": result.test_step.actual_input,
#                     "actual_id": result.actual_id,
#                     "actual_input": result.actual_input,
#                     "status": result.status,
#                     "duration": result.duration,
#                     "log_message": result.log_message,
#                     "error": result.error,
#                     "created_at": result.created_at
#                 })

#             return Response({
#                 "test_execution_id": test_execution_id,
#                 "overall_status": test_execution.overallstatus,
#                 "results": data
#             })
            
#         except Exception as e:
#             return Response(
#                 {"error": str(e)},
#                 status=http_status.HTTP_400_BAD_REQUEST
#             )
        
        
class TestResultsListView(APIView):

    permission_classes = [IsAuthenticated, IsTester]

    def get(self, request, test_execution_id):
        """
        Get all step results for a test execution
        """
        try:
            test_execution = get_object_or_404(TestExecution, id=test_execution_id)

            # print(test_execution.executed_by)
            
            # Verify the requesting user has permission (either assigned tester or manager)
            if request.user != test_execution.executed_by and request.user.role != 'manager':
                return Response(
                    {"error": "You don't have permission to view these results"},
                    status=http_status.HTTP_403_FORBIDDEN
                )
            
            results = StepResult.objects.filter(
                test_execution=test_execution
            ).select_related('test_step').order_by('test_step__step_order')

            data = []
            for result in results:
                data.append({
                    "id": result.id,
                    "step_order": result.test_step.step_order,
                    "expected_action": result.test_step.action,
                    "expected_element": result.test_step.element_id,
                    "expected_input": result.test_step.actual_input,
                    "actual_id": result.actual_id,
                    "actual_input": result.actual_input,
                    "status": result.status,
                    "duration": result.duration,
                    "log_message": result.log_message,
                    "error": result.error,
                    "created_at": result.created_at
                })

            return Response({
                "test_execution_id": test_execution_id,
                "overall_status": test_execution.overallstatus,
                "results": data
            })
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=http_status.HTTP_400_BAD_REQUEST
            )

# class TesterTestResultsView(APIView):
#     permission_classes = [IsAuthenticated, IsTester]

#     def get(self, request, execution_id):
#         try:
#             # Get any assignment with this execution_id to verify existence
#             assignment = get_object_or_404(
#                 TestAssignment,
#                 execution_id=execution_id
#             )
            
#             # Check if the current user is the assigned tester
#             if assignment.assigned_to != request.user:
#                 raise PermissionDenied("You are not allowed to see these results")
            
#             # Now get all test assignments for this execution and user
#             assignments = TestAssignment.objects.filter(
#                 execution_id=execution_id,
#                 assigned_to=request.user
#             ).select_related(
#                 'test_case',
#                 'assigned_by',
#                 'execution'
#             ).order_by('priority', 'deadline')

#             execution = []
#             for assignment in assignments:
#                 test_case = assignment.test_case
#                 execution.append({
#                     "test_case_name": test_case.name,
#                     "assigned_by": assignment.assigned_by.username,
#                     "assigned_date": assignment.created_at,
#                     "priority": assignment.priority,
#                     "status": assignment.status,
#                     "deadline": assignment.deadline,
#                     "execution_id": assignment.execution.id if assignment.execution else None,
#                     "test_case_code": test_case.code,
#                     "test_case_description": test_case.description,
#                     "notes": assignment.notes,
#                     "assignment_id": assignment.id
#                 })

#             return Response({
#                 "count": len(execution),
#                 "execution": execution
#             }, status=200)

#         except PermissionDenied as e:
#             return Response(
#                 {"error": str(e)},
#                 status=403  # This ensures 403 status
#             )
#         except Exception as e:
#             return Response(
#                 {"error": str(e)},
#                 status=400
#             )


class TesterAssignedTestsView(APIView):
    permission_classes = [IsAuthenticated, IsTester]

    def get(self, request):
        try:
            # Get all test assignments for the current user where execution is not null
            assignments = TestAssignment.objects.filter(
                assigned_to=request.user,
                execution__isnull=False
            ).exclude(
                status='pending'
            ).select_related(
                'test_case',
                'assigned_by',
                'execution',
                'execution__executed_device'  # Add this to join with Device table
            ).order_by('priority', 'deadline')

            results = []
            for assignment in assignments:
                # Get device name if execution exists and has a device
                device_name = None
                if assignment.execution and assignment.execution.executed_device:
                    device_name = assignment.execution.executed_device.device_name

                results.append({
                    "test_case_name": assignment.test_case.name,
                    "assigned_by": assignment.assigned_by.username,
                    "assigned_date": assignment.created_at,
                    "priority": assignment.priority,
                    "status": assignment.status,
                    "deadline": assignment.deadline,
                    "execution_id": assignment.execution.id,
                    "test_case_code": assignment.test_case.code,
                    "test_case_description": assignment.test_case.description,
                    "notes": assignment.notes,
                    "assignment_id": assignment.id,
                    "device_name": device_name  # Add device name to response
                })

            return Response({
                "count": len(results),
                "results": results
            }, status=200)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=400
            )
        

class TestResultDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, result_id):
        """
        Get detailed information about a specific test result
        """
        try:
            result = get_object_or_404(
                StepResult.objects.select_related('test_step', 'test_execution'),
                id=result_id
            )
            
            # Verify permission
            if request.user != result.test_execution.executed_by and request.user.role != 'manager':
                return Response(
                    {"error": "You don't have permission to view this result"},
                    status=http_status.HTTP_403_FORBIDDEN
                )
            
            response_data = {
                "id": result.id,
                "test_execution_id": result.test_execution.id,
                "test_case_id": result.test_execution.test_case.id,
                "test_case_name": result.test_execution.test_case.name,
                "step_order": result.test_step.step_order,
                "expected": {
                    "action": result.test_step.action,
                    "element_identifier": result.test_step.element_identifier_type.name if result.test_step.element_identifier_type else None,
                    "element_id": result.test_step.element_id,
                    "input": result.test_step.actual_input,
                    "input_type": result.test_step.input_type,
                    "parameter_name": result.test_step.parameter_name
                },
                "actual": {
                    "element_id": result.actual_id,
                    "input": result.actual_input,
                    # "screenshot": result.actual_screenshot
                },
                "status": result.status,
                "duration": result.duration,
                "start_time": result.time_start,
                "end_time": result.time_end,
                "log_message": result.log_message,
                "error": result.error,
                "created_at": result.created_at
            }
            
            return Response(response_data)
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=http_status.HTTP_400_BAD_REQUEST
            )

class CreateTestExecutionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Create a new test execution
        Expected POST data:
        {
            "test_case_id": 1,
            "device_id": 1,
            "executed_device_id": 1,  # Optional
            "notes": "Initial execution"  # Optional
        }
        """
        try:
            # Get required data
            test_case_id = request.data.get('test_case_id')
            device_id = request.data.get('device_id')
            
            if not test_case_id or not device_id:
                return Response(
                    {"error": "test_case_id and device_id are required"},
                    status=http_status.HTTP_400_BAD_REQUEST
                )
            
            # Verify test case exists
            test_case = get_object_or_404(TestCase, id=test_case_id)
            
            # Verify device exists
            device = get_object_or_404(Device, id=device_id)
            
            # Create test execution
            execution = TestExecution.objects.create(
                test_case=test_case,
                device=device,
                executed_by=request.user,
                executed_device_id=request.data.get('executed_device_id', device_id),
                overallstatus='pending'  # Default status
            )
            
            return Response({
                "message": "Test execution created successfully",
                "execution_id": execution.id,
                "status": execution.overallstatus,
                "created_at": execution.created_at
            }, status=http_status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=http_status.HTTP_400_BAD_REQUEST
            )

class TestExecutionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, execution_id):
        """
        Get detailed information about a specific test execution
        """
        try:
            execution = get_object_or_404(
                TestExecution.objects.select_related(
                    'test_case', 
                    'device', 
                    'executed_by',
                    'executed_device'
                ),
                id=execution_id
            )
            
            # Verify permission (either executor or manager/admin)
            if (request.user != execution.executed_by and 
                request.user.role not in ['manager', 'admin']):
                return Response(
                    {"error": "You don't have permission to view this execution"},
                    status=http_status.HTTP_403_FORBIDDEN
                )
            
            # Get all step results for this execution
            step_results = StepResult.objects.filter(
                test_execution=execution
            ).select_related('test_step').order_by('test_step__step_order')
            
            results_data = []
            for result in step_results:
                results_data.append({
                    "step_id": result.test_step.id,
                    "step_order": result.test_step.step_order,
                    "action": result.test_step.action,
                    "expected_element": result.test_step.element_id,
                    "status": result.status,
                    "duration": result.duration,
                    "error": result.error
                })
            
            response_data = {
                "id": execution.id,
                "test_case": {
                    "id": execution.test_case.id,
                    "name": execution.test_case.name,
                    "code": execution.test_case.code
                },
                "device": {
                    "id": execution.device.id,
                    "name": execution.device.device_name,
                    "platform": execution.device.platform
                },
                "executed_by": {
                    "id": execution.executed_by.id,
                    "username": execution.executed_by.username,
                    "role": execution.executed_by.role
                },
                "executed_device": {
                    "id": execution.executed_device.id if execution.executed_device else None,
                    "name": execution.executed_device.device_name if execution.executed_device else None
                },
                "status": execution.overallstatus,
                "created_at": execution.created_at,
                "updated_at": execution.updated_at,
                "step_results": results_data,
                "total_steps": step_results.count(),
                "passed_steps": step_results.filter(status='passed').count(),
                "failed_steps": step_results.filter(status='failed').count()
            }
            
            return Response(response_data)
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=http_status.HTTP_400_BAD_REQUEST
            )

class TestExecutionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get list of test executions with filtering options
        Query params:
        - test_case_id: filter by test case
        - device_id: filter by device
        - user_id: filter by executor
        - status: filter by status
        """
        try:
            queryset = TestExecution.objects.select_related(
                'test_case', 'device', 'executed_by'
            ).order_by('-created_at')
            
            # Apply filters
            test_case_id = request.query_params.get('test_case_id')
            if test_case_id:
                queryset = queryset.filter(test_case_id=test_case_id)
                
            device_id = request.query_params.get('device_id')
            if device_id:
                queryset = queryset.filter(device_id=device_id)
                
            user_id = request.query_params.get('user_id')
            if user_id:
                queryset = queryset.filter(executed_by_id=user_id)
                
            status = request.query_params.get('status')
            if status:
                queryset = queryset.filter(overallstatus=status)
            
            # For non-manager/admin users, only show their own executions
            if request.user.role not in ['manager', 'admin']:
                queryset = queryset.filter(executed_by=request.user)
            
            data = []
            for execution in queryset:
                # Get basic stats about step results
                step_results = StepResult.objects.filter(test_execution=execution)
                total_steps = step_results.count()
                passed_steps = step_results.filter(status='passed').count()
                
                data.append({
                    "id": execution.id,
                    "test_case_id": execution.test_case.id,
                    "test_case_name": execution.test_case.name,
                    "device_name": execution.device.device_name,
                    "executed_by": execution.executed_by.username,
                    "status": execution.overallstatus,
                    "progress": f"{passed_steps}/{total_steps}" if total_steps > 0 else "0/0",
                    "created_at": execution.created_at,
                    "updated_at": execution.updated_at
                })
            
            return Response({
                "count": len(data),
                "results": data
            })
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=http_status.HTTP_400_BAD_REQUEST
            )