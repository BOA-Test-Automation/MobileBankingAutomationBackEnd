from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated
from .models import StepResult, TestExecution, TestStep,  Device, TestCase 
from django.shortcuts import get_object_or_404
from django.shortcuts import get_object_or_404
import json

class SaveTestResultView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Save multiple test step results and update test execution status
        Expected POST data:
        {
            "test_execution_id": 1,
            "overall_status": "passed",
            "step_results": [
                {
                    "test_step_id": 5,
                    "actual_id": "com.example:id/button",
                    "actual_input": "test@example.com",
                    "actual_screenshot": "base64encodedimage",
                    "status": "passed",
                    "duration": 5,
                    "log_message": "Step completed successfully",
                    "error": null
                },
                ...
            ]
        }
        """
        try:
            # Get test execution and update its status
            test_execution = get_object_or_404(TestExecution, id=request.data.get('test_execution_id'))
            test_execution.overallstatus = request.data.get('overall_status', 'pending')
            test_execution.save()

            step_results_data = request.data.get('step_results', [])
            created_results = []
            
            for step_data in step_results_data:
                # Get test step
                test_step = get_object_or_404(TestStep, id=step_data.get('test_step_id'))
                
                # Create or update step result
                step_result, created = StepResult.objects.update_or_create(
                    test_execution=test_execution,
                    test_step=test_step,
                    defaults={
                        'actual_id': step_data.get('actual_id'),
                        'actual_input': step_data.get('actual_input'),
                        'actual_screenshot': step_data.get('actual_screenshot'),
                        'status': step_data.get('status'),
                        'duration': step_data.get('duration'),
                        'log_message': step_data.get('log_message'),
                        'error': step_data.get('error'),
                    }
                )
                
                created_results.append({
                    "result_id": step_result.id,
                    "test_step_id": test_step.id,
                    "created": created
                })
            
            return Response({
                "message": "Test results saved successfully",
                "test_execution_id": test_execution.id,
                "overall_status": test_execution.overallstatus,
                "results": created_results,
                "total_steps": len(created_results)
            }, status=http_status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=http_status.HTTP_400_BAD_REQUEST
            )

class TestResultsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, test_execution_id):
        """
        Get all step results for a test execution
        """
        try:
            test_execution = get_object_or_404(TestExecution, id=test_execution_id)
            
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
                    "expected_input": result.test_step.input,
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
                    "input": result.test_step.input,
                    "input_type": result.test_step.input_type,
                    "parameter_name": result.test_step.parameter_name
                },
                "actual": {
                    "element_id": result.actual_id,
                    "input": result.actual_input,
                    "screenshot": result.actual_screenshot
                },
                "status": result.status,
                "duration": result.duration,
                "start_time": result.test_start,
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