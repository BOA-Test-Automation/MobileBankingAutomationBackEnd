from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated
from .permissions import *
import logging
from .models import *
from django.shortcuts import get_object_or_404
from django.shortcuts import get_object_or_404
import json
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from django.utils.dateparse import parse_datetime
logger = logging.getLogger(__name__)
from django.db.models import Prefetch

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
            "error": null,
            "screenshot" :null
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
                        'actual_screenshot' : step_data.get('screenshot')
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
                    "screenshoot" : step_result.actual_screenshot
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
        
class StartBatchTestExecution(APIView):

    permission_classes = [IsAuthenticated, IsTester]

    def post(self, request):
        test_case_id = request.data.get("test_case_id")
        batch_id = request.data.get("batch_id")
        device_uuid = request.data.get("device_uuid")
        device_name = request.data.get("device_name")
        os_version = request.data.get("os_version")
        platform = request.data.get("platform")

        if not all([test_case_id, device_uuid, os_version, platform, batch_id]):
            return Response(
                {"error": "Required fields are missing"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        test_case = get_object_or_404(TestCase, id=test_case_id)
        batch = get_object_or_404(BatchAssignment, id=batch_id)

        try:
            device, created = Device.objects.get_or_create(
                device_uuid=device_uuid,
                defaults={
                    'device_name': device_name,
                    'platform': platform,
                    'os_version': os_version
                }
            )

            # Create test execution
            test_execution = TestExecution.objects.create(
                test_case=test_case,
                batch=batch,
                executed_by=request.user,
                executed_device=device,
                overallstatus='pending'
            )

            # Link to BatchAssignmentTestCase
            batch_test_case = BatchAssignmentTestCase.objects.get(
                batch=batch,
                test_case=test_case
            )
            batch_test_case.execution = test_execution
            batch_test_case.save()

            return Response({
                "message": "Batch test execution initialized successfully",
                "test_execution_id": test_execution.id,
                "device_id": device.id,
                "status": "in_progress"
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": f"Failed to initialize batch test execution: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

# class SaveBatchTestResultsView(APIView):
#     permission_classes = [IsAuthenticated, IsTester]

#     def post(self, request):
#         try:
#             data = request.data
#             batch_id = data.get('batch_id')
#             overall_status = data.get('overall_status')
#             test_case_results = data.get('test_case_results', [])
#             completed_at = data.get('completed_at')

#             if not all([batch_id, overall_status]):
#                 return Response(
#                     {"error": "batch_id and overall_status are required"},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )

#             # Get batch assignment with select_related/prefetch_related for performance
#             batch_assignment = BatchAssignment.objects.select_related(
#                 'assigned_to', 'assigned_by', 'assignment_type'
#             ).get(id=batch_id)

#             # Update batch status
#             batch_assignment.status = overall_status
#             batch_assignment.completedtestcases = len(test_case_results)
#             batch_assignment.passedtestcases = sum(
#                 1 for tc in test_case_results if tc.get('status') == 'passed'
#             )
            
#             if completed_at:
#                 try:
#                     batch_assignment.completed_at = parse_datetime(completed_at)
#                 except (ValueError, TypeError):
#                     pass

#             batch_assignment.save()

#             results = []
#             for tc_result in test_case_results:
#                 try:
#                     test_execution = TestExecution.objects.select_related(
#                         'test_case', 'executed_by', 'executed_device'
#                     ).get(
#                         id=tc_result.get('test_execution_id'),
#                         batch=batch_assignment
#                     )
                    
#                     # Update execution status
#                     test_execution.overallstatus = tc_result.get('status')
#                     test_execution.save()

#                     # Process step results
#                     step_results = []
#                     for step_data in tc_result.get('step_results', []):
#                         try:
#                             test_step = TestStepTest.objects.get(id=step_data.get('test_step_id'))
                            
#                             # Convert ISO strings to datetime
#                             time_start = parse_datetime(step_data.get('time_start'))
#                             time_end = parse_datetime(step_data.get('time_end'))
                            
#                             step_result, created = StepResult.objects.update_or_create(
#                                 test_execution=test_execution,
#                                 test_step=test_step,
#                                 defaults={
#                                     'actual_id': step_data.get('actual_id'),
#                                     'actual_input': step_data.get('actual_input'),
#                                     'status': step_data.get('status'),
#                                     'duration': step_data.get('duration'),
#                                     'time_start': time_start,
#                                     'time_end': time_end,
#                                     'log_message': step_data.get('log_message'),
#                                     'error': step_data.get('error'),
#                                     'actual_screenshot': step_data.get('screenshot') 
#                                 }
#                             )
#                             step_results.append({
#                                 "test_step_id": test_step.id,
#                                 "status": step_result.status,
#                                 "created": created
#                             })
                            
#                         except TestStepTest.DoesNotExist:
#                             continue
#                         except Exception as e:
#                             logger.error(f"Error saving step result: {str(e)}")
#                             continue

#                     results.append({
#                         "test_case_id": test_execution.test_case.id,
#                         "test_execution_id": test_execution.id,
#                         "step_results_count": len(step_results)
#                     })

#                 except TestExecution.DoesNotExist:
#                     continue
#                 except Exception as e:
#                     logger.error(f"Error processing test case result: {str(e)}")
#                     continue

#             return Response({
#                 "message": "Batch test results saved successfully",
#                 "batch_id": batch_assignment.id,
#                 "overall_status": batch_assignment.status,
#                 "passed_count": batch_assignment.passedtestcases,
#                 "total_count": batch_assignment.completedtestcases,
#                 "saved_results": len(results)
#             }, status=status.HTTP_200_OK)

#         except BatchAssignment.DoesNotExist:
#             return Response(
#                 {"error": "Batch assignment not found"},
#                 status=status.HTTP_404_NOT_FOUND
#             )
#         except Exception as e:
#             logger.error(f"Error saving batch results: {str(e)}")
#             return Response(
#                 {"error": "An error occurred while saving results"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )

class SaveBatchTestResultsView(APIView):
    permission_classes = [IsAuthenticated, IsTester]

    def post(self, request):
        try:
            data = request.data
            batch_id = data.get('batch_id')
            overall_status = data.get('overall_status')
            test_case_results = data.get('test_case_results', [])
            completed_at = data.get('completed_at')

            if not all([batch_id, overall_status]):
                return Response(
                    {"error": "batch_id and overall_status are required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            batch_assignment = BatchAssignment.objects.select_related(
                'assigned_to', 'assigned_by', 'assignment_type'
            ).get(id=batch_id)
            
            # --- We can optimistically save the main batch info first ---
            batch_assignment.status = overall_status
            batch_assignment.completedtestcases = len(test_case_results)
            batch_assignment.passedtestcases = sum(
                1 for tc in test_case_results if tc.get('status') == 'passed'
            )
            if completed_at:
                try:
                    batch_assignment.completed_at = parse_datetime(completed_at)
                except (ValueError, TypeError):
                    pass
            batch_assignment.save()


            # *** CRITICAL CHANGE IS HERE ***
            # We will now check for errors inside the loop and handle them after.
            errors_encountered = []
            saved_results_count = 0

            for tc_result in test_case_results:
                try:
                    test_execution = TestExecution.objects.select_related(
                        'test_case', 'executed_by', 'executed_device'
                    ).get(id=tc_result.get('test_execution_id'), batch=batch_assignment)
                    
                    test_execution.overallstatus = tc_result.get('status')
                    test_execution.save()

                    for step_data in tc_result.get('step_results', []):
                        try:
                            test_step = TestStepTest.objects.get(id=step_data.get('test_step_id'))
                            
                            time_start = parse_datetime(step_data.get('time_start')) if step_data.get('time_start') else None
                            time_end = parse_datetime(step_data.get('time_end')) if step_data.get('time_end') else None
                            
                            StepResult.objects.update_or_create(
                                test_execution=test_execution,
                                test_step=test_step,
                                defaults={
                                    'actual_id': step_data.get('actual_id'),
                                    'actual_input': step_data.get('actual_input'),
                                    'status': step_data.get('status'),
                                    'duration': step_data.get('duration'),
                                    'time_start': time_start,
                                    'time_end': time_end,
                                    'log_message': step_data.get('log_message'),
                                    'error': step_data.get('error'),
                                    'actual_screenshot': step_data.get('screenshot')
                                }
                            )
                        except Exception as e:
                            # Instead of continuing, we log the specific error and append it to our list
                            error_message = f"Failed to save step result for Test Step ID {step_data.get('test_step_id')}: {str(e)}"
                            logger.error(error_message)
                            errors_encountered.append(error_message)
                    
                    # If we made it this far without error for the TC, increment the count
                    if not errors_encountered:
                        saved_results_count += 1

                except Exception as e:
                    error_message = f"Failed to process Test Case Execution ID {tc_result.get('test_execution_id')}: {str(e)}"
                    logger.error(error_message)
                    errors_encountered.append(error_message)

            # *** After the loop, check if any errors were logged ***
            if errors_encountered:
                # If there were any failures, return a 500 error with details
                return Response({
                    "error": "Failed to save one or more results to the database.",
                    "details": errors_encountered,
                    "saved_results_count": saved_results_count
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # If the loop completes with no errors, return a success response
            return Response({
                "message": "Batch test results saved successfully",
                "batch_id": batch_assignment.id,
                "overall_status": batch_assignment.status,
                "saved_results": saved_results_count
            }, status=status.HTTP_200_OK)

        except BatchAssignment.DoesNotExist:
            return Response({"error": "Batch assignment not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # This is a catch-all for errors outside the main loop (e.g., finding the batch)
            logger.error(f"Critical error in SaveBatchTestResultsView: {str(e)}")
            return Response({"error": "An unexpected server error occurred while saving results"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestResultsListView(APIView):
    permission_classes = [IsAuthenticated, IsTester]

    def get(self, request, test_execution_id):
        """
        Get all step results for a test execution with test case details
        """
        try:
            test_execution = get_object_or_404(
                TestExecution.objects.select_related('test_case'),  # Add select_related
                id=test_execution_id
            )

            # Verify the requesting user has permission
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
                    "screenshot" : result.actual_screenshot,
                    "created_at": result.created_at
                })

            return Response({
                "test_execution_id": test_execution_id,
                "overall_status": test_execution.overallstatus,
                "test_case_name": test_execution.test_case.name,  # Add test case name
                "test_case_code": test_execution.test_case.code,  # Add test case code
                "results": data
            })
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=http_status.HTTP_400_BAD_REQUEST
            )


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
                'execution__executed_device'
            ).order_by('-updated_at', 'priority', 'deadline')  # Most recent first, then by priority/deadline

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
                    "device_name": device_name,
                    "last_updated": assignment.updated_at  # Include the update timestamp
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
        
class ManagerAssignedTestsView(APIView):
    permission_classes = [IsAuthenticated, IsManager]

    def get(self, request):
        try:
            # Get all test assignments for the current user where execution is not null
            assignments = TestAssignment.objects.filter(
                assigned_by=request.user,
                execution__isnull=False
            ).exclude(
                status='pending'
            ).select_related(
                'test_case',
                'assigned_to',
                'execution',
                'execution__executed_device'
            ).order_by('-updated_at', 'priority', 'deadline')  # Most recent first, then by priority/deadline

            results = []
            for assignment in assignments:
                # Get device name if execution exists and has a device
                device_name = None
                if assignment.execution and assignment.execution.executed_device:
                    device_name = assignment.execution.executed_device.device_name

                results.append({
                    "test_case_name": assignment.test_case.name,
                    "assigned_to": assignment.assigned_to.username,
                    "assigned_date": assignment.created_at,
                    "priority": assignment.priority,
                    "status": assignment.status,
                    "deadline": assignment.deadline,
                    "execution_id": assignment.execution.id,
                    "test_case_code": assignment.test_case.code,
                    "test_case_description": assignment.test_case.description,
                    "notes": assignment.notes,
                    "assignment_id": assignment.id,
                    "device_name": device_name,
                    "last_updated": assignment.updated_at  # Include the update timestamp
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


class TesterExecutedBatchTestsView(APIView):
    permission_classes = [IsAuthenticated, IsTester]

    def get(self, request):
        try:
            # Get all batch assignments for the current user that have been executed (status not pending)
            batch_assignments = BatchAssignment.objects.filter(
                assigned_to=request.user
            ).exclude(
                status='pending'
            ).select_related(
                'assigned_by',
                'assignment_type',
                'customgroup',
                'application'
            ).prefetch_related(
                'assigned_objects'  # This is the related_name for TestExecution's batch field
            ).order_by('-updated_at')  # Changed to descending order with '-'
            
            results = []
            for batch in batch_assignments:
                # Get all executions for this batch by the current user
                executions = batch.assigned_objects.filter(
                    executed_by=request.user
                ).select_related(
                    'test_case',
                    'executed_device'
                ).order_by('-updated_at')  # Also order executions by updated_at if needed
                
                # Collect execution IDs and device info
                execution_ids = []
                device_names = []
                
                for execution in executions:
                    execution_ids.append(execution.id)
                    if execution.executed_device:
                        device_names.append(execution.executed_device.device_name)
                
                # Remove duplicate device names while preserving order
                seen_devices = set()
                unique_device_names = []
                for name in device_names:
                    if name not in seen_devices:
                        seen_devices.add(name)
                        unique_device_names.append(name)
                
                results.append({
                    "batch_id": batch.id,
                    "batch_name": batch.name,
                    "assigned_by": batch.assigned_by.username,
                    "assigned_date": batch.created_at,
                    "priority": batch.priority,
                    "status": batch.status,
                    "deadline": batch.deadline,
                    "notes": batch.notes,
                    "assignment_type": batch.assignment_type.name if batch.assignment_type else None,
                    "total_test_cases": batch.totaltestcases,
                    "completed_test_cases": batch.completedtestcases,
                    "passed_test_cases": batch.passedtestcases,
                    "application_id": batch.application.id if batch.application else None,
                    "custom_group_id": batch.customgroup.id if batch.customgroup else None,
                    "execution_ids": execution_ids,  # Array of execution IDs
                    "devices_used": unique_device_names,  # Array of unique device names
                    "last_updated": batch.updated_at  # Include the updated_at field
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
        

class ManagerExecutedBatchTestsView(APIView):
    permission_classes = [IsAuthenticated, IsManager]

    def get(self, request):
        try:
            # Get all batch assignments created by this manager that have been executed
            batch_assignments = BatchAssignment.objects.filter(
                assigned_by=request.user
            ).exclude(
                status__in=['passed', 'failed']
            ).select_related(
                'assigned_to',
                'assignment_type',
                'customgroup',
                'customgroup__application',  # For CustomGroup assignments
                'application',  # For direct Application assignments
                'suite',
                'suite__application'  # For Suite assignments
            ).prefetch_related(
                Prefetch('assigned_objects',
                    queryset=TestExecution.objects.select_related(
                        'executed_by',
                        'executed_device',
                        'test_case'
                    ).order_by('-updated_at')
                )
            ).order_by('-updated_at')
            
            results = []
            for batch in batch_assignments:
                # Get the first execution (since all executions in a batch use same device/tester)
                execution = batch.assigned_objects.first()
                
                # Determine application info based on assignment type
                application_id = None
                application_name = None
                
                if batch.assignment_type.name == "Custom_Group" and batch.customgroup:
                    application_id = batch.customgroup.application.id
                    application_name = batch.customgroup.application.name
                elif batch.assignment_type.name == "Application" and batch.application:
                    application_id = batch.application.id
                    application_name = batch.application.name
                elif batch.assignment_type.name == "Suite" and batch.suite:
                    application_id = batch.suite.application.id
                    application_name = batch.suite.application.name
                
                results.append({
                    "batch_id": batch.id,
                    "batch_name": batch.name,
                    "assigned_to": batch.assigned_to.username,
                    "assigned_date": batch.created_at,
                    "priority": batch.priority,
                    "batch_status": batch.status,
                    "deadline": batch.deadline,
                    "notes": batch.notes,
                    "assignment_type": batch.assignment_type.name if batch.assignment_type else None,
                    "total_test_cases": batch.totaltestcases,
                    "application_id": application_id,
                    "application_name": application_name,
                    "custom_group_id": batch.customgroup.id if batch.customgroup else None,
                    "suite_id": batch.suite.id if batch.suite else None,
                    # "execution_id": execution.id if execution else None,
                    # "execution_status": execution.overallstatus if execution else None,
                    # "device_used": execution.executed_device.device_name if execution and execution.executed_device else None,
                    # "tester": execution.executed_by.username if execution else None,
                    "last_updated": batch.updated_at
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